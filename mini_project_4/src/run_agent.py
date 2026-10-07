"""Miniprojekt 4: agent odpowiada na pytania wzorcowe, a każdy zapis przebiegu (ang. trace) jest
oceniany. Gotowy program – uruchom go z katalogu głównego repozytorium:

    uv run python mini_project_4/src/run_agent.py
    uv run python mini_project_4/src/run_agent.py --only P1 --only A1     (tylko wybrane pytania)

Na żywo: twój LLM wybiera wywołania narzędzi dla 9 pytań; embeddingi zapytań wyszukiwania
powstają na żywo w OpenAI (potrzebny OPENAI_API_KEY) i nigdy nie trafiają do kursowego cache.
Około 4 centów z referencyjnym LLM-em. Każde pytanie zaczyna się od nowa i ma jeden limit
kroków i czasu (config "agent").

Program zapisuje identyfikator uruchomienia oraz przebiegi odpowiedzi na poszczególne pytania
wraz z ocenami w mini_project_4/output/agent_run.json. Wyświetla osobno wynik każdego sprawdzenia. Zapis dla jednego pytania wyświetlisz poleceniem:
    uv run python mini_project_4/src/show_trace.py P1
"""

from __future__ import annotations

import argparse
import sys
import uuid
import warnings
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

from helpers.agent_trace import AgentDeps, Budget, Trace, load_agent_gold, run_question, save_traces
from helpers.company import load_company_data
from helpers.config import Config, ConfigError, load_config
from helpers.embedding_cache import live_query_embeddings, require_openai_key, underlying_embeddings
from helpers.llm_notice import other_llm_note
from helpers.text_pl import number
from mini_project_1.src.step1_load_documents import load_documents
from mini_project_1.src.step4_build_embeddings import build_embeddings
from mini_project_1.src.step5_search import build_vector_store
from mini_project_1.src.step6_connect_llm import build_llm
from mini_project_2.src.step1_build_contextual_chunks import build_contextual_chunks
from mini_project_4.src.step3_build_agent import build_agent
from mini_project_4.src.step4_score_trace import score_trace

ROOT = Path(__file__).resolve().parents[2]
warnings.filterwarnings("ignore", message="Pydantic serializer warnings")


def build_live_deps(config: Config) -> AgentDeps:
    """Twój LLM, kontekstowy indeks z Miniprojektu 2 (embeddingi zapytań na żywo) i dane firmy."""
    store = build_vector_store(build_contextual_chunks(load_documents(config), config),
                               build_embeddings(config, underlying=underlying_embeddings()))
    store.embedding = live_query_embeddings(config)  # zapytania agenta: embeddingi na żywo, nigdy z cache
    return AgentDeps(llm=build_llm(config), store=store, data=load_company_data(config), config=config)


def new_run(config: Config, architecture: str, deps: AgentDeps) -> dict:
    return {"run_id": f"{datetime.now():%Y%m%dT%H%M%S}-{uuid.uuid4().hex[:8]}", "date": f"{datetime.now():%Y-%m-%d}",
            "provider": config.get("llm.provider"), "model": config.get("llm.model"), "architecture": architecture,
            "policy_version": config.get("policy.version"), "terms_version": deps.data.terms_version,
            "budget": {"max_steps": config.get("agent.max_steps"), "timeout_s": config.get("agent.timeout_s")}}


def run_all(agent, questions, config: Config) -> tuple[list, list[dict]]:
    traces, scores = [], []
    for gold in questions:
        print(f"  {gold.id} ...", end="", flush=True)
        trace = run_question(agent, gold.question, Budget.from_config(config), question_id=gold.id)
        traces.append(trace)
        scores.append(score_trace(trace, gold))
        print(f" {trace.status}, {len(trace.events)} calls, {trace.seconds:.0f} s")
    return traces, scores


def _count(scores: list[dict], key: str, ok) -> str:
    assessed = [s[key] for s in scores if s[key] is not None]
    return f"{sum(ok(v) for v in assessed)}/{len(assessed)}"


