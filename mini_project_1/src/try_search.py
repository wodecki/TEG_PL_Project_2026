"""Dla chętnych (bez oceny): przeszukaj korpus własnym pytaniem.

    uv run python mini_project_1/src/try_search.py "Czy przedstawiciel handlowy może zatwierdzić rabat 7%?"
    uv run python mini_project_1/src/try_search.py "Czy przedstawiciel handlowy może zatwierdzić rabat 7%?" --ask

Twojego pytania nie ma w dołączonej pamięci podręcznej (ang. cache), więc jego
reprezentacja wektorowa (ang. embedding) jest obliczana na bieżąco
w OpenAI (płatne wywołanie, znacznie poniżej centa; potrzebny OPENAI_API_KEY). Opcja --ask
wysyła też pytanie do twojego LLM-a (krok 6) *bez* żadnych znalezionych fragmentów,
żeby było widać, co model mówi o Kovalo, gdy nie ma żadnych dokumentów.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from dotenv import load_dotenv

from helpers.config import load_config
from helpers.embedding_cache import live_query_embeddings, require_openai_key, underlying_embeddings
from helpers.llm_notice import other_llm_note
from mini_project_1.src.step1_load_documents import load_documents
from mini_project_1.src.step3_chunk_documents import chunk_documents
from mini_project_1.src.step4_build_embeddings import build_embeddings
from mini_project_1.src.step5_search import build_vector_store, search
from mini_project_1.src.step6_connect_llm import build_llm

ROOT = Path(__file__).resolve().parents[2]


def main() -> None:
    parser = argparse.ArgumentParser(description="Przeszukaj korpus Kovalo.")
    parser.add_argument("question")
    parser.add_argument("--k", type=int, help="liczba wyników (domyślnie retrieval.top_k z config.yaml)")
    parser.add_argument("--doc-type", help="szukaj tylko w dokumentach tego typu, np. policy")
    parser.add_argument("--ask", action="store_true", help="zadaj też pytanie LLM-owi bez żadnego kontekstu")
    parser.add_argument("--config-override", type=Path, help="plik YAML z wartościami konfiguracji do zmiany, np. llm.provider")
    args = parser.parse_args()

    load_dotenv(ROOT / ".env", override=True)
    require_openai_key("twojego pytania nie ma w cache kursu, więc jego embedding powstaje na bieżąco w OpenAI.")
    config = load_config(ROOT / "config.yaml", args.config_override)
    k = args.k or config.get("retrieval.top_k")

    docs = load_documents(config)
    chunks = chunk_documents(docs, config)
    store = build_vector_store(chunks, build_embeddings(config, underlying=underlying_embeddings()))
    store.embedding = live_query_embeddings(config)  # twoje pytanie: embedding na bieżąco, nigdy nie trafia do cache kursu

    print(f"Top {k} chunków dla pytania: {args.question}\n")
    for rank, (chunk, score) in enumerate(search(store, args.question, k, doc_type=args.doc_type), start=1):
        preview = chunk.page_content.replace("\n", " ")[:160]
        print(f"{rank}. {chunk.metadata['chunk_id']}  score={score:.4f}\n   {preview}...\n")

    if args.ask:
        note = other_llm_note(config)
        if note:
            print(note + "\n")
        llm = build_llm(config)
        answer = llm.invoke(f"W firmie Kovalo Distribution: {args.question}")
        print("Odpowiedź LLM-a BEZ kontekstu:\n")
        print(answer.content)


if __name__ == "__main__":
    main()
