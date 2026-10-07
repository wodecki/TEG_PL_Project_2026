"""Program sprawdzający Miniprojekt 2. Uruchom go z katalogu głównego repozytorium:

    uv run python mini_project_2/src/check.py

Sprawdza, czy Miniprojekt 1 jest ukończony (Miniprojekt 2 na nim się opiera), potem
po kolei kroki 1–4, uruchamia porównanie wyszukiwania offline i sprawdza jego raport.
Nie wywołuje API i nie potrzebuje klucza. Ewaluacja na żywo to osobny program:
mini_project_2/src/answer_questions.py.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from helpers.checks import Checker, run_pytest, run_script, unimplemented_functions

ROOT = Path(__file__).resolve().parents[2]

HERE = ROOT / "mini_project_2"
REPORT = HERE / "output" / "retrieval_report.json"
STEPS = [
    ("Krok 1", "step1_build_contextual_chunks"),
    ("Krok 2", "step2_answer_question"),
    ("Krok 3", "step3_score_record"),
    ("Krok 4", "step4_judge_record"),
]


def step_done(c: Checker, label: str, module: str) -> bool:
    """Krok jest napisany i jego testy przechodzą."""
    todo = unimplemented_functions(HERE / "src" / f"{module}.py")
    if todo:
        return c.check(f"{label}: src/{module}.py", False, f"do napisania: {', '.join(todo)}")
    passed, line = run_pytest(HERE / "tests" / f"test_{module}.py", ROOT)
    return c.check(f"{label}: src/{module}.py", passed,
                   line if passed else f"{line} -> uv run pytest mini_project_2/tests/test_{module}.py -v")


def format_results(report: dict) -> str:
    """Podsumowanie wyników drukowane przez check.py (służy też do wygenerowania przebiegu referencyjnego w README)."""
    s = report["summary"]
    n = report["n_answerable"]
    lines = ["=== Twoje wyniki: chunki z Miniprojektu 1 a chunki z kontekstem ==="]
    for name, label in (("mp1", "z Miniprojektu 1"), ("contextual", "z kontekstem")):
        v = s[name]
        lines.append(f"{label:16} chunki {v['n_chunks']:3}   hit@1 {v['hit_at_1']}/{n}   hit@3 {v['hit_at_3']}/{n}   "
                     f"komplet fraz dowodowych {v['evidence_phrases_complete']}/{n}   tokeny w prompcie (średnio) {v['avg_prompt_tokens']}")
    for r in report["results"]:
        marks = []
        for name in ("mp1", "contextual"):
            v = r[name]
            hit = "1" if v["hit_at_1"] else ("3" if v["hit_at_3"] else "-")
            marks.append(f"{hit} {v['evidence_phrase_coverage']:.2f}")
        lines.append(f"  {r['id']}: Miniprojekt 1: {marks[0]} | z kontekstem: {marks[1]}   (hit, dowody)")
    return "\n".join(lines)


def main() -> int:
    c = Checker("Sprawdzenie Miniprojektu 2: odpowiedzi oparte na źródłach")

    # 0. Miniprojekt 2 opiera się na Miniprojekcie 1
    mp1_todo = [f"{p.stem}: {', '.join(t)}" for p in sorted((ROOT / "mini_project_1" / "src").glob("step*_*.py"))
                if (t := unimplemented_functions(p))]
    if not c.check("Miniprojekt 1 ukończony", not mp1_todo,
                   f"do napisania: {mp1_todo[0]} ... (dokończ go albo skopiuj jego rozwiązanie wzorcowe: zobacz README)"
                   if mp1_todo else ""):
        c.summary()
        return 1

    # 1. Kroki po kolei. Zatrzymaj się na pierwszym nieukończonym.
    for label, module in STEPS:
        if not step_done(c, label, module):
            break
    if not c.all_passed:
        c.summary()
        return 1

    # 2. Porównanie wyszukiwania offline
    REPORT.unlink(missing_ok=True)
    ran, error = run_script(HERE / "src" / "run_retrieval_eval.py", ROOT)
    if not c.check("Porównanie wyszukiwania działa: mini_project_2/src/run_retrieval_eval.py", ran, error) or not c.check(
        "Raport zapisany: mini_project_2/output/retrieval_report.json", REPORT.is_file()
    ):
        c.summary()
        return 1

    # 3. Raport
    try:
        report = json.loads(REPORT.read_text(encoding="utf-8"))
        summary, results, n = report["summary"], report["results"], report["n_answerable"]
    except (json.JSONDecodeError, KeyError) as exc:
        c.check("Raport ma oczekiwane sekcje", False, repr(exc))
        c.summary()
        return 1
    c.check("Porównano każde pytanie z odpowiedzią w korpusie", len(results) == n and n > 0, f"{len(results)} z {n}")
    c.check("Oba podziały na chunki zwracają top-k dla każdego pytania", all(
        len(r[name]["top_chunk_ids"]) == report["k"] for r in results for name in ("mp1", "contextual")))
    c.check("Id chunków z kontekstem różnią się od id chunków z Miniprojektu 1", all(
        "#ctx" in cid for r in results for cid in r["contextual"]["top_chunk_ids"]))
    c.check("Sumy zgadzają się z wynikami dla pytań", all(
        summary[name]["hit_at_3"] == sum(r[name]["hit_at_3"] for r in results) for name in ("mp1", "contextual")))

    c.summary()
    if not c.all_passed:
        return 1
    print()
    print(format_results(report))
    print("\nDalej: odpowiedz swoim LLM-em na dwanaście pytań i oceń odpowiedzi (na żywo, około 2 centów z referencyjnym LLM-em):")
    print("  uv run python mini_project_2/src/answer_questions.py")
    return 0


if __name__ == "__main__":
    sys.exit(main())
