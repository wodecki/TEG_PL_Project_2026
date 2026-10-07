"""Miniprojekt 5: cały asystent, oceniany tura po turze według OCZEKIWANEJ ścieżki każdej tury. Gotowy
program – uruchom go z katalogu głównego repozytorium:

    uv run python mini_project_5/src/run_assistant_eval.py

Na żywo: twój LLM interpretuje każdą turę użytkownika (prompt rozumienia z Miniprojektu 5), a agent
odpowiada na pytania o dane przez MCP. Na pauzach odpowiada skrypt (symulowane osoby
zatwierdzające). Program przechodzi rozmowy z Miniprojektu 5, które łączą różne ścieżki, oraz
8 dialogów z Miniprojektu 3: 25 tur użytkownika, około 4,5 centa z referencyjnym LLM-em.

Każda tura jest oceniana tylko pod kątem tego, co definiuje jej oczekiwana ścieżka
(helpers/assistant_eval.py): w każdej turze sama ścieżka i status; pauzy, osoby zatwierdzające
i wniosek tam, gdzie podaje je wzorzec; w turach z pytaniami o dane musi istnieć zapis przebiegu
agenta (ang. trace) i obowiązują sprawdzenia z Miniprojektu 4. Tura skierowana na niewłaściwą ścieżkę nadal
podlega ocenie. Zapisuje mini_project_5/output/assistant_run.json.
"""

from __future__ import annotations

import argparse
import json
import sys
import uuid
from datetime import datetime
from pathlib import Path

import yaml
from dotenv import load_dotenv

from helpers.assistant import assistant_turn, trace_from_record
from helpers.workflow import new_checkpointer
from helpers.assistant_eval import DIMENSIONS, load_conversations, score_assistant_turn, summarise
from helpers.config import ConfigError, load_config
from helpers.embedding_cache import require_openai_key
from helpers.llm_notice import other_llm_note
from helpers.mcp_runtime import connect_kovalo
from helpers.text_pl import number
from mini_project_1.src.step6_connect_llm import build_llm
from mini_project_4.src.step4_score_trace import score_trace
from mini_project_5.src.step4_build_assistant import build_assistant

ROOT = Path(__file__).resolve().parents[2]


def format_assistant_report(data: dict) -> str:
    """Zapisany przebieg jako raport (prowadzący wstawia go też do README)."""
    run, rows = data["run"], data["turns"]
    totals = summarise([r["score"] for r in rows])
    names = {"route": "ścieżka (oczekiwany kind)", "status": "status końcowy", "fields": "pola wyodrębnione przez LLM",
             "pauses": "pauzy (rodzaj, rola, kolejność)",
             "approvers": "osoby zatwierdzające (polityka)", "request": "stan wniosku",
             "agent_trace": "zapis przebiegu agenta tylko tam, gdzie oczekiwany",
             "tool_coverage": "pytania o dane: każde potrzebne wywołanie", "arguments_correct": "pytania o dane: argumenty obliczenia",
             "answer_facts": "pytania o dane: każdy kluczowy fakt", "numbers_backed": "pytania o dane: żadnej liczby bez pokrycia",
             "no_approval_claim": "pytania o dane: brak twierdzenia o akceptacji"}
    lines = [f"=== Asystent z Miniprojektu 5: {run['provider']} / {run['model']}, przez MCP (przebieg {run['run_id']}) ===",
             f"{'Sprawdzenie (gdy definiuje je oczekiwana ścieżka)':52} trafne/ocenione"]
    lines += [f"{names[d]:52} {totals[d][0]}/{totals[d][1]}" for d in DIMENSIONS if totals[d][1]]
    lines.append(f"{'wywołania MCP (nieudane)':52} {run['mcp_calls']} ({run['mcp_failures']})")
    price = run.get("prices")
    cost = (f"; około {100 * (run['input_tokens'] * price['input'] + run['output_tokens'] * price['output']) / 1e6:.1f} centa".replace(".", ",")
            if price else "")
    lines.append(f"{'tokeny (rozumienie + agent)':52} {number(run['input_tokens'])} wejściowych / {number(run['output_tokens'])} wyjściowych{cost}")
    lines += ["", "Tura po turze (sprawdzenia, które nie przeszły):"]
    for r in rows:
        wrong = ", ".join(k for k, v in r["score"].items() if v is False) or "ok"
        kind = (r["entry"].get("turn") or {}).get("kind", "-")
        lines.append(f"  {r['dialogue']:3} {kind:17} {r['entry']['status'] or '-':16} {wrong:30} {r['entry']['user'][:44]}")
    return "\n".join(lines)


