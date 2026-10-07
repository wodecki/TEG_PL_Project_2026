"""Miniprojekt 2: odpowiedz swoim LLM-em na wszystkie dwanaście pytań i oceń odpowiedzi. Gotowy program: uruchom go z katalogu głównego repozytorium:

    uv run python mini_project_2/src/answer_questions.py

Na żywo: 12 razy wywołuje twój LLM, żeby odpowiedzieć, i do 10 razy jako
sędziego (łącznie około 2 centów z referencyjnym LLM-em, openai / gpt-5.4-mini).
Każdy przebieg otrzymuje własny identyfikator (ang. run ID). Rekordy przebiegu trafiają do
mini_project_2/output/answers.json, a raport czterech poziomów do
mini_project_2/output/live_report.json – ZAWSZE, nawet gdy każde wywołanie się
nie udało, aby poprzedni przebieg nie został omyłkowo uznany za bieżący. Sędzia i opcjonalne
porównanie z DeepEval czytają te zapisane rekordy; nigdy nie odpowiadają od nowa.

Żeby wypróbować innego dostawcę bez edycji config.yaml: --config-override <plik>
(zobacz mini_project_1/src/first_llm_call.py).
"""

from __future__ import annotations

import argparse
import json
import sys
import uuid
import warnings
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

from helpers.config import ConfigError, load_config
from helpers.embedding_cache import underlying_embeddings
from helpers.gold import load_gold
from helpers.llm_notice import other_llm_note
from helpers.records import save_run
from mini_project_1.src.step1_load_documents import load_documents
from mini_project_1.src.step4_build_embeddings import build_embeddings
from mini_project_1.src.step5_search import build_vector_store
from mini_project_1.src.step6_connect_llm import build_llm
from mini_project_2.src.step1_build_contextual_chunks import build_contextual_chunks
from mini_project_2.src.step2_answer_question import answer_question
from mini_project_2.src.step3_score_record import score_record
from mini_project_2.src.step4_judge_record import judge_record

ROOT = Path(__file__).resolve().parents[2]
# structured output w langchain-openai wywołuje niegroźne ostrzeżenia serializacji Pydantic; ukrywamy je
warnings.filterwarnings("ignore", message="Pydantic serializer warnings")


