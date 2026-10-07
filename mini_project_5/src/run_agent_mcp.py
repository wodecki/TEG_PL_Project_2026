"""Miniprojekt 5: dziewięć pytań z Miniprojektu 4, na które odpowiada agent przez MCP. Gotowy program –
uruchom go z katalogu głównego repozytorium:

    uv run python mini_project_5/src/run_agent_mcp.py
    uv run python mini_project_5/src/run_agent_mcp.py --only P1

Na żywo, około 4 centów z referencyjnym LLM-em. Ten sam agent, prompt, pytania, limity i ocena
co w mini_project_4/src/run_agent.py; różnią się tylko narzędzia: pochodzą z serwera MCP Kovalo
(uruchamianego przez stdio). Zapisuje mini_project_5/output/agent_mcp_run.json i wypisuje raport
obok bezpośredniego przebiegu z Miniprojektu 4 (twojego albo przebiegu referencyjnego kursu).

Porównuj wyniki sprawdzeń obu przebiegów, zamiast oczekiwać identycznych planów wywołań: dwa przebiegi
tego samego agenta mogą wybrać różne, równie poprawne wywołania.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from types import SimpleNamespace

from dotenv import load_dotenv
from langchain.agents import create_agent

from helpers.agent_trace import load_agent_gold, load_traces, save_traces, tool_errors
from helpers.company import load_company_data
from helpers.config import ConfigError, load_config
from helpers.embedding_cache import require_openai_key
from helpers.llm_notice import other_llm_note
from helpers.mcp_runtime import connect_kovalo
from mini_project_1.src.step6_connect_llm import build_llm
from mini_project_4.src.run_agent import format_report, format_saved_run, run_all  # noqa: F401  (format_saved_run: README blocks)

ROOT = Path(__file__).resolve().parents[2]


def main() -> None:
    parser = argparse.ArgumentParser(description="Pytania z Miniprojektu 4 przez agenta z narzędziami MCP (na żywo).")
    parser.add_argument("--config-override", type=Path, help="plik YAML z wartościami konfiguracji do zmiany, np. llm.provider")
    parser.add_argument("--only", action="append", metavar="ID", help="uruchom tylko pytania o tych identyfikatorach (można powtarzać)")
    args = parser.parse_args()
    load_dotenv(ROOT / ".env", override=True)
    config = load_config(ROOT / "config.yaml", args.config_override)
    require_openai_key("embeddingi zapytań wyszukiwania na serwerze powstają na żywo w OpenAI.")
    note = other_llm_note(config)
    if note:
        print(note + "\n")
    questions = load_agent_gold(config.path("paths.mini_project_4_questions"))
    if args.only:
        questions = [q for q in questions if q.id in args.only]
        if not questions:
            raise ConfigError(f"brak pytania o identyfikatorze {args.only}")
    from mini_project_4.src.run_agent import new_run

    with connect_kovalo(config) as connection:
        agent = create_agent(build_llm(config), connection.tools(), system_prompt=config.get("prompts.agent_system"),
                             middleware=[tool_errors()])
        run = new_run(config, "single agent over MCP", SimpleNamespace(data=load_company_data(config)))
        print(f"Uruchamiam pytania ({len(questions)}) z {run['provider']} / {run['model']} (narzędzia przez MCP):")
        traces, scores = run_all(agent, questions, config)
        captures = list(connection.captures)
    out = config.path("paths.mini_project_5_output_dir") / "agent_mcp_run.json"
    save_traces(out, {**run, "mcp_calls": len(captures),
                      "mcp_failures": sum(c["outcome"] != "ok" for c in captures)}, traces, scores)
    print("\n" + format_report(run, [{"trace": t, "score": s} for t, s in zip(traces, scores)], config))
    direct = config.path("paths.mini_project_4_output_dir") / "agent_run.json"
    if not direct.is_file():
        direct = ROOT / "mini_project_4" / "reference_traces" / "agent_run.json"
    other, rows = load_traces(direct)
    print(f"\nDla porównania agent bezpośredni ({direct.relative_to(ROOT)}):\n" + format_report(other, rows, config))
    print(f"\nZapisano {out.relative_to(ROOT)}.")
    if all(s["outcome"] != "answered" for s in scores):
        sys.exit("Żadne pytanie się nie powiodło: sprawdź błąd powyżej (klucz API, nazwa modelu, dostawca).")


if __name__ == "__main__":
    try:
        main()
    except NotImplementedError as exc:
        sys.exit(f"Jeszcze nie zaimplementowano: {exc}. Najpierw dokończ ten krok: uv run python mini_project_5/src/check.py")
    except ConfigError as exc:  # brak klucza, wartości w konfiguracji, pliku danych albo serwer, który nie startuje
        sys.exit(f"{exc}\n(zob. „Jeśli utkniesz” i „Ile to kosztuje” w mini_project_5/README.md)")
