"""Program sprawdzający Miniprojekt 5. Uruchom go z katalogu głównego repozytorium:

    uv run python mini_project_5/src/check.py

Sprawdza, czy Miniprojekty 1–4 są ukończone (Miniprojekt 5 na nich bazuje), sprawdza po kolei
kroki 1–4, a potem odtwarza każdą rozmowę przez twojego asystenta (idealne rozumienie wiadomości,
bez LLM-a) i sprawdza środowisko uruchomieniowe MCP oraz prawdziwy serwer stdio. Bez wywołań API
i bez klucza. Przebiegi na żywo to osobne programy: run_agent_mcp.py i run_assistant_eval.py.
"""

from __future__ import annotations

import sys
from pathlib import Path

from helpers.checks import Checker, run_pytest, unimplemented_functions

ROOT = Path(__file__).resolve().parents[2]
HERE = ROOT / "mini_project_5"
STEPS = [
    ("Krok 1", "step1_build_server"),
    ("Krok 2", "step2_compare_call"),
    ("Krok 3", "step3_answer_with_tools"),
    ("Krok 4", "step4_build_assistant"),
]
PROVIDED = [
    ("Każda rozmowa przechodzi przez twojego asystenta (idealne rozumienie, bez LLM-a)", "test_provided_conversation_replay.py"),
    ("Ocena asystenta obejmuje każde oczekiwane sprawdzenie", "test_provided_assistant_eval.py"),
    ("Środowisko MCP: kontrakt, warstwy błędów, limity czasu", "test_provided_mcp_runtime.py"),
    ("Prawdziwy serwer stdio i ograniczony czas życia połączenia", "test_provided_stdio.py"),
    ("Zabezpieczenia z Miniprojektu 4 przez MCP (dowody, jednostki, limity)", "test_provided_mp4_guards_over_mcp.py"),
]


def step_done(c: Checker, label: str, module: str) -> bool:
    todo = unimplemented_functions(HERE / "src" / f"{module}.py")
    if todo:
        return c.check(f"{label}: src/{module}.py", False, f"do napisania: {', '.join(todo)}")
    passed, line = run_pytest(HERE / "tests" / f"test_{module}.py", ROOT)
    return c.check(f"{label}: src/{module}.py", passed,
                   line if passed else f"{line} -> uv run pytest mini_project_5/tests/test_{module}.py -v")


def main() -> int:
    c = Checker("Sprawdzenie Miniprojektu 5: jeden standardowy interfejs (MCP) i końcowy asystent")
    for mp in (1, 2, 3, 4):
        todo = [f"{p.stem}: {', '.join(t)}" for p in sorted((ROOT / f"mini_project_{mp}" / "src").glob("step*_*.py"))
                if (t := unimplemented_functions(p))]
        if not c.check(f"Miniprojekt {mp} ukończony", not todo,
                       f"do napisania: {todo[0]} ... (dokończ go albo skopiuj jego rozwiązanie referencyjne: zob. README)" if todo else ""):
            c.summary()
            return 1
    for label, module in STEPS:
        if not step_done(c, label, module):
            break
    if not c.all_passed:
        c.summary()
        return 1
    for name, test in PROVIDED:
        passed, line = run_pytest(HERE / "tests" / test, ROOT)
        c.check(name, passed, line if passed else f"{line} -> uv run pytest mini_project_5/tests/{test} -v")
    c.summary()
    if not c.all_passed:
        return 1
    print("\nTwój serwer, sprawdzenie zgodności, węzeł z narzędziami i asystent działają offline.")
    print("Dalej (na żywo): agent przez MCP na pytaniach z Miniprojektu 4, potem cały asystent:")
    print("  uv run python mini_project_5/src/run_agent_mcp.py")
    print("  uv run python mini_project_5/src/run_assistant_eval.py")
    return 0


if __name__ == "__main__":
    sys.exit(main())
