"""Gotowy test: prawdziwa ścieżka stdio. stdout serwera Kovalo przenosi wyłącznie komunikaty protokołu,
a czas życia połączenia jest ograniczony bez względu na to, co robi serwer: kończy działanie, nigdy
nie odpowiada, ulega awarii w trakcie wywołania, zawiesza się albo ignoruje łagodne zamknięcie. Każdy
scenariusz działa we własnym procesie Pythona z ZEWNĘTRZNYM limitem czasu, więc błąd zwalniania zasobów kończy
test wynikiem negatywnym, zamiast zawiesić cały zestaw. Serwery testowe zapisują identyfikator procesu, więc
testy sprawdzają, czy proces naprawdę się zakończył. Bez klucza API i bez sieci."""

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
TOYS = Path(__file__).resolve().parent / "toy_servers"
SCENARIO = r'''
import json, os, sys, threading, time
sys.path.insert(0, sys.argv[1])
from helpers.mcp_runtime import McpCallError, McpStartupError, stdio_connection
toy, pid_file, action, cleanup = sys.argv[2], sys.argv[3], sys.argv[4], float(sys.argv[5])
out = {}
started = time.monotonic()
try:
    conn = stdio_connection([toy, pid_file], os.path.dirname(toy), startup_timeout_s=2, call_timeout_s=1, cleanup_timeout_s=cleanup)
    out["started"] = True
    if action == "crash":
        try: conn.call("crash", {})
        except McpCallError as e: out["error"] = str(e)
    if action == "hang":
        try: conn.call("hang", {})
        except McpCallError as e: out["error"] = str(e)
        try: conn.call("ping", {})
        except McpCallError as e: out["after"] = str(e)
    t0 = time.monotonic(); conn.close(); conn.close(); out["close_s"] = round(time.monotonic() - t0, 2)
    out["thread_alive"] = conn.alive
except McpStartupError as e:
    out["startup_error"] = str(e)
out["seconds"] = round(time.monotonic() - started, 2)
print(json.dumps(out))
'''


def pid_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def run_scenario(tmp_path, toy: str, action: str, deadline: float = 40, cleanup: float = 6) -> tuple[dict, int]:
    folder = tmp_path / "toy servers"                       # ścieżka ze spacją
    folder.mkdir(exist_ok=True)
    shutil.copy(TOYS / toy, folder / toy)
    pid_file = folder / f"{toy}.pid"
    proc = subprocess.run([sys.executable, "-c", SCENARIO, str(ROOT), str(folder / toy), str(pid_file), action, str(cleanup)],
                          capture_output=True, text=True, timeout=deadline, cwd=tmp_path)
    assert proc.returncode == 0, proc.stderr[-1500:]
    return json.loads(proc.stdout.strip().splitlines()[-1]), int(pid_file.read_text())


@pytest.mark.skipif(sys.platform == "win32", reason="sprawdzanie procesów działa tu tylko w POSIX; Windows nie jest testowany")
def test_a_server_that_exits_at_start_fails_promptly(tmp_path):
    out, pid = run_scenario(tmp_path, "exits_at_start.py", "none")
    assert "startup_error" in out and out["seconds"] < 10, out
    assert "celowo nie startuje" in out["startup_error"], "końcówka stderr serwera jest w komunikacie błędu"
    assert not pid_alive(pid)


@pytest.mark.skipif(sys.platform == "win32", reason="tylko POSIX")
def test_a_silent_server_hits_the_startup_deadline_and_is_ended(tmp_path):
    out, pid = run_scenario(tmp_path, "silent.py", "none")
    assert "nie dokończył inicjalizacji w ciągu 2 s" in out.get("startup_error", ""), out
    assert out["seconds"] < 2 + 6 + 8, "ograniczone: termin startu plus sprzątanie"
    assert not pid_alive(pid), "proces milczącego serwera został zakończony"