def summarise(rows: list[dict]) -> dict:
    """Cztery poziomy, każdy z własnym mianownikiem."""
    def count(pred, subset):
        return sum(1 for r in subset if pred(r))
    answerable = [r for r in rows if r["answerable"]]
    unanswerable = [r for r in rows if not r["answerable"]]
    answered = [r for r in rows if r["score"]["outcome"] == "answered"]
    answered_answerable = [r for r in answered if r["answerable"]]
    judged = [r for r in answered if r["verdict"]["correct"] is not None]
    return {
        "questions": len(rows),
        "errors": count(lambda r: r["score"]["outcome"] == "error", rows),
        "retrieval_hit": [count(lambda r: r["retrieval_hit"], answerable), len(answerable)],
        "evidence_phrases_complete": [count(lambda r: r["score"]["evidence_phrase_coverage"] == 1, answerable), len(answerable)],
        "answered": [len(answered_answerable), len(answerable)],
        "key_facts_complete": [count(lambda r: r["score"]["answer_coverage"] == 1, answered_answerable), len(answered_answerable)],
        "judge_correct": [count(lambda r: r["verdict"]["correct"], [r for r in judged if r["answerable"]]),
                          len([r for r in judged if r["answerable"]])],
        "judge_grounded": [count(lambda r: r["verdict"]["grounded"], judged), len(judged)],
        "judge_errors": count(lambda r: r["verdict"]["error"] is not None, rows),
        "citations_valid": [count(lambda r: r["score"]["citations_valid"], answered), len(answered)],
        "cites_relevant": [count(lambda r: r["score"]["cites_relevant"], answered_answerable), len(answered_answerable)],
        "refusals_correct": [count(lambda r: r["score"]["refusal"] == "correct", unanswerable), len(unanswerable)],
        "refusals_on_answerable": {kind: count(lambda r, k=kind: r["score"]["refusal"] == k, answerable)
                                   for kind in ("phrases_missing", "phrases_present")},
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Odpowiedz na pytania Miniprojektu 2 i oceń odpowiedzi (na żywo).")
    parser.add_argument("--config-override", type=Path, help="plik YAML z wartościami konfiguracji do zmiany, np. llm.provider")
    args = parser.parse_args()
    load_dotenv(ROOT / ".env", override=True)
    config = load_config(ROOT / "config.yaml", args.config_override)
    note = other_llm_note(config)
    if note:
        print(note + "\n")

    now = datetime.now()
    run = {"run_id": f"{now.strftime('%Y%m%dT%H%M%S')}-{uuid.uuid4().hex[:8]}", "date": now.date().isoformat(),
           "provider": config.get("llm.provider"), "model": config.get("llm.model")}
    store = build_vector_store(build_contextual_chunks(load_documents(config), config),
                               build_embeddings(config, underlying=underlying_embeddings()))
    llm = build_llm(config)
    rows, saved = [], []
    for q in load_gold(config.path("paths.mini_project_2_questions")):
        record = answer_question(q.question, store, llm, config)
        print(f"{q.id} {'answered' if record.output and record.output.answerable else ('refused' if record.output else 'ERROR')}: {q.question}")
        score = score_record(record, q)
        verdict = judge_record(record, q, llm)
        rows.append({"id": q.id, "question": q.question, "answerable": q.answerable,
                     "retrieval_hit": any(item.doc_id in q.relevant_docs for item in record.context),
                     "answer": record.output.answer if record.output else None,
                     "citations": record.output.citations if record.output else None,
                     "error": record.error, "score": score, "verdict": verdict})
        saved.append({"id": q.id, "record": record})
    report = {**run, "summary": summarise(rows), "results": rows}
    out_dir = config.path("paths.mini_project_2_output_dir")
    out_dir.mkdir(parents=True, exist_ok=True)
    save_run(out_dir / "answers.json", run, saved)  # zapis przed każdym wyjściem: nieudany przebieg zastępuje stary
    (out_dir / "live_report.json").write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print()
    print(format_report(report))
    if all(r["score"]["outcome"] == "error" for r in rows):
        raise SystemExit(f"\nŻadna odpowiedź się nie udała (przebieg {run['run_id']} zapisano jako nieudany), np.: {rows[0]['error']}\n"
                         "Zobacz „Krok 6: prawdziwe wywołanie LLM-a się nie udaje” w mini_project_1/README.md.")


def format_report(report: dict) -> str:
    s = report["summary"]
    frac = lambda pair: f"{pair[0]}/{pair[1]}"
    lines = [
        f"=== Ewaluacja Miniprojektu 2: {report['provider']} / {report['model']} (przebieg {report['run_id']}) ===",
        f"Pytania: {s['questions']}   błędy (brak czytelnej odpowiedzi): {s['errors']}   błędy sędziego: {s['judge_errors']}",
        "1 Retrieval   znaleziono trafny dokument:              " + frac(s["retrieval_hit"]) + "  (pytania z odpowiedzią w korpusie)",
        "2 Dowody      wszystkie frazy dowodowe w tekście:      " + frac(s["evidence_phrases_complete"]) + "  (pytania z odpowiedzią w korpusie; przybliżenie)",
        "3 Odpowiedź   udzielono odpowiedzi:                    " + frac(s["answered"]) + "  (pytania z odpowiedzią w korpusie)",
        "              podano wszystkie kluczowe fakty:         " + frac(s["key_facts_complete"]) + "  (udzielone odpowiedzi)",
        "              sędzia: poprawna                         " + frac(s["judge_correct"]) + "  (ocenione przez sędziego, pytania z odpowiedzią w korpusie)",
        "              sędzia: oparta na kontekście             " + frac(s["judge_grounded"]) + "  (ocenione przez sędziego)",
        "4 Odwołania   prawidłowe (obecne, z kontekstu):        " + frac(s["citations_valid"]) + "  (udzielone odpowiedzi)",
        "              odwołanie do trafnego dokumentu:         " + frac(s["cites_relevant"]) + "  (udzielone odpowiedzi, pytania z odpowiedzią w korpusie)",
        "Odmowy        trafne (pytania spoza korpusu):          " + frac(s["refusals_correct"]),
        f"              przy pytaniach z odpowiedzią w korpusie: {s['refusals_on_answerable']['phrases_missing']} bez fraz dowodowych "
        f"(sprawdź wyszukiwanie), {s['refusals_on_answerable']['phrases_present']} z frazami w tekście (prawdopodobnie niesłuszne)",
        "",
        "Według pytań (pokrycie = kluczowe fakty znalezione w odpowiedzi; sędzia = poprawna/oparta na kontekście):",
    ]
    for r in report["results"]:
        sc, v = r["score"], r["verdict"]
        cov = "-" if sc["answer_coverage"] is None else f"{sc['answer_coverage']:.2f}"
        judge = "-" if v["correct"] is None else f"{'tak' if v['correct'] else 'NIE'}/{'tak' if v['grounded'] else 'NIE'}"
        detail = sc["outcome"] + (f" ({sc['refusal']})" if sc["refusal"] else "")
        lines.append(f"  {r['id']}  {detail:22} pokrycie {cov:5} sędzia {judge:7} odwołania {', '.join(r['citations'] or []) or '-'}")
    return "\n".join(lines)


if __name__ == "__main__":
    try:
        main()
    except NotImplementedError as exc:
        sys.exit(f"Jeszcze do napisania: {exc}")
    except ConfigError as exc:
        sys.exit(str(exc))
