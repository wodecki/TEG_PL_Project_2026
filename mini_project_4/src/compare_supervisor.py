"""Miniprojekt 4: te same pytania, na które odpowiada agent koordynujący (ang. supervisor) z trzema agentami specjalistycznymi.
Gotowy program – uruchom go z katalogu głównego repozytorium:

    uv run python mini_project_4/src/compare_supervisor.py        (opcjonalnie: na żywo, około 14 centów)

Częścią Miniprojektu 4 jest analiza przebiegu tego programu zapisanego przez kurs; samodzielne
uruchomienie jest opcjonalne. Zob. „Jeden agent czy zespół?” w mini_project_4/README.md.

Zespół: agent koordynujący, którego narzędziami są trzej agenci specjalistyczni, każdy z częścią
TWOICH narzędzi (wzorzec supervisora „przez narzędzia”):
    documents_analyst   search_documents
    data_analyst        get_contract_terms, get_supplier_otif, get_invoice_value, calculate_otif_penalty
    policy_checker      check_discount_policy
Ten sam model, te same narzędzia, te same pytania, ta sama ocena, jeden limit na pytanie. Każde
wywołanie specjalisty zostaje w zapisie przebiegu (ang. trace), zagnieżdżone pod wywołaniem
supervisora; odpowiedź specjalisty jest zapisywana jako "worker_summary", nigdy jako dowód.

Program zapisuje mini_project_4/output/supervisor_run.json i wypisuje raport obok twojego
przebiegu z jednym agentem (jeśli uruchomisz wcześniej run_agent.py) albo obok przebiegu
referencyjnego kursu.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from dotenv import load_dotenv

from helpers.agent_trace import (Budget, load_agent_gold, load_traces, run_question, save_traces, tool_errors,
                                 worker_result)
from langchain_core.tools import tool
from langchain.agents import create_agent
from helpers.config import ConfigError, load_config
from helpers.embedding_cache import require_openai_key
from helpers.llm_notice import other_llm_note
from mini_project_4.src.run_agent import build_live_deps, format_report, new_run
from mini_project_4.src.step3_build_agent import build_tools
from mini_project_4.src.step4_score_trace import score_trace

ROOT = Path(__file__).resolve().parents[2]

WORKERS = {
    "documents_analyst": (["search_documents"],
                          "Za pomocą search_documents ustalasz, co mówią dokumenty Kovalo (umowy, polityki, notatki ze "
                          "spotkań, raporty). W odpowiedzi podaj istotne fakty i identyfikatory dokumentów, z których "
                          "pochodzą. Nigdy nie wymyślaj liczb."),
    "data_analyst": (["get_contract_terms", "get_supplier_otif", "get_invoice_value", "calculate_otif_penalty"],
                     "Odpowiadasz na pytania o warunki umów z dostawcami, miesięczny OTIF, faktury i kary za OTIF, "
                     "korzystając ze swoich narzędzi. Sprawdź penalty_clause, zanim uznasz, że należy się jakakolwiek "
                     "kara. Podaj każdą liczbę wraz z jej źródłem (identyfikator umowy, dane, obliczenie). Jeśli "
                     "brakuje danych, napisz, czego brakuje. Nigdy nie wymyślaj liczb."),
    "policy_checker": (["check_discount_policy"],
                       "Za pomocą check_discount_policy ustalasz, kto musi zatwierdzić rabat i dlaczego. Niczego nie "
                       "zatwierdzasz."),
}
SUPERVISOR = (
    "Pracujesz dla zarządu Kovalo i koordynujesz pracę trzech specjalistów: documents_analyst (co mówią "
    "dokumenty), data_analyst (warunki OTIF z umów, wartości OTIF, faktury, obliczenia kar) i policy_checker "
    "(kto musi zatwierdzić rabat). Każdemu potrzebnemu specjaliście daj pełne zadanie, zrozumiałe bez tej "
    "rozmowy: specjaliści jej nie widzą. Potem odpowiedz menedżerowi wyłącznie na podstawie tego, co zwrócili: "
    "zachowaj identyfikatory dokumentów i przy każdej liczbie podaj jej źródło. Jeśli czegoś brakuje, napisz, "
    "czego. Nie możesz niczego zatwierdzić, przesłać ani obiecać. Odpowiadaj krótko, w języku pytania, także "
    "gdy dokumenty lub dane są w innym języku: na pytanie po polsku odpowiadaj po polsku, na pytanie "
    "po angielsku – po angielsku.")


def worker_tool(name: str, worker, tool_names: list[str], budget_box: dict):
    """Agent-specjalista opakowany jako jedno narzędzie supervisora: jego jedynym argumentem jest zadanie."""
    def ask(task: str) -> dict:
        return worker_result(run_question(worker, task, budget_box["budget"], agent_name=name))

    ask.__doc__ = (f"Przekazuje zadanie specjaliście {name} (narzędzia: {', '.join(tool_names)}). "
                   "task: pełne polecenie, zrozumiałe bez tej rozmowy.")
    return tool(f"ask_{name}")(ask)


def build_supervisor(deps, budget_box: dict):
    """Agent-supervisor. budget_box["budget"] to Budget bieżącego pytania, wspólny dla wszystkich specjalistów."""
    tools = {t.name: t for t in build_tools(deps)}
    worker_tools = [worker_tool(name, create_agent(deps.llm, [tools[n] for n in tool_names], system_prompt=prompt,
                                                   middleware=[tool_errors()]),
                                tool_names, budget_box)
                    for name, (tool_names, prompt) in WORKERS.items()]
    return create_agent(deps.llm, worker_tools, system_prompt=SUPERVISOR, middleware=[tool_errors()])


def main() -> None:
    parser = argparse.ArgumentParser(description="Uruchamia porównanie z supervisorem i specjalistami (na żywo).")
    parser.add_argument("--config-override", type=Path, help="plik YAML z wartościami konfiguracji do zmiany, np. llm.provider")
    parser.add_argument("--only", action="append", metavar="ID", help="uruchom tylko pytania o tych identyfikatorach (można powtarzać)")
    args = parser.parse_args()
    load_dotenv(ROOT / ".env", override=True)
    config = load_config(ROOT / "config.yaml", args.config_override)
    require_openai_key("embeddingi zapytań wyszukiwania specjalistów powstają na żywo w OpenAI.")
    note = other_llm_note(config)
    if note:
        print(note + "\n")
    questions = load_agent_gold(config.path("paths.mini_project_4_questions"))
    if args.only:
        questions = [q for q in questions if q.id in args.only]
        if not questions:
            raise ConfigError(f"nie ma pytania o identyfikatorze {args.only}")
    deps = build_live_deps(config)
    run = new_run(config, "supervisor + 3 specialists", deps)
    box: dict = {}
    supervisor = build_supervisor(deps, box)
    print(f"Uruchamiam pytania ({len(questions)}) z {run['provider']} / {run['model']}:")
    traces, scores = [], []
    for gold in questions:
        print(f"  {gold.id} ...", end="", flush=True)
        box["budget"] = Budget.from_config(config)
        trace = run_question(supervisor, gold.question, box["budget"], question_id=gold.id, agent_name="supervisor")
        traces.append(trace)
        scores.append(score_trace(trace, gold))
        print(f" {trace.status}, {len(trace.events)} calls, {trace.seconds:.0f} s")
    out = config.path("paths.mini_project_4_output_dir") / "supervisor_run.json"
    save_traces(out, run, traces, scores)
    print("\n" + format_report(run, [{"trace": t, "score": s} for t, s in zip(traces, scores)], config))
    single = config.path("paths.mini_project_4_output_dir") / "agent_run.json"
    if not single.is_file():
        single = ROOT / "mini_project_4" / "reference_traces" / "agent_run.json"
    if single.is_file():
        other, rows = load_traces(single)
        print(f"\nDla porównania jeden agent ({single.relative_to(ROOT)}):\n" + format_report(other, rows, config))
    print(f"\nZapisano {out.relative_to(ROOT)}. Porównaj jedno pytanie: "
          "uv run python mini_project_4/src/show_trace.py P1 --run supervisor")


if __name__ == "__main__":
    try:
        main()
    except NotImplementedError as exc:
        sys.exit(f"Jeszcze nie zaimplementowano: {exc}. Najpierw dokończ ten krok: uv run python mini_project_4/src/check.py")
    except ConfigError as exc:  # brak klucza, wartości konfiguracji albo pliku danych: powiedz, co ustawić, bez tracebacku
        sys.exit(f"{exc}\n(zob. „Jeśli utkniesz” i „Ile to kosztuje” w mini_project_4/README.md)")
