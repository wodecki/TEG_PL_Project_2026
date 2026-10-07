"""Program sprawdzający Miniprojekt 4. Uruchom go z katalogu głównego repozytorium:

    uv run python mini_project_4/src/check.py

Sprawdza, czy Miniprojekty 1–3 są ukończone (Miniprojekt 4 na nich bazuje), potem po kolei
kroki 1–4, a na koniec twoje narzędzia na dostarczonych danych firmy, porównując wyniki
ze wzorcem policzonym ręcznie. Nie wywołuje API i nie potrzebuje klucza. Przebieg na żywo
to osobny program: mini_project_4/src/run_agent.py.
"""

from __future__ import annotations

import sys
from pathlib import Path

from helpers.checks import Checker, run_pytest, unimplemented_functions

ROOT = Path(__file__).resolve().parents[2]
HERE = ROOT / "mini_project_4"
STEPS = [
    ("Krok 1", "step1_read_company_data"),
    ("Krok 2", "step2_compute_and_search"),
    ("Krok 3", "step3_build_agent"),
    ("Krok 4", "step4_score_trace"),
]


def step_done(c: Checker, label: str, module: str) -> bool:
    todo = unimplemented_functions(HERE / "src" / f"{module}.py")
    if todo:
        return c.check(f"{label}: src/{module}.py", False, f"do napisania: {', '.join(todo)}")
    passed, line = run_pytest(HERE / "tests" / f"test_{module}.py", ROOT)
    return c.check(f"{label}: src/{module}.py", passed,
                   line if passed else f"{line} -> uv run pytest mini_project_4/tests/test_{module}.py -v")


def main() -> int:
    c = Checker("Sprawdzenie Miniprojektu 4: agent z narzędziami")
    for mp in (1, 2, 3):
        todo = [f"{p.stem}: {', '.join(t)}" for p in sorted((ROOT / f"mini_project_{mp}" / "src").glob("step*_*.py"))
                if (t := unimplemented_functions(p))]
        if not c.check(f"Miniprojekt {mp} ukończony", not todo,
                       f"do napisania: {todo[0]} ... (dokończ go albo skopiuj jego rozwiązanie wzorcowe: zob. README)" if todo else ""):
            c.summary()
            return 1
    for label, module in STEPS:
        if not step_done(c, label, module):
            break
    if not c.all_passed:
        c.summary()
        return 1
    for name, test in [("Wyniki narzędzi dla danych firmy są zgodne ze wzorcem obliczonym ręcznie", "test_provided_company_data.py"),
                       ("Mechanika zapisu przebiegu i reguły rozpoznawania liczb", "test_provided_trace_plumbing.py"),
                       ("Programy na żywo startują z czytelnymi błędami (klucz niepotrzebny)", "test_provided_programs.py")]:
        passed, line = run_pytest(HERE / "tests" / test, ROOT)
        c.check(name, passed, line if passed else f"{line} -> uv run pytest mini_project_4/tests/{test} -v")
    c.summary()
    if not c.all_passed:
        return 1
    print("\nTwoje narzędzia, pętla agenta i ocena działają offline.")
    print("Dalej: uruchom agenta na pytaniach wzorcowych (na żywo, około 4 centów z referencyjnym LLM-em):")
    print("  uv run python mini_project_4/src/run_agent.py")
    return 0


if __name__ == "__main__":
    sys.exit(main())
