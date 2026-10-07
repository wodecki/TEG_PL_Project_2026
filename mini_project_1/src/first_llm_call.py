"""Miniprojekt 1: twoje pierwsze prawdziwe wywołanie LLM-a (krok 6). Gotowy program: uruchom go
z katalogu głównego repozytorium:

    uv run python mini_project_1/src/first_llm_call.py

Korzystając z twoich kroków 1–5, wyszukuje k najlepiej dopasowanych fragmentów (ang. chunks) dla pierwszego pytania testowego, wysyła do
twojego LLM-a ten sam prompt, którego tokeny run_pipeline.py szacuje w raporcie kosztów,
i porównuje twoje oszacowanie z liczbą tokenów policzoną przez dostawcę. Jedno wywołanie:
znacznie poniżej centa, w Ollamie za darmo. Zapisuje mini_project_1/output/llm_call.json.

Aby wypróbować innego dostawcę bez edytowania config.yaml, wpisz wartości do zmiany
w małym pliku YAML i przekaż go opcją --config-override, np. plik z treścią
    llm: {provider: ollama, model: gemma3:4b}
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import date
from pathlib import Path

from dotenv import dotenv_values, load_dotenv

from helpers.config import ConfigError, load_config
from helpers.embedding_cache import underlying_embeddings
from helpers.eval_queries import load_eval_queries
from helpers.llm_notice import other_llm_note
from helpers.prompts import build_prompt
from mini_project_1.src.step1_load_documents import load_documents
from mini_project_1.src.step2_count_tokens import count_tokens
from mini_project_1.src.step3_chunk_documents import chunk_documents
from mini_project_1.src.step4_build_embeddings import build_embeddings
from mini_project_1.src.step5_search import build_vector_store, search
from mini_project_1.src.step6_connect_llm import build_llm, measure_call

ROOT = Path(__file__).resolve().parents[2]


def credential_source(config) -> str:
    """Która zmienna przechowuje klucz do LLM-a i skąd pochodzi – nigdy jej wartość."""
    variable = config.get("llm.api_key_env").get(config.get("llm.provider"))
    if variable is None:
        return "niepotrzebny"
    if dotenv_values(ROOT / ".env").get(variable):
        return f"{variable} z .env"
    return f"{variable} ze środowiska" if os.environ.get(variable) else f"{variable} (brak wartości)"


def main() -> None:
    parser = argparse.ArgumentParser(description="Jedno prawdziwe wywołanie twojego LLM-a (krok 6).")
    parser.add_argument("--config-override", type=Path, help="plik YAML z wartościami konfiguracji do zmiany, np. llm.provider")
    args = parser.parse_args()

    load_dotenv(ROOT / ".env", override=True)
    config = load_config(ROOT / "config.yaml", args.config_override)

    chunks = chunk_documents(load_documents(config), config)
    store = build_vector_store(chunks, build_embeddings(config, underlying=underlying_embeddings()))
    query = load_eval_queries(config.path("paths.eval_queries"))[0]
    hits = search(store, query.question, config.get("retrieval.top_k"))
    prompt = build_prompt(config.get("prompts.system"), [chunk for chunk, _ in hits], query.question)

    note = other_llm_note(config)
    if note:
        print(note + "\n")
    llm = build_llm(config)
    try:
        result = measure_call(llm, prompt)
    except NotImplementedError:
        raise
    except Exception as exc:  # każdy błąd dostawcy: pokaż go w jednym wierszu, nie jako traceback
        raise SystemExit(
            f"Wywołanie {config.get('llm.provider')} / {config.get('llm.model')} nie powiodło się: "
            f"{type(exc).__name__}: {exc}\nZobacz „Krok 6: prawdziwe wywołanie LLM-a się nie udaje” w mini_project_1/README.md."
        ) from None
    record = {
        "date": date.today().isoformat(),
        "credential": credential_source(config),
        "provider": config.get("llm.provider"),
        "model": config.get("llm.model"),
        "question": query.question,
        "context_chunks": [chunk.metadata["chunk_id"] for chunk, _ in hits],
        "answer": result["answer"],
        "input_tokens": result["input_tokens"],
        "output_tokens": result["output_tokens"],
        "estimated_input_tokens": count_tokens(prompt, config),
        "estimate_tokenizer": config.get("tokenizer.encoding"),
        "assumed_output_tokens": config.get("cost.scenario.output_tokens_per_answer"),
    }
    out_dir = config.path("paths.mini_project_1_output_dir")
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "llm_call.json").write_text(json.dumps(record, indent=2, ensure_ascii=False), encoding="utf-8")
    print_call(record)


def print_call(record: dict) -> None:
    print(f"=== Twoje pierwsze wywołanie LLM-a: {record['provider']} / {record['model']} ===")
    if "credential" in record:
        print(f"Klucz:      {record['credential']} (uruchomiono {record['date']})")
    print(f"Pytanie:    {record['question']}")
    print(f"Kontekst:   {', '.join(record['context_chunks'])}")
    print("Odpowiedź:")
    for line in str(record["answer"]).strip().splitlines():
        print(f"  {line}" if line.strip() else "")
    print(f"Tokeny wejściowe: twoje oszacowanie {record['estimated_input_tokens']} ({record['estimate_tokenizer']}), "
          f"dostawca policzył {record['input_tokens']}")
    print(f"Tokeny wyjściowe: scenariusz kosztów zakłada {record['assumed_output_tokens']}, "
          f"ta odpowiedź zużyła {record['output_tokens']}")


if __name__ == "__main__":
    try:
        main()
    except NotImplementedError as exc:
        sys.exit(f"Jeszcze nie napisane: {exc}")
    except ConfigError as exc:
        sys.exit(str(exc))
