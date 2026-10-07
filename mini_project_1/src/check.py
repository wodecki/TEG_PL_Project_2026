"""Program sprawdzający Miniprojekt 1. Uruchom go z katalogu głównego repozytorium:

    uv run python mini_project_1/src/check.py

Sprawdza po kolei kroki 1–5, uruchamia proces przetwarzania (ang. pipeline), weryfikuje jego raport i sprawdza
krok 6. Nie wywołuje żadnego API i nie potrzebuje klucza. Na koniec wypisuje
podsumowanie wyników (CONCEPTS.md wyjaśnia, na co w nim zwrócić uwagę). Prawdziwe
wywołanie LLM-a to osobny program: mini_project_1/src/first_llm_call.py.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from helpers.checks import Checker, run_pytest, run_script, unimplemented_functions

ROOT = Path(__file__).resolve().parents[2]

HERE = ROOT / "mini_project_1"
REPORT = HERE / "output" / "report.json"
STEPS = [
    ("Krok 1", "step1_load_documents"),
    ("Krok 2", "step2_count_tokens"),
    ("Krok 3", "step3_chunk_documents"),
    ("Krok 4", "step4_build_embeddings"),
    ("Krok 5", "step5_search"),
]


def step_done(c: Checker, label: str, module: str) -> bool:
    """Krok jest napisany i jego testy przechodzą."""
    todo = unimplemented_functions(HERE / "src" / f"{module}.py")
    if todo:
        return c.check(f"{label}: src/{module}.py", False, f"do napisania: {', '.join(todo)}")
    passed, line = run_pytest(HERE / "tests" / f"test_{module}.py", ROOT)
    return c.check(f"{label}: src/{module}.py", passed,
                   line if passed else f"{line} -> uv run pytest mini_project_1/tests/test_{module}.py -v")


def format_results(report: dict) -> str:
    """Podsumowanie wyników wypisywane przez check.py (z niego powstaje też przebieg referencyjny w README)."""
    corpus, chunks, ret, cost = (report[s] for s in ("corpus", "chunks", "retrieval", "cost"))
    lines = [
        "=== Twoje wyniki ===",
        f"Dokumenty / tokeny łącznie:           {corpus['n_documents']} / {corpus['total_tokens']}",
        f"Największy dokument (tokeny):         {corpus['largest_document']}",
        f"Tokeny na słowo według języka:        {corpus['tokens_per_word_by_language']}",
        f"Chunki / średnio znaków / maks.:      {chunks['n_chunks']} / {chunks['avg_chars']} / {chunks['max_chars']}",
        f"Dokument z największą liczbą chunków: {chunks['most_chunked_document']}",
        f"hit@1 / hit@3:                        {ret['hit_rate_at_1']} / {ret['hit_rate_at_3']}",
        *(f"  {r['query_id']}: {', '.join(r['top_ids'])}" for r in ret["results"]),
        f"Miesięczny koszt LLM-a, retrieval / cały korpus: ${cost['rag_monthly_usd']} / "
        f"${cost['full_context_monthly_usd']} (x{cost['full_to_rag_cost_ratio']})",
    ]
    return "\n".join(lines)


def main() -> int:
    c = Checker("Sprawdzenie Miniprojektu 1: fundament wiedzy")

    # 1. Kroki 1–5 po kolei. Zatrzymaj się na pierwszym niegotowym kroku.
    for label, module in STEPS:
        if not step_done(c, label, module):
            break
    if not c.all_passed:
        c.summary()
        return 1

    # 2. Pipeline
    REPORT.unlink(missing_ok=True)
    ran, error = run_script(HERE / "src" / "run_pipeline.py", ROOT)
    if not c.check("Pipeline działa: mini_project_1/src/run_pipeline.py", ran, error) or not c.check(
        "Raport zapisany: mini_project_1/output/report.json", REPORT.is_file()
    ):
        c.summary()
        return 1

    # 3. Raport
    try:
        report = json.loads(REPORT.read_text(encoding="utf-8"))
        corpus, chunks, emb = report["corpus"], report["chunks"], report["embeddings"]
        ret, cost = report["retrieval"], report["cost"]
    except (json.JSONDecodeError, KeyError) as exc:
        c.check("Raport ma oczekiwane sekcje", False, repr(exc))
        c.summary()
        return 1

    n_files = len(list((ROOT / "data" / "corpus").glob("*.md")))
    c.check("Wczytano każdy plik korpusu", corpus["n_documents"] == n_files, f"{corpus['n_documents']} z {n_files}")
    c.check("Liczby tokenów według doc_type sumują się do całości", sum(corpus["tokens_by_doc_type"].values()) == corpus["total_tokens"])
    c.check("Każdy chunk pochodzi z cache kursu", emb["chunks_not_cached"] == 0,
            f"{emb['chunks_not_cached']} poza cache – podział na chunki różni się od ustalonych ustawień"
            if emb["chunks_not_cached"] else "")
    k = ret["k"]
    c.check(f"Każde zapytanie zwraca top {k}, od najlepszego wyniku", all(
        len(r["top_ids"]) == k and r["top_scores"] == sorted(r["top_scores"], reverse=True) for r in ret["results"]
    ))
    rate3 = round(sum(r["hit_at_3"] for r in ret["results"]) / len(ret["results"]), 2)
    c.check("hit@k zgadza się z wynikami poszczególnych zapytań", rate3 == ret["hit_rate_at_3"] and ret["hit_rate_at_1"] <= rate3)
    c.check("Prompty z całym korpusem kosztują więcej niż prompty z wynikami wyszukiwania",
            0 < cost["rag_monthly_usd"] < cost["full_context_monthly_usd"])

    report_ok = c.all_passed

    # 4. Krok 6, sprawdzany offline na sztucznym modelu. Nic powyżej od niego nie zależy.
    llm_step_ok = report_ok and step_done(c, "Krok 6", "step6_connect_llm")

    c.summary()
    if not report_ok:
        return 1

    print()
    print(format_results(report))
    if llm_step_ok:
        print("\nDalej: sprawdź połączenie ze swoim LLM-em (jedno prawdziwe wywołanie, potrzebny dostęp do LLM-a):")
        print("  uv run python mini_project_1/src/first_llm_call.py")
    return 0 if c.all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
