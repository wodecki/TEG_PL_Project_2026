"""Opcjonalnie (bez oceny): rozmowa z copilotem Kovalo. Gotowy program – uruchom go z katalogu głównego repozytorium:

    uv run python mini_project_3/src/chat.py

Na żywo: jedno wywołanie LLM-a na wiadomość (ułamek centa z referencyjnym LLM-em); reprezentacje wektorowe
pytań o dokumenty (ang. embeddings) są obliczane na bieżąco przez OpenAI. Gdy przepływ pracy
(ang. workflow) zatrzymuje się w oczekiwaniu na akceptację,
to ty odgrywasz wskazaną rolę. To symulacja: nic nie trafia do CRM-u i nikt nic nie obiecuje
klientowi. Wpisz „quit”, aby zakończyć.
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
from helpers.text_pl import human_answer, number
from helpers.workflow import CopilotDeps, run_turn, new_checkpointer
from mini_project_1.src.step1_load_documents import load_documents
from mini_project_1.src.step4_build_embeddings import build_embeddings
from mini_project_1.src.step5_search import build_vector_store
from mini_project_1.src.step6_connect_llm import build_llm
from mini_project_2.src.step1_build_contextual_chunks import build_contextual_chunks
from mini_project_3.src.step4_copilot_graph import build_copilot_graph

ROOT = Path(__file__).resolve().parents[2]
warnings.filterwarnings("ignore", message="Pydantic serializer warnings")
EXCEPTION_NAMES = {"clearance": "wyprzedaż końcówek", "strategic_account": "klient strategiczny",
                   "competitor_offer": "oferta konkurencji"}


def describe_request(request: dict) -> str:
    flags = [label for name, label in EXCEPTION_NAMES.items() if request.get(name)]
    margin = "nie podano" if request.get("margin_after_pct") is None else f"{number(request['margin_after_pct'])}%"
    return (f"klient: {request.get('customer') or '-'}, produkt: {request.get('product') or '-'}, "
            f"rabat: {number(request.get('discount_pct'))}%, marża po rabacie: {margin}, "
            f"wyjątki: {', '.join(flags) or 'brak'}, wersja wniosku: {request.get('revision')}")


def ask_human(payload: dict):
    """Pyta osobę przy klawiaturze; polskie (albo angielskie) odpowiedzi zamienia na wartości, których oczekuje graf."""
    if payload["type"] == "clarification":
        return human_answer("clarification", input(f"  [doprecyzowanie] {payload['question']} > "))
    roles = ", ".join(payload["approvers"])
    print(f"  [akceptacja, symulacja] Wniosek, tak jak zrozumiał go copilot:\n    {describe_request(payload['request'])}")
    return human_answer("approval", input(f"  Rola: {payload['role']} (wymagani: {roles}). zatwierdź / odrzuć / anuluj > "))


def main() -> None:
    parser = argparse.ArgumentParser(description="Rozmowa z copilotem Kovalo.")
    parser.add_argument("--config-override", type=Path, help="plik YAML z wartościami konfiguracji do zmiany")
    args = parser.parse_args()
    load_dotenv(ROOT / ".env", override=True)
    config = load_config(ROOT / "config.yaml", args.config_override)
    require_openai_key("embeddingi pytań o dokumenty są obliczane na bieżąco przez OpenAI.")
    note = other_llm_note(config)
    if note:
        print(note + "\n")
    store = build_vector_store(build_contextual_chunks(load_documents(config), config),
                               build_embeddings(config, underlying=underlying_embeddings()))
    store.embedding = live_query_embeddings(config)
    graph = build_copilot_graph(CopilotDeps(llm=build_llm(config), store=store, config=config), new_checkpointer())
    print("Copilot Kovalo. Zapytaj o dokumenty albo o rabat; „quit” kończy rozmowę.\n")
    while (text := input("ty > ").strip()).lower() not in ("quit", "exit"):
        if text:
            entry = run_turn(graph, "chat", text, ask_human)
            print(f"copilot > {entry['reply']}\n          [status: {entry['status']}]\n")


if __name__ == "__main__":
    try:
        main()
    except (KeyboardInterrupt, EOFError):
        print()
    except ConfigError as exc:
        sys.exit(str(exc))