class TokenCounter:
    """Liczy tokeny każdego wywołania modelu (callback LangChaina)."""

    def __init__(self):
        from langchain_core.callbacks import BaseCallbackHandler

        counter = self

        class Handler(BaseCallbackHandler):
            def on_llm_end(self, response, **kwargs):
                for generation in response.generations:
                    for g in generation:
                        usage = getattr(getattr(g, "message", None), "usage_metadata", None) or {}
                        counter.input += usage.get("input_tokens", 0)
                        counter.output += usage.get("output_tokens", 0)
        self.input = self.output = 0
        self.handler = Handler()


def main() -> None:
    parser = argparse.ArgumentParser(description="Ocena całego asystenta na rozmowach (na żywo).")
    parser.add_argument("--config-override", type=Path, help="plik YAML z wartościami konfiguracji do zmiany, np. llm.provider")
    parser.add_argument("--only", action="append", metavar="ID", help="uruchom tylko rozmowy o tych identyfikatorach (można powtarzać)")
    args = parser.parse_args()
    load_dotenv(ROOT / ".env", override=True)
    config = load_config(ROOT / "config.yaml", args.config_override)
    require_openai_key("embeddingi zapytań wyszukiwania na serwerze powstają na żywo w OpenAI.")
    note = other_llm_note(config)
    if note:
        print(note + "\n")
    conversations = load_conversations(config)
    if args.only:
        conversations = [c for c in conversations if c["id"] in args.only]
        if not conversations:
            raise ConfigError(f"brak rozmowy o identyfikatorze {args.only}")
    claims = yaml.safe_load(config.path("paths.mini_project_4_questions").read_text(encoding="utf-8"))["approval_claim_phrases"]
    tokens = TokenCounter()
    llm = build_llm(config)
    llm.callbacks = [tokens.handler]                  # sam obiekt modelu: przetrwa podpięcie narzędzi i structured output
    run = {"run_id": f"{datetime.now():%Y%m%dT%H%M%S}-{uuid.uuid4().hex[:8]}", "date": f"{datetime.now():%Y-%m-%d}",
           "provider": config.get("llm.provider"), "model": config.get("llm.model"),
           "policy_version": config.get("policy.version")}
    rows = []
    with connect_kovalo(config) as connection:
        assistant = build_assistant(llm, connection.tools(), config, new_checkpointer())
        for conversation in conversations:
            print(f"{conversation['id']}: {conversation.get('title', '')}")
            skip = None
            for n, t in enumerate(conversation["turns"], start=1):
                if skip:
                    entry = {"user": t["user"], "turn": None, "request": None, "approvers": None, "pauses": [],
                             "status": "skipped", "record": None, "error": f"skipped: {skip}", "reply": None}
                else:
                    scripted = iter(t["resume"])

                    def answer(payload, scripted=scripted):
                        try:
                            return next(scripted)
                        except StopIteration:
                            raise RuntimeError("skrypt nie ma odpowiedzi na tę pauzę") from None
                    entry = assistant_turn(assistant, conversation["id"], t["user"], answer, connection, turn=n)
                    if entry["status"] == "error" and entry["error"] and "przy pauzie" in entry["error"]:
                        skip = entry["error"]
                score = score_assistant_turn(entry, t["expect"], claims, score_trace)
                rows.append({"dialogue": conversation["id"], "entry": entry, "score": score})
                wrong = ", ".join(k for k, v in score.items() if v is False) or "ok"
                print(f"  {entry['status'] or '-':16} {wrong:30} {t['user'][:60]}")
        captures = list(connection.captures)
    run.update(mcp_calls=len(captures), mcp_failures=sum(c["outcome"] != "ok" for c in captures),
               input_tokens=tokens.input, output_tokens=tokens.output,
               prices=(config.get("cost.prices_per_1m_tokens")[run["model"]]
                       if run["model"] == config.get("cost.reference_model") else None))
    out = config.path("paths.mini_project_5_output_dir") / "assistant_run.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    data = {"run": run, "turns": rows, "mcp_captures": captures}
    out.write_text(json.dumps(data, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    print("\n" + format_assistant_report(data))
    print(f"\nZapisano {out.relative_to(ROOT)}.")
    if all(r["entry"]["status"] in ("error", "skipped") for r in rows):
        sys.exit("Żadna tura się nie powiodła: sprawdź błąd powyżej (klucz API, nazwa modelu, dostawca).")


if __name__ == "__main__":
    try:
        main()
    except NotImplementedError as exc:
        sys.exit(f"Jeszcze nie zaimplementowano: {exc}. Najpierw dokończ ten krok: uv run python mini_project_5/src/check.py")
    except ConfigError as exc:
        sys.exit(f"{exc}\n(zob. „Jeśli utkniesz” i „Ile to kosztuje” w mini_project_5/README.md)")
