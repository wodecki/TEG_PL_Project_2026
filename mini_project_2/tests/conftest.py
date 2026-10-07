"""Wspólne dane i obiekty przygotowywane do testów (ang. fixtures) Miniprojektu 2.
Testy nie wymagają klucza API."""

from __future__ import annotations

from pathlib import Path

import pytest
from langchain_core.documents import Document
from langchain_core.embeddings import DeterministicFakeEmbedding
from langchain_core.runnables import RunnableLambda

from helpers.config import load_config
from helpers.gold import GoldQuestion
from helpers.records import Answer, ContextItem, RunRecord

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture(scope="session")
def config():
    return load_config(ROOT / "config.yaml")


class FakeStructuredLLM:
    """Zastępuje model czatu ze structured output.

    Zwraca `result` (Answer, Verdict albo None) albo zgłasza `error` i zapisuje każdy
    otrzymany prompt i schemat. Atrapy modeli czatu z LangChain nie obsługują
    with_structured_output, więc testy używają tej.
    """

    def __init__(self, result=None, error: Exception | None = None):
        self.result, self.error = result, error
        self.prompts: list[str] = []
        self.schemas: list = []

    def with_structured_output(self, schema, **kwargs):
        self.schemas.append(schema)

        def respond(prompt):
            text = prompt.to_string() if hasattr(prompt, "to_string") else str(prompt)
            self.prompts.append(text)
            if self.error is not None:
                raise self.error
            return self.result

        return RunnableLambda(respond)


TOY_CHUNKS = [
    Document(page_content="Polityka podróży > Akceptacje\n\nWyjazdy zagraniczne wymagają zgody CFO.",
             metadata={"doc_id": "TST-001", "chunk_id": "TST-001#ctx000", "title": "Polityka podróży"}),
    Document(page_content="Zasady floty > Kierowcy\n\nFurgonetki mogą prowadzić tylko kierowcy z ważnym prawem jazdy.",
             metadata={"doc_id": "TST-002", "chunk_id": "TST-002#ctx000", "title": "Zasady floty"}),
]


@pytest.fixture
def toy_store():
    from mini_project_1.src.step5_search import build_vector_store

    return build_vector_store(TOY_CHUNKS, DeterministicFakeEmbedding(size=16))


def gold(**fields) -> GoldQuestion:
    base = dict(id="T01", question="Kto zatwierdza wyjazdy zagraniczne?", answerable=True, relevant_docs=["TST-001"],
                requires_all=False, evidence_facts=[["CFO"]], key_facts=[["CFO", "dyrektor finansowy"]],
                reference="Wyjazdy zagraniczne wymagają zgody CFO.")
    base.update(fields)
    return GoldQuestion(**base)


def record(answer=None, citations=(), answerable=True, error=None, context_text="Wyjazdy zagraniczne wymagają zgody CFO.",
           context_doc="TST-001", question="Kto zatwierdza wyjazdy zagraniczne?") -> RunRecord:
    context = [ContextItem(doc_id=context_doc, chunk_id=f"{context_doc}#ctx000", text=context_text)]
    output = None if answer is None else Answer(answer=answer, citations=list(citations), answerable=answerable)
    return RunRecord(question=question, context=context, output=output, error=error)
