"""Wczytuje zestawy pytań ewaluacyjnych. Gotowy plik: nie edytujesz go."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml


@dataclass(frozen=True)
class EvalQuery:
    query_id: str
    question: str
    relevant_docs: list[str]


def load_eval_queries(path: Path) -> list[EvalQuery]:
    path = Path(path)
    if not path.is_file():
        raise FileNotFoundError(f"Nie znaleziono pliku z pytaniami ewaluacyjnymi: {path}")
    with path.open(encoding="utf-8") as fh:
        raw = yaml.safe_load(fh)
    items = raw.get("queries") if isinstance(raw, dict) else None
    if not items:
        raise ValueError(f"{path}: oczekiwano niepustej listy 'queries'")
    return [
        EvalQuery(query_id=str(q["query_id"]), question=str(q["question"]), relevant_docs=list(q["relevant_docs"]))
        for q in items
    ]
