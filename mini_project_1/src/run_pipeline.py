"""Proces przetwarzania (ang. pipeline) w Miniprojekcie 1: uruchamia razem twoje kroki 1–5 i zapisuje raport.

Gotowy program: uruchom go z katalogu głównego repozytorium:

    uv run python mini_project_1/src/run_pipeline.py

Zapisuje mini_project_1/output/report.json i mini_project_1/output/chunks.jsonl, a potem wypisuje
podsumowanie. Nie wykonuje płatnych wywołań API i nie potrzebuje klucza API: wszystkie reprezentacje wektorowe tekstu (ang. embeddings)
są odczytywane z pamięci podręcznej kursu (ang. cache).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from statistics import mean

from dotenv import load_dotenv

from helpers.config import load_config
from helpers.embedding_cache import missing_from_cache, underlying_embeddings
from helpers.eval_queries import load_eval_queries
from helpers.prompts import build_prompt
from mini_project_1.src.step1_load_documents import load_documents
from mini_project_1.src.step2_count_tokens import count_tokens, monthly_cost
from mini_project_1.src.step3_chunk_documents import chunk_documents
from mini_project_1.src.step4_build_embeddings import build_embeddings
from mini_project_1.src.step5_search import build_vector_store, search

ROOT = Path(__file__).resolve().parents[2]


def main() -> None:
    load_dotenv(ROOT / ".env", override=True)
    config = load_config(ROOT / "config.yaml")
    k = config.get("retrieval.top_k")

    # Kroki 1–2: dokumenty i tokeny
    docs = load_documents(config)
    tokens = {d.metadata["doc_id"]: count_tokens(d.page_content, config) for d in docs}
    tokens_by_type: dict[str, int] = {}
    for d in docs:
        tokens_by_type[d.metadata["doc_type"]] = tokens_by_type.get(d.metadata["doc_type"], 0) + tokens[d.metadata["doc_id"]]
    tokens_per_word = {}
    for lang in sorted({d.metadata["language"] for d in docs}):
        text = "\n".join(d.page_content for d in docs if d.metadata["language"] == lang)
        tokens_per_word[lang] = round(count_tokens(text, config) / len(text.split()), 3)

    # Krok 3: chunki
    chunks = chunk_documents(docs, config)
    lengths = [len(c.page_content) for c in chunks]
    chunks_per_doc: dict[str, int] = {}
    for c in chunks:
        chunks_per_doc[c.metadata["doc_id"]] = chunks_per_doc.get(c.metadata["doc_id"], 0) + 1

    # Krok 4: embeddingi – każdy poprawny chunk jest już w cache kursu, więc klucz OpenAI nie jest potrzebny
    embeddings = build_embeddings(config, underlying=underlying_embeddings())
    missing = missing_from_cache(config, [c.page_content for c in chunks])
    if missing:
        raise SystemExit(
            f"{len(missing)} z {len(chunks)} chunków nie ma w cache kursu "
            f"(pierwszy: {chunks[missing[0]].metadata['chunk_id']}). Twoje chunki różnią się od ustalonego "
            "podziału – zobacz mini_project_1/src/step3_chunk_documents.py."
        )

    # Krok 5: wyszukiwanie dla dziesięciu pytań testowych
    store = build_vector_store(chunks, embeddings)
    queries = load_eval_queries(config.path("paths.eval_queries"))
    results = []
    for query in queries:
        hits = search(store, query.question, k)
        found_docs = [chunk.metadata["doc_id"] for chunk, _ in hits]
        results.append(
            {
                "query_id": query.query_id,
                "top_ids": [chunk.metadata["chunk_id"] for chunk, _ in hits],
                "top_scores": [round(float(score), 4) for _, score in hits],
                "hit_at_1": any(d in query.relevant_docs for d in found_docs[:1]),
                "hit_at_3": any(d in query.relevant_docs for d in found_docs[:3]),
            }
        )

    # Koszt: prompt z top-k chunkami a prompt z całym korpusem
    system = config.get("prompts.system")
    by_id = {c.metadata["chunk_id"]: c for c in chunks}
    rag_tokens = [
        count_tokens(build_prompt(system, [by_id[cid] for cid in r["top_ids"]], q.question), config)
        for q, r in zip(queries, results)
    ]
    full_tokens = [count_tokens(build_prompt(system, docs, q.question), config) for q in queries]
    rag_monthly = monthly_cost(mean(rag_tokens), config)
    full_monthly = monthly_cost(mean(full_tokens), config)

    report = {
        "corpus": {
            "n_documents": len(docs),
            "total_tokens": sum(tokens.values()),
            "tokens_by_doc_type": tokens_by_type,
            "largest_document": min(tokens, key=lambda i: (-tokens[i], i)),
            "tokens_per_word_by_language": tokens_per_word,
        },
        "chunks": {
            "n_chunks": len(chunks),
            "avg_chars": round(sum(lengths) / len(lengths), 1),
            "max_chars": max(lengths),
            "most_chunked_document": min(chunks_per_doc, key=lambda i: (-chunks_per_doc[i], i)),
        },
        "embeddings": {"model": config.get("embeddings.model"), "chunks_not_cached": len(missing)},
        "retrieval": {
            "k": k,
            "results": results,
            "hit_rate_at_1": round(float(mean(r["hit_at_1"] for r in results)), 2),
            "hit_rate_at_3": round(float(mean(r["hit_at_3"] for r in results)), 2),
        },
        "cost": {
            "llm_model": config.get("cost.reference_model"),
            "rag_avg_input_tokens": round(mean(rag_tokens), 1),
            "full_context_avg_input_tokens": round(mean(full_tokens), 1),
            "rag_monthly_usd": round(rag_monthly, 2),
            "full_context_monthly_usd": round(full_monthly, 2),
            "full_to_rag_cost_ratio": round(full_monthly / rag_monthly, 1),
        },
    }

    out_dir = config.path("paths.mini_project_1_output_dir")
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "report.json").write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    with (out_dir / "chunks.jsonl").open("w", encoding="utf-8") as fh:
        for chunk in chunks:
            fh.write(json.dumps({"metadata": chunk.metadata, "page_content": chunk.page_content}, ensure_ascii=False) + "\n")

    print_summary(report)
    print(f"\nRaport zapisany w {out_dir / 'report.json'}")


def print_summary(report: dict) -> None:
    corpus, chunks, ret, cost = (report[s] for s in ("corpus", "chunks", "retrieval", "cost"))
    print("=== Miniprojekt 1: fundament wiedzy ===")
    print(f"Dokumenty: {corpus['n_documents']}   tokeny łącznie: {corpus['total_tokens']}   "
          f"największy: {corpus['largest_document']}")
    print(f"Tokeny na słowo według języka: {corpus['tokens_per_word_by_language']}")
    print(f"Chunki: {chunks['n_chunks']}   średnio znaków: {chunks['avg_chars']}   maks. znaków: {chunks['max_chars']}   "
          f"najwięcej chunków: {chunks['most_chunked_document']}")
    print(f"\nWyszukiwanie (top-{ret['k']}):")
    for r in ret["results"]:
        mark = "hit@1" if r["hit_at_1"] else ("hit@3" if r["hit_at_3"] else "MISS ")
        print(f"  {r['query_id']}  {mark}  {', '.join(r['top_ids'])}  {r['top_scores']}")
    print(f"hit@1: {ret['hit_rate_at_1']}   hit@3: {ret['hit_rate_at_3']}")
    print(f"\nKoszt tokenów LLM-a ({cost['llm_model']}, ustalone ceny z października 2026 r.): prompt top-{ret['k']} ~{cost['rag_avg_input_tokens']} tokenów -> "
          f"${cost['rag_monthly_usd']}/miesiąc; cały korpus ~{cost['full_context_avg_input_tokens']} tokenów -> "
          f"${cost['full_context_monthly_usd']}/miesiąc (x{cost['full_to_rag_cost_ratio']})")


if __name__ == "__main__":
    try:
        main()
    except NotImplementedError as exc:
        sys.exit(f"Jeszcze nie napisane: {exc}")
