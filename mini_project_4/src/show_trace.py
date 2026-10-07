"""Miniprojekt 4: co agent zrobił przy jednym pytaniu. Gotowy program – uruchom go z katalogu
głównego repozytorium:

    uv run python mini_project_4/src/show_trace.py P1                       twój ostatni przebieg agenta
    uv run python mini_project_4/src/show_trace.py P1 --run supervisor      twój ostatni przebieg supervisora
    uv run python mini_project_4/src/show_trace.py P1 --reference           zapisany przebieg referencyjny kursu
    uv run python mini_project_4/src/show_trace.py P1 --reference --run supervisor

Wypisuje ścieżkę dowodów: każde wywołanie narzędzia po kolei (własne wywołania specjalisty
z wcięciem pod jego wywołaniem), jego pochodzenie (data / calculation / worker_summary),
argumenty i kluczowe pola wyniku; potem odpowiedź i oceny. Nie wywołuje API.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from helpers.agent_trace import Trace, load_traces
from mini_project_4.src.run_agent import architecture_label

ROOT = Path(__file__).resolve().parents[2]
SKIP = {"status", "currency", "note", "requested", "query", "settlement", "terms_version", "message", "supplier"}


def brief(result) -> str:
    """Kluczowe pola wyniku narzędzia, w jednym wierszu."""
    if not isinstance(result, dict):
        return str(result)[:160]
    if "passages" in result:
        return f"{result['status']}: " + ", ".join(p["chunk_id"] for p in result["passages"])
    if "summary" in result:
        return "podsumowanie: " + str(result["summary"]).replace("\n", " ")[:160]
    fields = {k: v for k, v in result.items() if k not in SKIP and v not in (None, [], "")}
    if "observations" in fields:
        fields["observations"] = ", ".join(f"{o['month']}: {o['otif_pct']}" for o in fields["observations"])
    text = f"{result.get('status')}: " + json.dumps(fields, ensure_ascii=False)
    return text if not result.get("message") else f"{text} ({result['message']})"


def format_trace(trace: Trace, score: dict | None = None) -> str:
    lines = [f"{trace.question_id or ''}  {trace.question}", f"status: {trace.status}"
             + (f" ({trace.error})" if trace.error else "") + f"; kroki: {trace.steps}, {trace.seconds:.0f} s"]
    depth = {}
    for n, event in enumerate(trace.events, start=1):
        depth[event.call_id] = depth.get(event.parent_call_id, -1) + 1 if event.parent_call_id else 0
        indent = "    " * depth[event.call_id]
        args = ", ".join(f"{k}={v!r}" for k, v in event.arguments.items())
        outcome = brief(event.result) if event.status == "ok" else f"{event.status.upper()}: {(event.error or '')[:160]}"
        who = "" if event.agent == "agent" else f"[{event.agent}] "
        lines.append(f"  {indent}{n:2}. {who}{event.tool}({args})  <{event.origin}>")
        lines.append(f"  {indent}      -> {outcome}")
    lines.append("odpowiedź: " + (trace.answer or "(brak)"))
    if score:
        lines.append("ocena: " + json.dumps(score, ensure_ascii=False))
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Pokazuje jeden trace z przebiegu agenta.")
    parser.add_argument("question_id", help="np. P1")
    parser.add_argument("--run", choices=["agent", "supervisor"], default="agent")
    parser.add_argument("--reference", action="store_true", help="zapisany przebieg referencyjny kursu")
    args = parser.parse_args()
    folder = ROOT / "mini_project_4" / ("reference_traces" if args.reference else "output")
    path = folder / f"{args.run}_run.json"
    if not path.is_file():
        sys.exit(f"nie znaleziono {path.relative_to(ROOT)}: najpierw uruchom mini_project_4/src/"
                 f"{'run_agent' if args.run == 'agent' else 'compare_supervisor'}.py albo użyj --reference")
    run, rows = load_traces(path)
    row = next((r for r in rows if r["trace"].question_id == args.question_id), None)
    if row is None:
        sys.exit(f"w {path.name} nie ma pytania {args.question_id!r}; są: {', '.join(r['trace'].question_id for r in rows)}")
    print(f"przebieg {run['run_id']}: {architecture_label(run['architecture'])}, {run['provider']} / {run['model']}\n")
    print(format_trace(row["trace"], row.get("score")))


if __name__ == "__main__":
    main()
