"""Miniprojekt 5: rozmowa z końcowym asystentem. Gotowy program, opcjonalny – uruchom go z katalogu
głównego repozytorium:

    uv run python mini_project_5/src/chat.py

Jedna rozmowa: zapytaj o dokumenty i dane firmy (odpowiada agent przez MCP i pokazuje, skąd wziął
dowody), zapytaj, kto zatwierdza rabat (reguły z Miniprojektu 3), albo złóż wniosek o rabat:
asystent wtedy się zatrzymuje, a ty kolejno odgrywasz role osób zatwierdzających. Ułamek
centa za wiadomość z referencyjnym LLM-em. 'quit' kończy rozmowę.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from dotenv import load_dotenv

from helpers.assistant import assistant_turn, trace_from_record
from helpers.workflow import new_checkpointer
from helpers.config import ConfigError, load_config
from helpers.embedding_cache import require_openai_key
from helpers.llm_notice import other_llm_note
from helpers.mcp_runtime import connect_kovalo
from mini_project_1.src.step6_connect_llm import build_llm
from mini_project_3.src.chat import ask_human
from mini_project_4.src.show_trace import format_trace
from mini_project_5.src.step4_build_assistant import build_assistant

ROOT = Path(__file__).resolve().parents[2]


def main() -> None:
    parser = argparse.ArgumentParser(description="Rozmowa z asystentem Kovalo (na żywo).")
    parser.add_argument("--config-override", type=Path, help="plik YAML z wartościami konfiguracji do zmiany")
    parser.add_argument("--trace", action="store_true", help="po każdej odpowiedzi pokaż, skąd agent wziął dowody")
    args = parser.parse_args()
    load_dotenv(ROOT / ".env", override=True)
    config = load_config(ROOT / "config.yaml", args.config_override)
    require_openai_key("embeddingi zapytań wyszukiwania na serwerze powstają na żywo w OpenAI.")
    note = other_llm_note(config)
    if note:
        print(note + "\n")
    with connect_kovalo(config) as connection:
        assistant = build_assistant(build_llm(config), connection.tools(), config, new_checkpointer())
        print("Asystent Kovalo (narzędzia przez MCP). Pytaj o dokumenty, dostawców, kary umowne albo rabat; 'quit' kończy.\n")
        n = 0
        while (text := input("ty > ").strip()).lower() not in ("quit", "exit"):
            if not text:
                continue
            n += 1
            entry = assistant_turn(assistant, "chat", text, ask_human, connection, turn=n)
            print(f"asystent > {entry['reply']}\n            [ścieżka: {(entry['turn'] or {}).get('kind')}, status: {entry['status']}]")
            trace = trace_from_record(entry["record"])
            if args.trace and trace:
                print(format_trace(trace))
            print()


if __name__ == "__main__":
    try:
        main()
    except (KeyboardInterrupt, EOFError):
        print()
    except NotImplementedError as exc:
        sys.exit(f"Jeszcze nie zaimplementowano: {exc}. Najpierw dokończ ten krok: uv run python mini_project_5/src/check.py")
    except ConfigError as exc:
        sys.exit(f"{exc}\n(zob. „Jeśli utkniesz” w mini_project_5/README.md)")
