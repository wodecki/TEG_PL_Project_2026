"""Gotowe testy: programy na żywo kończą się przy starcie jednowierszową instrukcją, a nie tracebackiem (bez wywołań API)."""

import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
# Uruchom program tak jak `python mini_project_4/src/<name>.py`, ale z pominięciem .env, żeby
# brakujący klucz był brakujący także na komputerze, który go ma.
LAUNCH = ("import runpy, sys, dotenv; dotenv.load_dotenv = lambda *a, **k: False; "
          "sys.argv = [sys.argv[1]]; runpy.run_path(sys.argv[0], run_name='__main__')")


@pytest.mark.parametrize("program", ["run_agent.py", "compare_supervisor.py", "ask_agent.py"])
def test_a_missing_key_is_one_clear_line(program):
    env = {k: v for k, v in os.environ.items() if not k.endswith("_API_KEY")}
    proc = subprocess.run([sys.executable, "-c", LAUNCH, str(ROOT / "mini_project_4" / "src" / program)],
                          cwd=ROOT, env=env, capture_output=True, text=True, timeout=120, stdin=subprocess.DEVNULL)
    assert proc.returncode == 1, proc.stderr[-500:]
    assert "OPENAI_API_KEY" in proc.stderr and "Traceback" not in proc.stderr, proc.stderr[-800:]
    assert "README.md" in proc.stderr
