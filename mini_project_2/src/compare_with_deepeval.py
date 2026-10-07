"""Opcjonalnie (bez oceny): porównaj swoją ewaluację z DeepEval. Gotowy program: uruchom go z katalogu głównego repozytorium:

    uv sync --extra deepeval                                # raz: instaluje DeepEval 4.2.8
    uv run python mini_project_2/src/compare_with_deepeval.py

Najpierw uruchom answer_questions.py: ten program czyta ZAPISANE rekordy przebiegu
(mini_project_2/output/answers.json), więc każdy oceniający patrzy na te same odpowiedzi.
Potrzebny jest klucz OpenAI: sędzią DeepEval jest referencyjny LLM, openai / gpt-5.4-mini
(około 5 centów za ocenione odpowiedzi). Jeśli nie korzystasz z płatnego API, możesz przeanalizować
zapisane porównanie referencyjne w README.

Dwie metryki frameworka obok twojego pokrycia kluczowych faktów (krok 3) i twojego sędziego (krok 4):
  faithfulness   wierność źródłom: udział twierdzeń odpowiedzi POPARTYCH znalezionym kontekstem
                 (oparcie w źródłach; NIE sprawdza, czy kontekst wystarczał). Domyślnie DeepEval
                 przepuszcza też twierdzenia „borderline”, których kontekst nie potwierdza;
                 ustawiamy penalize_ambiguous_claims=True, żeby liczyły się tylko twierdzenia poparte.
  correctness    sędzia G-Eval: LLM ocenia w skali 0–1, na ile odpowiedź podaje fakty z odpowiedzi
                 wzorcowej i im nie przeczy, według kroków, które sam układa na podstawie naszego kryterium.
Plik wynikowy zachowuje materiały stanowiące podstawę każdej oceny: pytanie, odpowiedź i odpowiedź wzorcową,
twierdzenia i ich werdykty, kroki wygenerowane przez G-Eval oraz uzasadnienie każdego sędziego.
Uzasadnienie sędziego też trzeba sprawdzić: porównaj je z odpowiedzią, źródłem i rubryką.
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

from helpers.config import ConfigError, load_config
from helpers.embedding_cache import require_openai_key
from helpers.gold import load_gold
from helpers.records import load_run
from helpers.text_pl import number

ROOT = Path(__file__).resolve().parents[2]
CORRECTNESS = ("Czy odpowiedź (actual output) podaje fakty z odpowiedzi wzorcowej (expected output) i im nie przeczy? "
               "Dodatkowe poprawne szczegóły są dopuszczalne; brakujące albo sprzeczne fakty obniżają ocenę.")


METRIC_CONFIG = {"faithfulness": {"penalize_ambiguous_claims": True, "eval_mode": "llm"},
                 "correctness": {"criterion": CORRECTNESS, "evaluation_params": ["input", "actual_output", "expected_output"]}}


def make_metrics(model) -> dict:
    """Obie metryki, skonfigurowane jawnie (ustawienia DeepEval użytkownika nie zmienią ich znaczenia)."""
    from deepeval.metrics import FaithfulnessMetric, GEval
    from deepeval.test_case import SingleTurnParams

    return {"faithfulness": FaithfulnessMetric(model=model, include_reason=True, **METRIC_CONFIG["faithfulness"]),
            "correctness": GEval(name="Correctness", model=model, criteria=CORRECTNESS,
                                 evaluation_params=[SingleTurnParams.INPUT, SingleTurnParams.ACTUAL_OUTPUT,
                                                    SingleTurnParams.EXPECTED_OUTPUT])}


def evidence(name: str, metric) -> dict:
    """Co metryka policzyła: twierdzenia i werdykty faithfulness; kroki wygenerowane przez G-Eval."""
    if name == "faithfulness":
        return {"claims": list(getattr(metric, "claims", None) or []),
                "verdicts": [v.model_dump(mode="json") for v in (getattr(metric, "verdicts", None) or [])]}
    return {"evaluation_steps": list(getattr(metric, "evaluation_steps", None) or [])}


async def score_all(cases: list, model) -> list[dict]:
    """Obie metryki dla każdego przypadku, równolegle; nieudana metryka jest zapisana jako None z błędem."""
    async def one(case):
        out = {}
        for name, metric in make_metrics(model).items():
            try:
                await metric.a_measure(case, _show_indicator=False)
                out[name] = {"score": round(float(metric.score), 2), "reason": metric.reason,
                             "cost_usd": metric.evaluation_cost, **evidence(name, metric)}
            except Exception as exc:
                out[name] = {"score": None, "reason": f"{type(exc).__name__}: {exc}", "cost_usd": None}
        return out

    return await asyncio.gather(*(one(case) for case in cases))


def main() -> None:
    load_dotenv(ROOT / ".env", override=True)
    os.environ.setdefault("DEEPEVAL_TELEMETRY_OPT_OUT", "YES")      # żadne dane o użyciu nie opuszczają tego komputera
    config = load_config(ROOT / "config.yaml")
    out_dir = config.path("paths.mini_project_2_output_dir")
    if not (out_dir / "answers.json").is_file() or not (out_dir / "live_report.json").is_file():
        sys.exit("Najpierw uruchom mini_project_2/src/answer_questions.py: ten program porównuje zapisane przez niego odpowiedzi.")
    try:
        from deepeval.test_case import LLMTestCase
    except ImportError:
        sys.exit("DeepEval nie jest zainstalowany. Uruchom: uv sync --extra deepeval")
    require_openai_key("sędzią DeepEval w tym porównaniu jest referencyjny model OpenAI.")

    gold = {q.id: q for q in load_gold(config.path("paths.mini_project_2_questions"))}
    run, records = load_run(out_dir / "answers.json")
    live_report = json.loads((out_dir / "live_report.json").read_text(encoding="utf-8"))
    if live_report.get("run_id") != run["run_id"]:
        sys.exit(f"answers.json (przebieg {run['run_id']}) i live_report.json (przebieg {live_report.get('run_id')}) "
                 "pochodzą z różnych przebiegów. Uruchom ponownie answer_questions.py.")
    live = {r["id"]: r for r in live_report["results"]}
    rows = [row for row in records if row["record"].output is not None and row["record"].output.answerable]
    if not rows:
        sys.exit(f"Przebieg {run['run_id']} nie ma rekordów z odpowiedzią (prób: {len(records)}): nie ma czego porównać.")
    cases = [LLMTestCase(input=row["record"].question, actual_output=row["record"].output.answer,
                         expected_output=gold[row["id"]].reference,
                         retrieval_context=[item.text for item in row["record"].context]) for row in rows]
    model = config.get("reference_llm.model")
    print(f"Ocena odpowiedzi w DeepEval: {len(cases)} (sędzia: {model}) ...")
    scores = asyncio.run(score_all(cases, model))

    table = []
    for row, s in zip(rows, scores):
        live_row = live[row["id"]]
        table.append({"id": row["id"], "key_fact_coverage": live_row["score"]["answer_coverage"],
                      "judge_correct": live_row["verdict"]["correct"], "judge_grounded": live_row["verdict"]["grounded"],
                      "deepeval_faithfulness": s["faithfulness"]["score"],
                      "deepeval_correctness": s["correctness"]["score"],
                      "question": row["record"].question, "answer": row["record"].output.answer,
                      "reference": gold[row["id"]].reference,
                      "context_chunks": [item.chunk_id for item in row["record"].context],
                      "evidence": s})
    cost = sum(s[name]["cost_usd"] or 0 for s in scores for name in s)
    from importlib.metadata import version
    result = {"run_id": run["run_id"], "answered_by": f"{run['provider']} / {run['model']}", "model": model,
              "deepeval_version": version("deepeval"), "config": METRIC_CONFIG, "judge_cost_usd": round(cost, 4),
              "rows": table}
    (out_dir / "deepeval_comparison.json").write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    print(format_table(result))


def format_table(result: dict) -> str:
    def show(value):
        return "-" if value is None else ("tak" if value is True else ("NIE" if value is False else f"{value:.2f}"))
    lines = [f"=== Twoja ewaluacja a DeepEval {result['deepeval_version']} (sędzia: {result['model']}) ===",
             f"Przebieg {result['run_id']}, odpowiedzi: {result['answered_by']}",
             "id    pokrycie  sędzia:        sędzia: oparta  DeepEval faithfulness  DeepEval correctness (G-Eval)",
             "                poprawna       na kontekście"]
    for r in result["rows"]:
        lines.append(f"{r['id']:5} {show(r['key_fact_coverage']):9} {show(r['judge_correct']):14} {show(r['judge_grounded']):15} "
                     f"{show(r['deepeval_faithfulness']):22} {show(r['deepeval_correctness'])}")
    missing = sum(r["deepeval_faithfulness"] is None or r["deepeval_correctness"] is None for r in result["rows"])
    lines.append(f"Brakujące oceny DeepEval: {missing} z {len(result['rows'])} (policzone tutaj, nie ukryte w średniej)")
    lines.append(f"Koszt sędziego: około {number(result['judge_cost_usd'])} USD (szacunek samego DeepEval)")
    return "\n".join(lines)


def format_examples(result: dict) -> str:
    """Odpowiedzi, którym metryka frameworka dała mniej niż 1, z dowodami do sprawdzenia jej uzasadnienia."""
    out = []
    for r in result["rows"]:
        low = [m for m, key in (("faithfulness", "deepeval_faithfulness"), ("correctness", "deepeval_correctness"))
               if r[key] is not None and r[key] < 1]
        if not low:
            continue
        out += [f"--- {r['id']}: {r['question']}", f"ODPOWIEDŹ: {r['answer']}", f"WZORZEC:   {r['reference']}",
                f"znalezione: {', '.join(r['context_chunks'])}"]
        for m in low:
            e = r["evidence"][m]
            out.append(f"{m} {e['score']:.2f}, uzasadnienie: {e['reason']}")
            for v in e.get("verdicts", []):
                if v.get("verdict") != "yes":
                    out.append(f"    werdykt dla twierdzenia {v.get('verdict')}: {v.get('reason')}")
            for i, step in enumerate(e.get("evaluation_steps", []), start=1):
                out.append(f"    krok G-Eval {i} (wygenerowany dla tej odpowiedzi): {step}")
    return "\n".join(out) if out else "(każda odpowiedź dostała ocenę 1,00 w obu metrykach)"


if __name__ == "__main__":
    try:
        main()
    except ConfigError as exc:
        sys.exit(str(exc))
