"""Wspólne dane i obiekty przygotowywane do testów (ang. fixtures) Miniprojektu 3.
Testy nie wymagają klucza API."""

from __future__ import annotations

import copy
from pathlib import Path

import pytest
import yaml
from langchain_core.documents import Document
from langchain_core.embeddings import DeterministicFakeEmbedding
from langchain_core.runnables import RunnableLambda

from helpers.config import Config, load_config
from helpers.records import Answer
from helpers.workflow import Turn

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture(scope="session")
def config():
    return load_config(ROOT / "config.yaml")


def config_with_policy(config: Config, **policy) -> Config:
    raw = copy.deepcopy(config.raw)
    raw["policy"].update(policy)
    return Config(root=config.root, raw=raw)


class ReplayLLM:
    """Zastępuje model czatu: zwraca po kolei zaplanowane obiekty Turn, a na pytania
    o dokumenty stałą odpowiedź Answer. Liczy każde wywołanie, więc testy widzą ponowne
    uruchomienia."""

    def __init__(self, turns=(), answer=None, fail=False):
        self.turns = list(turns)
        self.answer = answer or Answer(answer="(odtworzona odpowiedź)", citations=[], answerable=True)
        self.fail = fail
        self.calls = {"Turn": 0, "Answer": 0}
        self.prompts = []

    def with_structured_output(self, schema, **kwargs):
        def respond(messages):
            self.prompts.append(messages)
            if self.fail:
                raise ValueError("sztuczny błąd")
            if schema is Turn:
                self.calls["Turn"] += 1
                return self.turns.pop(0)
            if schema is Answer:
                self.calls["Answer"] += 1
                return self.answer
            raise AssertionError(f"nieoczekiwany schemat {schema}")
        return RunnableLambda(respond)


def turn(**fields) -> Turn:
    base = dict(kind="other", request_action="none", standalone="(standalone)")
    base.update(fields)
    return Turn(**base)


class NoStore:
    """Vector store, którego nie wolno użyć (wszystkie trasy poza pytaniami o dokumenty)."""

    def similarity_search_with_score(self, *args, **kwargs):
        raise AssertionError("ta trasa nie może przeszukiwać dokumentów")


@pytest.fixture
def toy_store():
    from mini_project_1.src.step5_search import build_vector_store

    chunks = [Document(page_content="Komitet cenowy > Woda\n\nKomitet utrzymał ceny wody.",
                       metadata={"doc_id": "TST-001", "chunk_id": "TST-001#ctx000"})]
    return build_vector_store(chunks, DeterministicFakeEmbedding(size=16))


def gold_dialogues():
    with (ROOT / "data" / "eval" / "mini_project_3_dialogues.yaml").open(encoding="utf-8") as fh:
        return yaml.safe_load(fh)["dialogues"]
