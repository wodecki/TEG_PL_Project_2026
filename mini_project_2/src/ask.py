"""Opcjonalnie (bez oceny): zadaj copilotowi własne pytanie. Gotowy program: uruchom go z katalogu głównego repozytorium:

    uv run python mini_project_2/src/ask.py "Czy regionalny kierownik sprzedaży może zatwierdzić 10% dla klienta strategicznego?"

Jedno wywołanie na żywo (ułamek centa z referencyjnym LLM-em). Twojego pytania nie ma
w pamięci podręcznej kursu (ang. cache), więc jego reprezentacja wektorowa
(ang. embedding) jest obliczana na bieżąco w OpenAI (potrzebny OPENAI_API_KEY).
"""

from __future__ import annotations

import argparse
import sys
import warnings
from pathlib import Path

from dotenv import load_dotenv

from helpers.config import ConfigError, load_config
from helpers.embedding_cache import live_query_embeddings, require_openai_key, underlying_embeddings
from helpers.llm_notice import other_llm_note
from mini_project_1.src.step1_load_documents import load_documents
from mini_project_1.src.step4_build_embeddings import build_embeddings
from mini_project_1.src.step5_search import build_vector_store
from mini_project_1.src.step6_connect_llm import build_llm
from mini_project_2.src.step1_build_contextual_chunks import build_contextual_chunks
from mini_project_2.src.step2_answer_question import answer_question

ROOT = Path(__file__).resolve().parents[2]
# structured output w langchain-openai wywołuje niegroźne ostrzeżenia serializacji Pydantic; ukrywamy je
warnings.filterwarnings("ignore", message="Pydantic serializer warnings")


def main() -> None:
    parser = argparse.ArgumentParser(description="Zadaj copilotowi Kovalo jedno pytanie.")
    parser.add_argument("question")
    parser.add_argument("--config-override", type=Path, help="plik YAML z wartościami konfiguracji do zmiany")
    args = parser.parse_args()
    load_dotenv(ROOT / ".env", override=True)
    require_openai_key("twojego pytania nie ma w kursowym cache, więc jego embedding powstaje na żywo w OpenAI.")
    config = load_config(ROOT / "config.yaml", args.config_override)
    note = other_llm_note(config)
    if note:
        print(note + "\n")
    store = build_vector_store(build_contextual_chunks(load_documents(config), config),
                               build_embeddings(config, underlying=underlying_embeddings()))
    store.embedding = live_query_embeddings(config)  # twoje pytanie: embedding na żywo, nigdy nie trafia do kursowego cache
    record = answer_question(args.question, store, build_llm(config), config)
    print(f"Kontekst: {', '.join(item.chunk_id for item in record.context)}\n")
    if record.error:
        sys.exit(f"Brak odpowiedzi: {record.error}")
    print(record.output.answer)
    print(f"\nOdwołania: {', '.join(record.output.citations) or '-'}   answerable: {record.output.answerable}")


if __name__ == "__main__":
    try:
        main()
    except ConfigError as exc:
        sys.exit(str(exc))
