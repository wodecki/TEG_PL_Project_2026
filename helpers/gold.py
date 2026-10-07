"""Wczytuje zestaw pytań Miniprojektu 2 razem z faktami wzorcowymi. Gotowy plik: nie edytujesz go."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml

from helpers.config import ConfigError


@dataclass(frozen=True)
class GoldQuestion:
    id: str
    question: str
    answerable: bool
    relevant_docs: list[str]
    requires_all: bool
    evidence_facts: list[list[str]]   # każdy fakt: lista akceptowanych wariantów
    key_facts: list[list[str]]
    reference: str


def load_gold(path: Path) -> list[GoldQuestion]:
    path = Path(path)
    if not path.is_file():
        raise ConfigError(f"Nie znaleziono pliku z pytaniami: {path}")
    with path.open(encoding="utf-8") as fh:
        raw = yaml.safe_load(fh)
    try:
        return [GoldQuestion(**q) for q in raw["questions"]]
    except (KeyError, TypeError) as exc:
        raise ConfigError(f"{path}: każde pytanie musi mieć pola GoldQuestion ({exc})") from exc
