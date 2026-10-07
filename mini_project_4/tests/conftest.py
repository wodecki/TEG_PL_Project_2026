"""Wspólne dane i obiekty przygotowywane do testów (ang. fixtures) Miniprojektu 4.
Testy nie wymagają klucza API."""

from __future__ import annotations

import itertools
from pathlib import Path
from typing import Any

import pytest
from langchain_core.documents import Document
from langchain_core.embeddings import DeterministicFakeEmbedding
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage
from langchain_core.outputs import ChatGeneration, ChatResult

from helpers.agent_trace import AgentDeps, AgentGold, Trace, TraceEvent, load_agent_gold
from helpers.company import CompanyData, load_company_data
from helpers.config import load_config

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture(scope="session")
def config():
    return load_config(ROOT / "config.yaml")


@pytest.fixture
def small_data() -> CompanyData:
    """Dane zrobione ręcznie: wiersze celowo nie po kolei, luka w lipcu, dostawca bez warunków."""
    return CompanyData(
        suppliers={"SUP-114": "Mleczna Dolina", "SUP-207": "Aqua Kryształ", "SUP-300": "Test Foods"},
        otif={("SUP-114", "2026-09"): 93.5, ("SUP-114", "2026-06"): 95.2, ("SUP-114", "2026-08"): 94.0,
              ("SUP-114", "2026-05"): 96.4, ("SUP-207", "2026-07"): 95.1},
        invoices={("SUP-114", "2026-06"): 18120000, ("SUP-207", "2026-07"): 9630000},
        terms={"SUP-114": {"source_doc_id": "CON-101", "otif_target_pct": 97, "penalty_clause": True,
                           "rate_per_full_point_pct": 2, "cap_pct": 10, "settlement": "credit note"},
               "SUP-207": {"source_doc_id": "CON-102", "otif_target_pct": 96, "penalty_clause": False,
                           "rate_per_full_point_pct": None, "cap_pct": None, "settlement": "quarterly review"}},
        terms_version="terms-test",
        not_otif=[{"name": "TransBałt", "source_doc_id": "CON-103", "reason": "terminowe dostawy palet, nie OTIF"}],
    )


@pytest.fixture(scope="session")
def company_data(config) -> CompanyData:
    return load_company_data(config)


@pytest.fixture(scope="session")
def gold(config) -> dict[str, AgentGold]:
    return {g.id: g for g in load_agent_gold(config.path("paths.mini_project_4_questions"))}


class CountingStore:
    """Malutki vector store, który dodatkowo zapisuje, o jakie k go poproszono."""

    def __init__(self):
        from mini_project_1.src.step5_search import build_vector_store

        chunks = [
            Document(page_content="TransBałt > Poziom obsługi i odpowiedzialność\n\n"
                                      "TransBałt musi dostarczać 98% palet w uzgodnionym oknie czasowym.",
                     metadata={"doc_id": "CON-103", "chunk_id": "CON-103#ctx003", "doc_type": "contract"}),
            Document(page_content="Mleczna Dolina > Rozwiązanie umowy\n\nKovalo może rozwiązać umowę z 60-dniowym okresem "
                                      "wypowiedzenia, jeśli OTIF przez trzy kolejne miesiące wynosi mniej niż 94%.",
                     metadata={"doc_id": "CON-101", "chunk_id": "CON-101#ctx004", "doc_type": "contract"}),
            Document(page_content="Podróże służbowe > Noclegi\n\nKoszty hotelu są zwracane do 450 PLN za noc.",
                     metadata={"doc_id": "POL-004", "chunk_id": "POL-004#ctx001", "doc_type": "policy"}),
        ]
        self.store = build_vector_store(chunks, DeterministicFakeEmbedding(size=16))
        self.ks: list[int] = []

    def similarity_search_with_score(self, query, k=4, **kwargs):
        self.ks.append(k)
        return self.store.similarity_search_with_score(query, k=k, **kwargs)


@pytest.fixture
def store():
    return CountingStore()