@pytest.mark.skipif(sys.platform == "win32", reason="tylko POSIX")
def test_a_server_that_ignores_a_graceful_close_is_killed(tmp_path):
    out, pid = run_scenario(tmp_path, "stubborn.py", "none")
    assert out.get("started") and out["close_s"] < 6 + 8, out
    assert out["thread_alive"] is False and not pid_alive(pid), "SIGTERM zignorowany: SDK przechodzi do kill"


@pytest.mark.skipif(sys.platform == "win32", reason="tylko POSIX")
def test_a_server_that_dies_during_a_call(tmp_path):
    out, pid = run_scenario(tmp_path, "fragile.py", "crash")
    assert "[błąd transportu]" in out.get("error", ""), out
    assert out["thread_alive"] is False and not pid_alive(pid)


@pytest.mark.skipif(sys.platform == "win32", reason="tylko POSIX")
def test_a_hanging_call_times_out_and_the_connection_is_not_reused(tmp_path):
    out, pid = run_scenario(tmp_path, "fragile.py", "hang")
    assert "przekroczyło limit czasu 1 s" in out.get("error", ""), out
    assert "nie nadaje się do użycia" in out.get("after", "")
    assert out["thread_alive"] is False and not pid_alive(pid)


def test_the_kovalo_servers_stdout_is_protocol_only():
    proc = subprocess.Popen([sys.executable, str(ROOT / "mini_project_5" / "src" / "serve.py"),
                             "--config", str(ROOT / "config.yaml")], cwd="/", stdin=subprocess.PIPE,
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    try:
        def send(msg):
            proc.stdin.write(json.dumps(msg) + "\n")
            proc.stdin.flush()
        send({"jsonrpc": "2.0", "id": 1, "method": "initialize",
              "params": {"protocolVersion": "2025-06-18", "capabilities": {}, "clientInfo": {"name": "t", "version": "0"}}})
        send({"jsonrpc": "2.0", "method": "notifications/initialized"})
        send({"jsonrpc": "2.0", "id": 2, "method": "tools/list"})
        send({"jsonrpc": "2.0", "id": 3, "method": "tools/call",
              "params": {"name": "get_invoice_value", "arguments": {"supplier": "SUP-114", "month": "2026-07"}}})
        frames = []
        while len([f for f in frames if "id" in f]) < 3:
            line = proc.stdout.readline()
            assert line, f"serwer zamknął stdout; stderr: {proc.stderr.read()[-800:]}"
            frame = json.loads(line)                        # każdy wiersz stdout musi być komunikatem JSON-RPC
            assert frame.get("jsonrpc") == "2.0", line
            frames.append(frame)
        answer = next(f for f in frames if f.get("id") == 3)
        assert answer["result"]["structuredContent"]["invoiced_grosze"] == 18240000
    finally:
        proc.stdin.close()
        proc.wait(timeout=20)


@pytest.mark.skipif(sys.platform == "win32", reason="tylko POSIX")
def test_the_smallest_allowed_cleanup_deadline_still_ends_a_stubborn_server(tmp_path):
    from helpers.mcp_runtime import MIN_STDIO_CLEANUP_S
    out, pid = run_scenario(tmp_path, "stubborn.py", "none", cleanup=MIN_STDIO_CLEANUP_S)
    assert out.get("started") and out["thread_alive"] is False, out
    assert not pid_alive(pid), "zakończył się proces, nie tylko wątek"


def test_a_cleanup_deadline_too_short_for_the_sdks_teardown_is_refused(tmp_path):
    from helpers.config import ConfigError
    from helpers.mcp_runtime import stdio_connection
    with pytest.raises(ConfigError, match="co najmniej 5 s"):
        stdio_connection([TOYS / "stubborn.py", tmp_path / "pid"], tmp_path, startup_timeout_s=2, call_timeout_s=1,
                         cleanup_timeout_s=0.05)
    assert not (tmp_path / "pid").exists(), "odrzucone, zanim uruchomiono jakikolwiek proces"
