"""Program sprawdzający Miniprojekt 3. Uruchom go z katalogu głównego repozytorium:

    uv run python mini_project_3/src/check.py

Sprawdza, czy Miniprojekty 1 i 2 są ukończone (Miniprojekt 3 na nich się opiera),
sprawdza po kolei kroki 1–5, a potem odtwarza każdy dialog wzorcowy w twoim grafie
z idealnym zrozumieniem wiadomości (atrapa LLM-a). Nie wywołuje API i nie potrzebuje
klucza. Przebieg na żywo to osobny program: mini_project_3/src/run_dialogues.py.
"""

from __future__ import annotations

import sys
from pathlib import Path

from helpers.checks import Checker, run_pytest, unimplemented_functions

ROOT = Path(__file__).resolve().parents[2]
HERE = ROOT / "mini_project_3"
STEPS = [
    ("Krok 1", "step1_required_approvers"),
    ("Krok 2", "step2_understand_turn"),
    ("Krok 3", "step3_conversation_graph"),
    ("Krok 4", "step4_copilot_graph"),
    ("Krok 5", "step5_score_transcript"),
]


def step_done(c: Checker, label: str, module: str) -> bool:
    todo = unimplemented_functions(HERE / "src" / f"{module}.py")
    if todo:
        return c.check(f"{label}: src/{module}.py", False, f"do napisania: {', '.join(todo)}")
    passed, line = run_pytest(HERE / "tests" / f"test_{module}.py", ROOT)
    return c.check(f"{label}: src/{module}.py", passed,
                   line if passed else f"{line} -> uv run pytest mini_project_3/tests/test_{module}.py -v")


def main() -> int:
    c = Checker("Sprawdzenie Miniprojektu 3: workflow decyzyjny")
    for mp in (1, 2):
        todo = [f"{p.stem}: {', '.join(t)}" for p in sorted((ROOT / f"mini_project_{mp}" / "src").glob("step*_*.py"))
                if (t := unimplemented_functions(p))]
        if not c.check(f"Miniprojekt {mp} ukończony", not todo,
                       f"do napisania: {todo[0]} ... (dokończ go albo skopiuj jego rozwiązanie wzorcowe: patrz README)" if todo else ""):
            c.summary()
            return 1
    for label, module in STEPS:
        if not step_done(c, label, module):
            break
    if not c.all_passed:
        c.summary()
        return 1
    passed, line = run_pytest(HERE / "tests" / "test_provided_dialogue_replay.py", ROOT)
    c.check("Dialogi wzorcowe w twoim grafie (idealne zrozumienie, bez LLM-a)", passed,
            line if passed else f"{line} -> uv run pytest mini_project_3/tests/test_provided_dialogue_replay.py -v")
    c.summary()
    if not c.all_passed:
        return 1
    print("\nPrzy poprawnym zrozumieniu wiadomości twój workflow, stan wniosku i polityka zgadzają się z każdym dialogiem wzorcowym.")
    print("Dalej: uruchom dialogi ze swoim LLM-em (na żywo, około 1,7 centa z referencyjnym LLM-em):")
    print("  uv run python mini_project_3/src/run_dialogues.py")
    return 0


if __name__ == "__main__":
    sys.exit(main())
