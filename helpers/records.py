"""Schematy odpowiedzi i zapis przebiegu wspólne dla Miniprojektów 2–5. Gotowy plik: nie edytujesz go.

Model wypełnia `Answer` (albo `Verdict`) w odpowiedzi o ustalonym schemacie (ang. structured output).
Wszystko o tym, jak powstała odpowiedź – pytanie, dokładny kontekst, który widział model, błąd –
trafia do `RunRecord`. To właśnie on jest czytany przy każdej ewaluacji.
"""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, Field


class Answer(BaseModel):
    """Odpowiedź oparta na dokumentach z kontekstu."""

    answer: str = Field(description="odpowiedź oparta wyłącznie na faktach z dokumentów kontekstu")
    citations: list[str] = Field(description="identyfikatory dokumentów kontekstu, z których korzysta odpowiedź, np. POL-001")
    answerable: bool = Field(description="false, jeśli dokumenty kontekstu nie zawierają odpowiedzi")


class Verdict(BaseModel):
    """Werdykt sędziego (LLM-as-judge) dla jednej odpowiedzi."""

    correct: bool = Field(description="true, jeśli odpowiedź podaje fakty z odpowiedzi wzorcowej i im nie przeczy")
    grounded: bool = Field(description="true, jeśli każde twierdzenie odpowiedzi jest poparte kontekstem")
    reason: str = Field(description="jedno lub dwa zdania uzasadnienia werdyktu")


class ContextItem(BaseModel):
    """Jeden znaleziony chunk, dokładnie w takiej postaci, w jakiej zobaczył go model."""

    doc_id: str
    chunk_id: str
    text: str


class RunRecord(BaseModel):
    """Jedno pytanie z odpowiedzią: dane wejściowe, kontekst oraz Answer albo błąd."""

    question: str
    context: list[ContextItem]
    output: Answer | None = None
    error: str | None = None


def save_run(path: Path, run: dict, records: list[dict]) -> None:
    """Zapisuje jeden przebieg jako jeden plik JSON: jego pochodzenie (`run`: run_id, data,
    dostawca, model) i wpisy {"id": ..., "record": RunRecord}."""
    rows = [{**row, "record": row["record"].model_dump()} for row in records]
    Path(path).write_text(json.dumps({"run": run, "records": rows}, indent=2, ensure_ascii=False), encoding="utf-8")


def load_run(path: Path) -> tuple[dict, list[dict]]:
    """Odwrotność save_run: (run, records)."""
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return data["run"], [{**row, "record": RunRecord.model_validate(row["record"])} for row in data["records"]]
