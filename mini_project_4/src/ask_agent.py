"""Miniprojekt 4: zadaj agentowi własne pytania. Gotowy program, opcjonalny – uruchom go z katalogu
głównego repozytorium:

    uv run python mini_project_4/src/ask_agent.py

Agent odpowiada na każde pytanie od nowa (bez pamięci: rozmowa to Miniprojekty 3 i 5)
i pokazuje źródła danych i wykonane obliczenia. Ułamek centa za pytanie z referencyjnym LLM-em. Pusty
wiersz albo Ctrl+C kończy program.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from dotenv import load_dotenv

from helpers.agent_trace import Budget, run_question
from helpers.config import ConfigError, load_config
from helpers.embedding_cache import require_openai_key
from helpers.llm_notice import other_llm_note
from mini_project_4.src.run_agent import build_live_deps
from mini_project_4.src.show_trace import format_trace
from mini_project_4.src.step3_build_agent import build_agent

ROOT = Path(__file__).resolve().parents[2]


def main() -> None:
    parser = argparse.ArgumentParser(description="Pytania do agenta z Miniprojektu 4 (na żywo).")
    parser.add_argument("--config-override", type=Path, help="plik YAML z wartościami konfiguracji do zmiany, np. llm.provider")
    args = parser.parse_args()
    load_dotenv(ROOT / ".env", override=True)
    config = load_config(ROOT / "config.yaml", args.config_override)
    require_openai_key("embeddingi zapytań wyszukiwania agenta powstają na żywo w OpenAI.")
    note = other_llm_note(config)
    if note:
        print(note + "\n")
    agent = build_agent(build_live_deps(config))
    print("Pytaj o dostawców, umowy, kary umowne albo rabaty (pusty wiersz kończy program).")
    try:
        while question := input("\n> ").strip():
            print(format_trace(run_question(agent, question, Budget.from_config(config))))
    except (KeyboardInterrupt, EOFError):
        print()


if __name__ == "__main__":
    try:
        main()
    except NotImplementedError as exc:
        sys.exit(f"Jeszcze nie zaimplementowano: {exc}. Najpierw dokończ ten krok: uv run python mini_project_4/src/check.py")
    except ConfigError as exc:  # brak klucza, wartości konfiguracji albo pliku danych: powiedz, co ustawić, bez tracebacku
        sys.exit(f"{exc}\n(zob. „Jeśli utkniesz” i „Ile to kosztuje” w mini_project_4/README.md)")
