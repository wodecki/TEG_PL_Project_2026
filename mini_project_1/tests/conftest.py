"""Wspólne dane i obiekty przygotowywane do testów (ang. fixtures) Miniprojektu 1.
Testy nie wymagają klucza API."""

from __future__ import annotations

import copy
import csv
from pathlib import Path

import pytest
from langchain_core.embeddings import DeterministicFakeEmbedding, Embeddings

from helpers.config import Config, load_config

ROOT = Path(__file__).resolve().parents[2]
CATALOG_COLUMNS = ["doc_id", "file", "title", "doc_type", "department", "owner", "effective_date", "language"]


@pytest.fixture(scope="session")
def config() -> Config:
    return load_config(ROOT / "config.yaml")


def config_with(config: Config, **paths) -> Config:
    """Kopia konfiguracji projektu z podmienionymi niektórymi wartościami `paths.*` (np. corpus_dir=tmp_path)."""
    raw = copy.deepcopy(config.raw)
    raw["paths"].update({key: str(value) for key, value in paths.items()})
    return Config(root=config.root, raw=raw)


def config_with_llm(config: Config, **llm) -> Config:
    """Kopia konfiguracji projektu z podmienionymi niektórymi wartościami `llm.*` (np. provider="ollama")."""
    raw = copy.deepcopy(config.raw)
    raw["llm"].update(llm)
    return Config(root=config.root, raw=raw)


@pytest.fixture(scope="session")
def documents(config):
    from mini_project_1.src.step1_load_documents import load_documents

    return load_documents(config)


@pytest.fixture
def toy_corpus(tmp_path, config):
    """Buduje mały korpus w tmp_path. Zwraca add(file, text, **catalog_fields) i pasującą konfigurację."""
    catalog = tmp_path / "catalog.csv"
    with catalog.open("w", encoding="utf-8", newline="") as fh:
        csv.writer(fh).writerow(CATALOG_COLUMNS)

    def add(file: str, text: str = "Przykładowy tekst.", in_catalog: bool = True, **fields) -> None:
        (tmp_path / file).write_text(text, encoding="utf-8")
        if in_catalog:
            row = {"doc_id": "TST-001", "file": file, "title": "Dokument testowy", "doc_type": "policy",
                   "department": "Testy", "owner": "Kierownik testów", "effective_date": "2026-01-01", "language": "en"}
            row.update(fields)
            with catalog.open("a", encoding="utf-8", newline="") as fh:
                csv.writer(fh).writerow([row[c] for c in CATALOG_COLUMNS])

    return add, config_with(config, corpus_dir=tmp_path, corpus_catalog=catalog)


class CountingFakeEmbeddings(DeterministicFakeEmbedding):
    """Sztuczny model embeddingów: ten sam tekst -> ten sam wektor; zapisuje każdy tekst, który zamienia na wektor."""

    calls: list[str] = []

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        self.calls.extend(texts)
        return super().embed_documents(texts)

    def embed_query(self, text: str) -> list[float]:
        self.calls.append(text)
        return super().embed_query(text)


class ForbiddenEmbeddings(Embeddings):
    """Zgłasza błąd przy każdym wywołaniu: dowodzi, że tekst pochodzi z cache."""

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        raise AssertionError(f"Liczba tekstów, których nie ma w cache: {len(texts)}, np. {texts[0][:60]!r}")

    def embed_query(self, text: str) -> list[float]:
        raise AssertionError(f"Tego pytania nie ma w cache: {text[:60]!r}")


@pytest.fixture
def fake_embeddings():
    return CountingFakeEmbeddings(size=16, calls=[])