def format_report(run: dict, rows: list[dict], config: Config | None = None) -> str:
    """Wyniki przebiegu, test po teście (rows: {"trace": Trace, "score": dict})."""
    traces, scores = [r["trace"] for r in rows], [r["score"] for r in rows]
    uncovered = sum(len(s["uncovered_numbers"]) for s in scores)
    user = sum(len(s["user_stated_numbers"]) for s in scores)
    outcomes = {k: sum(s["outcome"] == k for s in scores) for k in ("answered", "error", "limit")}
    tokens_in, tokens_out = sum(t.input_tokens for t in traces), sum(t.output_tokens for t in traces)
    calls, failed = sum(s["tool_calls"] for s in scores), sum(s["failed_calls"] for s in scores)
    lines = [f"=== Miniprojekt 4, {architecture_label(run['architecture'])}: {run['provider']} / {run['model']}, "
             f"polityka {run['policy_version']}, warunki {run['terms_version']} (przebieg {run['run_id']}) ===",
             f"{'Test (co mierzy)':50} wynik",
             f"{'1 pokrycie narzędzi: każde potrzebne wywołanie':50} {_count(scores, 'tool_coverage', lambda v: v == 1)} pytań",
             f"{'2 poprawne argumenty (gdzie liczono karę)':50} {_count(scores, 'arguments_correct', bool)} pytań",
             f"{'3 fakty: każdy kluczowy fakt w odpowiedzi':50} {_count(scores, 'answer_fact_coverage', lambda v: v == 1)} pytań",
             f"{'4 pokrycie liczb źródłami: liczby bez źródła':50} {uncovered} (podane przez użytkownika, osobno: {user})",
             f"{'5 twierdzenia o zatwierdzeniu w odpowiedziach':50} {sum(s['approval_claim'] for s in scores)}/{len(scores)} odpowiedzi",
             f"{'wyniki przebiegów':50} {outcomes['answered']} answered, {outcomes['error']} error, {outcomes['limit']} limit",
             f"{'wywołania narzędzi':50} {calls} (nieudane: {failed})",
             f"{'tokeny':50} {number(tokens_in)} wejściowych / {number(tokens_out)} wyjściowych" + _cost(run, tokens_in, tokens_out, config),
             "", "Według pytań (narzędzia = spełnione potrzeby; argumenty; fakty; liczby bez źródła):"]
    for trace, s in zip(traces, scores):
        tools = "-" if s["tool_coverage"] is None else f"{s['tool_coverage']:.0%}"
        args = {None: "-", True: "ok", False: "ŹLE"}[s["arguments_correct"]]
        facts = "-" if s["answer_fact_coverage"] is None else f"{s['answer_fact_coverage']:.0%}"
        unbacked = ", ".join(s["uncovered_numbers"]) or "brak"
        claim = "  TWIERDZI, ŻE ZATWIERDZONO" if s["approval_claim"] else ""
        answer = (trace.answer or f"({trace.error})").replace("\n", " ")
        lines.append(f"  {trace.question_id:3} {s['outcome']:8} narzędzia {tools:>4}  argumenty {args:5}  fakty {facts:>4}  "
                     f"bez źródła: {unbacked}{claim}")
        lines.append(f"      {answer[:150]}")
    return "\n".join(lines)


ARCHITECTURES = {"single agent": "jeden agent", "supervisor + 3 specialists": "agent koordynujący i 3 specjalistów",
                 "single agent over MCP": "jeden agent przez MCP"}


def architecture_label(stored: str) -> str:
    """Polska nazwa architektury do wyświetlenia; w zapisanym przebiegu zostaje wartość kodu."""
    return ARCHITECTURES.get(stored, stored)


def format_saved_run(data: dict) -> str:
    """format_report dla przebiegu zapisanego przez save_traces (JSON, już wczytany)."""
    rows = [{**row, "trace": Trace.model_validate(row["trace"])} for row in data["traces"]]
    return format_report(data["run"], rows, load_config(ROOT / "config.yaml"))


def _cost(run: dict, tokens_in: int, tokens_out: int, config: Config | None) -> str:
    if config is None or run["model"] != config.get("cost.reference_model"):
        return ""
    price = config.get("cost.prices_per_1m_tokens")[config.get("cost.reference_model")]
    cents = 100 * (tokens_in * price['input'] + tokens_out * price['output']) / 1e6
    return f"; około {cents:.1f} centa".replace(".", ",")      # „około 3,8 centa” (ułamek: dopełniacz l. poj.)


def main() -> None:
    parser = argparse.ArgumentParser(description="Uruchamia agenta z Miniprojektu 4 na pytaniach wzorcowych (na żywo).")
    parser.add_argument("--config-override", type=Path, help="plik YAML z wartościami konfiguracji do zmiany, np. llm.provider")
    parser.add_argument("--only", action="append", metavar="ID", help="uruchom tylko pytania o tych identyfikatorach (można powtarzać)")
    args = parser.parse_args()
    load_dotenv(ROOT / ".env", override=True)
    config = load_config(ROOT / "config.yaml", args.config_override)
    require_openai_key("embeddingi zapytań wyszukiwania agenta powstają na żywo w OpenAI.")
    note = other_llm_note(config)
    if note:
        print(note + "\n")
    questions = load_agent_gold(config.path("paths.mini_project_4_questions"))
    if args.only:
        questions = [q for q in questions if q.id in args.only]
        if not questions:
            raise ConfigError(f"nie ma pytania o identyfikatorze {args.only}")
    deps = build_live_deps(config)
    run = new_run(config, "single agent", deps)
    print(f"Uruchamiam pytania ({len(questions)}) z {run['provider']} / {run['model']}:")
    traces, scores = run_all(build_agent(deps), questions, config)
    out = config.path("paths.mini_project_4_output_dir") / "agent_run.json"
    save_traces(out, run, traces, scores)
    print("\n" + format_report(run, [{"trace": t, "score": s} for t, s in zip(traces, scores)], config))
    print(f"\nZapisano {out.relative_to(ROOT)}. Jeden zapis przebiegu obejrzysz tak: uv run python mini_project_4/src/show_trace.py P1")
    if all(s["outcome"] != "answered" for s in scores):
        sys.exit("Żadne pytanie się nie powiodło: sprawdź błąd powyżej (klucz API, nazwa modelu, dostawca).")


if __name__ == "__main__":
    try:
        main()
    except NotImplementedError as exc:
        sys.exit(f"Jeszcze nie zaimplementowano: {exc}. Najpierw dokończ ten krok: uv run python mini_project_4/src/check.py")
    except ConfigError as exc:  # brak klucza, wartości konfiguracji albo pliku danych: powiedz, co ustawić, bez tracebacku
        sys.exit(f"{exc}\n(zob. „Jeśli utkniesz” i „Ile to kosztuje” w mini_project_4/README.md)")