class ScriptedModel(BaseChatModel):
    """Zastępuje model czatu wywołujący narzędzia. Każde wywołanie bierze następny element
    scenariusza: AIMessage do zwrócenia, wyjątek do zgłoszenia albo funkcję wiadomości."""

    script: list[Any]
    calls: int = 0
    seen: list[Any] = []
    bound: list[str] = []

    @property
    def _llm_type(self) -> str:
        return "scripted-for-tests"

    def bind_tools(self, tools, **kwargs):
        self.bound = [getattr(t, "name", str(t)) for t in tools]
        return self

    def _generate(self, messages, stop=None, run_manager=None, **kwargs):
        self.seen.append(list(messages))
        if self.calls >= len(self.script):
            raise AssertionError("modelowi ze scenariusza skończyły się odpowiedzi")
        item = self.script[self.calls]
        self.calls += 1
        if isinstance(item, Exception):
            raise item
        message = item(messages) if callable(item) else item
        return ChatResult(generations=[ChatGeneration(message=message)])


_ids = itertools.count()


def call(name: str, **args) -> AIMessage:
    """Tura modelu, która wywołuje jedno narzędzie."""
    return AIMessage(content="", tool_calls=[{"name": name, "args": args, "id": f"call_{next(_ids)}"}])


def answer(text: str) -> AIMessage:
    return AIMessage(content=text)


@pytest.fixture
def deps_for(config, small_data, store):
    def make(script):
        return AgentDeps(llm=ScriptedModel(script=script), store=store, data=small_data, config=config)
    return make


# --- ręcznie zrobione zapisy przebiegu do oceny --------------------------------------------------------

def event(tool: str, result=None, origin=None, status="ok", call_id=None, parent=None, **arguments) -> TraceEvent:
    from helpers.agent_trace import ORIGINS
    return TraceEvent(call_id=call_id or f"e{next(_ids)}", parent_call_id=parent, tool=tool, arguments=arguments,
                      origin=origin or ORIGINS.get(tool, "unknown"), status=status, result=result)


def make_trace(question: str, answer_text: str | None, events: list[TraceEvent], status: str | None = None) -> Trace:
    return Trace(question=question, answer=answer_text, events=events,
                 status=status or ("answered" if answer_text is not None else "error"))


TERMS_114 = {"status": "ok", "supplier_id": "SUP-114", "supplier": "Mleczna Dolina", "source_doc_id": "CON-101",
             "otif_target_pct": 97.0, "penalty_clause": True, "rate_per_full_point_pct": 2.0, "cap_pct": 10.0}
TERMS_207 = {"status": "ok", "supplier_id": "SUP-207", "supplier": "Aqua Kryształ", "source_doc_id": "CON-102",
             "otif_target_pct": 96.0, "penalty_clause": False, "rate_per_full_point_pct": None, "cap_pct": None}


def otif_result(supplier_id: str, observations: dict[str, float], missing=()) -> dict:
    return {"status": "ok" if observations else "no_data", "supplier_id": supplier_id,
            "observations": [{"month": m, "otif_pct": v} for m, v in sorted(observations.items())],
            "missing_months": list(missing), "complete": not missing}


def invoice_result(supplier_id: str, month: str, grosze: int | None) -> dict:
    return {"status": "ok" if grosze is not None else "no_data", "supplier_id": supplier_id, "month": month,
            "invoiced_grosze": grosze, "currency": "PLN"}


def penalty_result(otif, target, rate, cap, invoice, full_points, pct, grosze) -> dict:
    return {"status": "ok", "otif_pct": otif, "target_pct": target, "rate_per_full_point_pct": rate, "cap_pct": cap,
            "invoice_grosze": invoice, "shortfall_points": round(target - otif, 4), "full_points": full_points,
            "penalty_pct_uncapped": pct, "penalty_pct": pct, "penalty_grosze": grosze, "currency": "PLN"}


def july_events() -> list[TraceEvent]:
    """Poprawna ścieżka dowodów dla lipcowej kary Mlecznej Doliny."""
    return [
        event("get_contract_terms", TERMS_114, supplier="Mleczna Dolina"),
        event("get_supplier_otif", otif_result("SUP-114", {"2026-07": 94.6}), supplier="SUP-114",
              from_month="2026-07", to_month="2026-07"),
        event("get_invoice_value", invoice_result("SUP-114", "2026-07", 18240000), supplier="SUP-114", month="2026-07"),
        event("calculate_otif_penalty", penalty_result(94.6, 97.0, 2.0, 10.0, 18240000, 2, 4.0, 729600),
              otif_pct=94.6, target_pct=97, rate_per_full_point_pct=2, cap_pct=10, invoice_grosze=18240000),
    ]
