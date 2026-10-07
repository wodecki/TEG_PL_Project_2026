"""Miniprojekt 5: serwer MCP Kovalo uruchamiany przez stdio. Gotowy program.

Rzadko uruchamiasz go samodzielnie: asystent (chat.py, run_assistant_eval.py) uruchamia go jako
podproces i wymienia z nim komunikaty przez standardowe wejście i wyjście (stdin/stdout). Żeby wypróbować go z innym klientem MCP, wskaż
klientowi to polecenie (z katalogu głównego repozytorium, ścieżki ze spacjami w cudzysłowie):

    uv run python mini_project_5/src/serve.py --config config.yaml

MCP Inspector:   npx @modelcontextprotocol/inspector uv run python mini_project_5/src/serve.py --config config.yaml
Claude Desktop:  zob. „Serwer w innym kliencie” w mini_project_5/README.md

stdout przenosi wyłącznie komunikaty MCP; wszystko inne (ostrzeżenia, błędy) trafia na stderr.
Indeks wyszukiwania powstaje przy PIERWSZYM wyszukiwaniu (embeddingi zapytań na żywo: potrzebny
OPENAI_API_KEY w pliku .env projektu); każde inne narzędzie działa bez klucza.
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))                    # uruchamiany jako skrypt przez dowolnego klienta, z dowolnego folderu

from dotenv import load_dotenv  # noqa: E402

from helpers.agent_trace import AgentDeps  # noqa: E402
from helpers.company import load_company_data  # noqa: E402
from helpers.config import load_config  # noqa: E402


class LazyStore:
    """Indeks kontekstowy z Miniprojektu 2, budowany przy pierwszym wyszukiwaniu (dzięki temu serwer
    startuje szybko i bez klucza). Embeddingi zapytań powstają na żywo i nigdy nie trafiają do cache."""

    def __init__(self, config):
        self.config, self._store = config, None

    def similarity_search_with_score(self, query, k=4, **kwargs):
        if self._store is None:
            from helpers.embedding_cache import live_query_embeddings, require_openai_key, underlying_embeddings
            from mini_project_1.src.step1_load_documents import load_documents
            from mini_project_1.src.step4_build_embeddings import build_embeddings
            from mini_project_1.src.step5_search import build_vector_store
            from mini_project_2.src.step1_build_contextual_chunks import build_contextual_chunks

            require_openai_key("embeddingi zapytań wyszukiwania powstają na żywo w OpenAI.")
            store = build_vector_store(build_contextual_chunks(load_documents(self.config), self.config),
                                       build_embeddings(self.config, underlying=underlying_embeddings()))
            store.embedding = live_query_embeddings(self.config)
            self._store = store
        return self._store.similarity_search_with_score(query, k=k, **kwargs)


def main() -> None:
    parser = argparse.ArgumentParser(description="Serwer MCP Kovalo (stdio).")
    parser.add_argument("--config", type=Path, default=ROOT / "config.yaml")
    args = parser.parse_args()
    logging.basicConfig(stream=sys.stderr, level=logging.WARNING)
    load_dotenv(args.config.resolve().parent / ".env", override=True)
    config = load_config(args.config)
    from mini_project_5.src.step1_build_server import build_server

    server = build_server(AgentDeps(llm=None, store=LazyStore(config), data=load_company_data(config), config=config))
    server.run("stdio")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:   # problemy ze startem trafiają na stderr; zgłasza je klient
        print(f"Nie udało się uruchomić serwera MCP Kovalo: {type(exc).__name__}: {exc}", file=sys.stderr)
        sys.exit(1)
