"""Miniprojekt 3: dialogi wzorcowe z twoim LLM-em i ocena każdego etapu. Gotowy program – uruchom go z katalogu głównego repozytorium:

    uv run python mini_project_3/src/run_dialogues.py

Na żywo: twój LLM odczytuje każdą turę użytkownika (13 wywołań) i odpowiada na jedno
pytanie o dokumenty; reprezentacja wektorowa (ang. embedding) przekształconego pytania jest obliczana przez OpenAI
(potrzebny OPENAI_API_KEY). Około 1,7 centa z referencyjnym LLM-em. Na pauzy odpowiada
skrypt (odpowiedzi `resume` każdego dialogu): to symulacja osób zatwierdzających.

Program zapisuje przebieg (identyfikator przebiegu, zapis każdej tury) do
mini_project_3/output/dialogues.json i wypisuje ocenę każdego etapu. check.py odtwarza
te same dialogi z IDEALNYM zrozumieniem; porównanie obu wyników wskazuje, co twój LLM
odczytał źle (sprawdź faktyczne tury). Jeśli tura zatrzymuje się częściej, niż
przewiduje skrypt, jej pauza zostaje anulowana, wszystko, co zaobserwowano do tej pory,
zostaje zachowane, a reszta dialogu jest oznaczona jako pominięta (i nadal liczona).
"""

from __future__ import annotations

import argparse
import json
import sys
import uuid
import warnings
from datetime import datetime
from pathlib import Path

import yaml
from dotenv import load_dotenv

from helpers.config import ConfigError, load_config
from helpers.embedding_cache import live_query_embeddings, require_openai_key, underlying_embeddings
from helpers.llm_notice import other_llm_note
from helpers.workflow import CopilotDeps, run_turn, new_checkpointer
from mini_project_1.src.step1_load_documents import load_documents
from mini_project_1.src.step4_build_embeddings import build_embeddings
from mini_project_1.src.step5_search import build_vector_store
from mini_project_1.src.step6_connect_llm import build_llm
from mini_project_2.src.step1_build_contextual_chunks import build_contextual_chunks
from mini_project_3.src.step4_copilot_graph import build_copilot_graph
from mini_project_3.src.step5_score_transcript import score_transcript

ROOT = Path(__file__).resolve().parents[2]
warnings.filterwarnings("ignore", message="Pydantic serializer warnings")


def main() -> None:
    parser = argparse.ArgumentParser(description="Dialogi Miniprojektu 3 z twoim LLM-em (na żywo).")
    parser.add_argument("--config-override", type=Path, help="plik YAML z wartościami konfiguracji do zmiany, np. llm.provider")
    args = parser.parse_args()
    load_dotenv(ROOT / ".env", override=True)
    config = load_config(ROOT / "config.yaml", args.config_override)
    require_openai_key("embeddingi przekształconych pytań o dokumenty są obliczane na bieżąco przez OpenAI.")
    note = other_llm_note(config)
    if note:
        print(note + "\n")

    store = build_vector_store(build_contextual_chunks(load_documents(config), config),
                               build_embeddings(config, underlying=underlying_embeddings()))
    store.embedding = live_query_embeddings(config)  # przepisane pytania: embedding na żywo, nigdy z cache
    graph = build_copilot_graph(CopilotDeps(llm=build_llm(config), store=store, config=config), new_checkpointer())
    with config.path("paths.mini_project_3_dialogues").open(encoding="utf-8") as fh:
        dialogues = yaml.safe_load(fh)["dialogues"]

    now = datetime.now()
    run = {"run_id": f"{now.strftime('%Y%m%dT%H%M%S')}-{uuid.uuid4().hex[:8]}", "date": now.date().isoformat(),
           "provider": config.get("llm.provider"), "model": config.get("llm.model"), "policy": config.get("policy.version")}
    transcript, gold = [], []
    for dialogue in dialogues:
        thread = f"{run['run_id']}-{dialogue['id']}"
        failed = None
        for t in dialogue["turns"]:
            if failed:  # opisana zasada: po nieudanej turze reszta dialogu się nie wykonuje
                entry = {"user": t["user"], "turn": None, "request": None, "approvers": None, "pauses": [],
                         "status": "error", "error": f"pominięte: wcześniejsza tura się nie udała ({failed})"}
            else:
                scripted = iter(t["resume"])

                def answer(payload, scripted=scripted):
                    try:
                        return next(scripted)
                    except StopIteration:
                        raise RuntimeError("skrypt nie ma odpowiedzi na tę pauzę (więcej pauz, niż przewidziano)") from None

                entry = run_turn(graph, thread, t["user"], answer)
                if entry["status"] == "error" and entry["error"] and "przy pauzie" in entry["error"]:
                    failed = entry["error"]
            transcript.append({"dialogue": dialogue["id"], **entry})
            gold.append(t["expect"])
            print(f"{dialogue['id']}  {entry['status']:16} {t['user'][:70]}")
    score = score_transcript(transcript, gold)
    report = {**run, "score": {k: v for k, v in score.items() if k != "details"}, "details": score["details"],
              "transcript": transcript}
    out_dir = config.path("paths.mini_project_3_output_dir")
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "dialogues.json").write_text(json.dumps(report, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    print()
    print(format_report(report))


def format_report(report: dict) -> str:
    s = report["score"]
    frac = lambda pair: f"{pair[0]}/{pair[1]}"
    lines = [
        f"=== Dialogi Miniprojektu 3: {report['provider']} / {report['model']}, polityka {report['policy']} (przebieg {report['run_id']}) ===",
        "Etap                              trafne/ocenione",
        f"1 kierowanie (rodzaj wiadomości)  {frac(s['route'])}",
        f"2 pola odczytane przez LLM        {frac(s['fields'])}",
        f"3 stan wniosku po aktualizacji    {frac(s['request'])}",
        f"4 osoby zatwierdzające (polityka) {frac(s['approvers'])}",
        f"5 pauzy (typ, rola, kolejność)    {frac(s['pauses'])}",
        f"6 status końcowy                  {frac(s['status'])}",
        f"błędy (nieudane tury)             {s['errors']}",
        "",
        "Tura po turze (etapy z błędem):",
    ]
    for entry, detail in zip(report["transcript"], report["details"]):
        kind = (entry.get("turn") or {}).get("kind", "-")
        wrong = ", ".join(detail["wrong"]) or "ok"
        lines.append(f"  {entry['dialogue']}  {kind:17} {entry['status'] or '-':16} {wrong:22} {entry['user'][:48]}")
    return "\n".join(lines)


if __name__ == "__main__":
    try:
        main()
    except NotImplementedError as exc:
        sys.exit(f"Jeszcze do napisania: {exc}")
    except ConfigError as exc:
        sys.exit(str(exc))
