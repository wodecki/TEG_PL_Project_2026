"""Miniprojekt 2: porównaj fragmenty dokumentów (ang. chunks) z Miniprojektu 1 ze swoimi chunkami z kontekstem. Gotowy program: uruchom go z katalogu głównego repozytorium:

    uv run python mini_project_2/src/run_retrieval_eval.py

Bez wywołań API i bez opłat: każda reprezentacja wektorowa tekstu (ang. embedding)
pochodzi z pamięci podręcznej kursu (ang. cache). Dla każdego pytania
z odpowiedzią w korpusie pokazuje, dla obu podziałów na chunki, znalezione chunki,
czy znaleziono trafny dokument (poziom 1: wyszukiwanie, ang. retrieval) i ile potrzebnych dowodów
zawiera znaleziony tekst (poziom 2: dowody, mierzone twoim krokiem 3). Najpierw
przejrzyj wiersze dla pojedynczych pytań; sumy są na końcu. Zapisuje
mini_project_2/output/retrieval_report.json.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from dotenv import load_dotenv

from helpers.config import load_config
from helpers.embedding_cache import missing_from_cache, underlying_embeddings
from helpers.gold import load_gold
from helpers.prompts import build_prompt
from helpers.records import Answer, ContextItem, RunRecord
from mini_project_1.src.step1_load_documents import load_documents
from mini_project_1.src.step2_count_tokens import count_tokens
from mini_project_1.src.step3_chunk_documents import chunk_documents
from mini_project_1.src.step4_build_embeddings import build_embeddings
from mini_project_1.src.step5_search import build_vector_store, search
from mini_project_2.src.step1_build_contextual_chunks import build_contextual_chunks
from mini_project_2.src.step3_score_record import score_record

ROOT = Path(__file__).resolve().parents[2]


def evidence_coverage(chunks, question) -> float:
    """Poziom 2 dla wyniku wyszukiwania: twój krok 3 zastosowany do rekordu, który ma tylko kontekst."""
    record = RunRecord(
        question=question.question,
        context=[ContextItem(doc_id=c.metadata["doc_id"], chunk_id=c.metadata["chunk_id"], text=c.page_content) for c in chunks],
        output=Answer(answer="", citations=[], answerable=False),
    )
    return score_record(record, question)["evidence_phrase_coverage"]


def main() -> None:
    load_dotenv(ROOT / ".env", override=True)
    config = load_config(ROOT / "config.yaml")
    k = config.get("retrieval.top_k")
    docs = load_documents(config)
    embeddings = build_embeddings(config, underlying=underlying_embeddings())
    variants = {"mp1": chunk_documents(docs, config), "contextual": build_contextual_chunks(docs, config)}

    missing = missing_from_cache(config, [c.page_content for c in variants["contextual"]])
    if missing:
        raise SystemExit(f"Chunków z kontekstem, których nie ma w kursowym cache: {len(missing)} "
                         f"(pierwszy: {variants['contextual'][missing[0]].metadata['chunk_id']}). Zobacz krok 1.")
    stores = {name: build_vector_store(chunks, embeddings) for name, chunks in variants.items()}
    questions = [q for q in load_gold(config.path("paths.mini_project_2_questions")) if q.answerable]

    results = []
    for q in questions:
        row = {"id": q.id, "question": q.question, "relevant_docs": q.relevant_docs, "requires_all": q.requires_all}
        for name, store in stores.items():
            chunks = [c for c, _ in search(store, q.question, k)]
            ids = [c.metadata["doc_id"] for c in chunks]
            row[name] = {
                "top_chunk_ids": [c.metadata["chunk_id"] for c in chunks],
                "hit_at_1": ids[0] in q.relevant_docs,
                "hit_at_3": any(d in q.relevant_docs for d in ids),
                "all_required_found": all(d in ids for d in q.relevant_docs) if q.requires_all else None,
                "evidence_phrase_coverage": evidence_coverage(chunks, q),
                "prompt_tokens": count_tokens(build_prompt(config.get("prompts.answer_system"), chunks, q.question), config),
            }
        results.append(row)

    n = len(results)
    summary = {}
    for name in stores:
        rows = [r[name] for r in results]
        summary[name] = {
            "n_chunks": len(variants[name]),
            "hit_at_1": sum(r["hit_at_1"] for r in rows),
            "hit_at_3": sum(r["hit_at_3"] for r in rows),
            "evidence_phrases_complete": sum(r["evidence_phrase_coverage"] == 1 for r in rows),
            "avg_prompt_tokens": round(sum(r["prompt_tokens"] for r in rows) / n, 1),
        }
    report = {"k": k, "n_answerable": n, "summary": summary, "results": results}
    out_dir = config.path("paths.mini_project_2_output_dir")
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "retrieval_report.json").write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print_report(report)
    print(f"\nRaport zapisany w {out_dir / 'retrieval_report.json'}")


def print_report(report: dict) -> None:
    print("=== Miniprojekt 2: chunki z Miniprojektu 1 a chunki z kontekstem ===")
    print("Według pytań (hit: 1 = trafny dokument na pierwszym miejscu, 3 = w pierwszej trójce, - = nie znaleziono; dowody = udział fraz dowodowych w tekście)")
    for r in report["results"]:
        print(f"\n{r['id']}  {r['question']}   trafne: {', '.join(r['relevant_docs'])}"
              + ("  (potrzebne wszystkie)" if r["requires_all"] else ""))
        for name in ("mp1", "contextual"):
            v = r[name]
            hit = "1" if v["hit_at_1"] else ("3" if v["hit_at_3"] else "-")
            joint = "" if v["all_required_found"] is None else f"  znaleziono wszystkie potrzebne: {v['all_required_found']}"
            print(f"  {name:10} hit {hit}  dowody {v['evidence_phrase_coverage']:.2f}  {', '.join(v['top_chunk_ids'])}{joint}")


if __name__ == "__main__":
    try:
        main()
    except NotImplementedError as exc:
        sys.exit(f"Jeszcze do napisania: {exc}")
