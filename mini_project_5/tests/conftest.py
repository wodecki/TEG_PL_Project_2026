"""Wspólne dane i obiekty przygotowywane do testów (ang. fixtures) Miniprojektu 5.
Sesje MCP działają w pamięci, serwery stdio symulują błędy, a modele realizują przygotowane scenariusze.
Testy nie wymagają klucza API ani dostępu do sieci."""

from __future__ import annotations

import itertools
from pathlib import Path
from typing import Any

import pytest
import yaml
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from langchain_core.runnables import RunnableLambda

from helpers.agent_trace import AgentDeps
from helpers.company import ContractTermsResult, InvoiceResult, OtifResult, load_company_data
from helpers.config import load_config
from helpers.mcp_runtime import in_memory_connection
from helpers.workflow import Turn

ROOT = Path(__file__).resolve().parents[2]
_ids = itertools.count()


@pytest.fixture(scope="session")
def config():
    return load_config(ROOT / "config.yaml")


@pytest.fixture(scope="session")
def company(config):
    return load_company_data(config)


class FakeStore:
    """Dwa fragmenty, żeby search_documents działało offline."""

    def __init__(self):
        from langchain_core.documents import Document
        from langchain_core.embeddings import DeterministicFakeEmbedding

        from mini_project_1.src.step5_search import build_vector_store

        self.store = build_vector_store([
            Document(page_content="TransBałt musi dostarczać 98% palet w uzgodnionym oknie czasowym.",
                     metadata={"doc_id": "CON-103", "chunk_id": "CON-103#ctx003", "doc_type": "contract"}),
            Document(page_content="Kovalo może rozwiązać umowę z 60-dniowym okresem wypowiedzenia, jeśli OTIF "
                                  "przez trzy kolejne miesiące wynosi mniej niż 94%.",
                     metadata={"doc_id": "CON-101", "chunk_id": "CON-101#ctx004", "doc_type": "contract"})],
            DeterministicFakeEmbedding(size=16))
        self.ks: list[int] = []

    def similarity_search_with_score(self, query, k=4, **kwargs):
        self.ks.append(k)
        return self.store.similarity_search_with_score(query, k=k, **kwargs)


@pytest.fixture
def server(config, company):
    from mini_project_5.src.step1_build_server import build_server
    return build_server(AgentDeps(llm=None, store=FakeStore(), data=company, config=config))


@pytest.fixture
def connection(server):
    conn = in_memory_connection(server, call_timeout_s=20)
    yield conn
    conn.close()


class ScriptedChat(BaseChatModel):
    """Jeden udawany model dla całego asystenta: wywołania ze structured output (rozumienie z MP3)
    biorą następny Turn ze skryptu; wywołania z narzędziami (agent) biorą następną AIMessage ze
    skryptu, wyjątek do zgłoszenia albo funkcję wiadomości. Liczy oba rodzaje i zapisuje, co widział."""

    turns: list[Any] = []
    script: list[Any] = []
    understand_calls: int = 0
    agent_calls: int = 0
    seen_systems: list[str] = []
    seen_understand: list[list[str]] = []      # teksty wiadomości, które widziało każde wywołanie rozumienia
    bound: list[str] = []

    @property
    def _llm_type(self) -> str:
        return "scripted-assistant-for-tests"

    def bind_tools(self, tools, **kwargs):
        self.bound = [getattr(t, "name", str(t)) for t in tools]
        return self

    def with_structured_output(self, schema, **kwargs):
        def respond(messages):
            if schema is not Turn:
                raise AssertionError(f"nieoczekiwany structured output {schema}")
            self.understand_calls += 1
            self.seen_systems.append(messages[0].content)
            self.seen_understand.append([m.content for m in messages])
            if not self.turns:
                raise AssertionError("modelowi ze skryptem skończyły się obiekty Turn: dodatkowe wywołanie rozumienia?")
            return self.turns.pop(0)
        return RunnableLambda(respond)

    def _generate(self, messages, stop=None, run_manager=None, **kwargs):
        self.agent_calls += 1
        if not self.script:
            raise AssertionError("modelowi ze skryptem skończyły się wiadomości agenta")
        item = self.script.pop(0)
        if isinstance(item, Exception):
            raise item
        message = item(messages) if callable(item) else item
        return ChatResult(generations=[ChatGeneration(message=message)])


def call(name: str, **args) -> AIMessage:
    return AIMessage(content="", tool_calls=[{"name": name, "args": args, "id": f"call_{next(_ids)}"}])


def answer(text: str) -> AIMessage:
    return AIMessage(content=text)


def turn(**fields) -> Turn:
    base = dict(kind="other", request_action="none", standalone="(standalone)")
    base.update(fields)
    return Turn(**base)


def answers(*values):
    it = iter(values)
    return lambda payload: next(it)


def all_conversations():
    """Rozmowy z MP5 + dialogi z MP3 z nakładkami MP5 (helpers.assistant_eval.load_conversations)."""
    from helpers.assistant_eval import load_conversations
    return load_conversations(load_config(ROOT / "config.yaml"))


# --- zgodność wyników: gotowa macierz wywołań i serwery-mutanty -----------------------------

PARITY_MATRIX = [
    ("get_supplier_otif", {"supplier": "Mleczna Dolina", "from_month": "2026-08", "to_month": "2026-10"}),
    ("get_supplier_otif", {"supplier": "SUP-114", "from_month": "2026-05", "to_month": "2026-07"}),
    ("get_supplier_otif", {"supplier": "SUP-114", "from_month": "2026-10", "to_month": "2026-10"}),
    ("get_supplier_otif", {"supplier": "Nordic Fish", "from_month": "2026-07", "to_month": "2026-07"}),
    ("get_supplier_otif", {"supplier": "SUP-114", "from_month": "2026-7", "to_month": "2026-07"}),
    ("get_invoice_value", {"supplier": "SUP-114", "month": "2026-07"}),
    ("get_invoice_value", {"supplier": "SUP-207", "month": "2026-08"}),
    ("get_contract_terms", {"supplier": "Mleczna Dolina"}),
    ("get_contract_terms", {"supplier": "SUP-207"}),
    ("get_contract_terms", {"supplier": "TransBałt"}),
    ("calculate_otif_penalty", {"otif_pct": 94.6, "target_pct": 97, "rate_per_full_point_pct": 2, "cap_pct": 10,
                                "invoice_grosze": 18240000}),
    ("calculate_otif_penalty", {"otif_pct": 101, "target_pct": 97, "rate_per_full_point_pct": 2, "cap_pct": 10,
                                "invoice_grosze": 1}),
    ("check_discount_policy", {"discount_pct": 22, "margin_after_pct": 7, "strategic_account": True}),
    ("check_discount_policy", {"discount_pct": 30, "margin_after_pct": 4, "clearance": True}),
    ("check_discount_policy", {"discount_pct": 14, "competitor_offer": True}),
    ("check_discount_policy", {"discount_pct": 4, "contractual_volume_rebate": True}),
    ("search_documents", {"question": "TransBałt terminowe dostawy palet"}),
]


def direct_record(tool: str, args: dict, config, company, store) -> dict:
    """To samo wywołanie wykonane bezpośrednio na funkcjach Miniprojektu 4."""
    from mini_project_4.src import step1_read_company_data as d
    from mini_project_4.src import step2_compute_and_search as c
    functions = {
        "get_supplier_otif": lambda: d.get_supplier_otif(company, **args),
        "get_invoice_value": lambda: d.get_invoice_value(company, **args),
        "get_contract_terms": lambda: d.get_contract_terms(company, **args),
        "calculate_otif_penalty": lambda: c.calculate_otif_penalty(**args),
        "check_discount_policy": lambda: c.check_discount_policy(config, **args),
        "search_documents": lambda: c.search_documents(store, args["question"], config.get("retrieval.top_k")),
    }
    return functions[tool]().model_dump(mode="json")


def mutant_server(kind: str, config, company, store):
    """Serwer z JEDNYM celowym błędem nakładki (reszta poprawna). Rodzaje:
    pln_floats (faktura w złotych jako float), dropped_missing (missing_months usunięte z rekordu OTIF),
    wrong_function (get_invoice_value odpowiada OTIF-em), static (get_contract_terms ignoruje argument),
    renamed (zmieniona nazwa terms_version)."""
    from mcp.server.fastmcp import FastMCP

    from mini_project_5.src.step1_build_server import build_server
    good = build_server(AgentDeps(llm=None, store=store, data=company, config=config))
    server = FastMCP("kovalo-mutant", log_level="WARNING")
    for tool in good._tool_manager.list_tools():
        server._tool_manager._tools[tool.name] = tool

    def patch(name, fn):
        server._tool_manager._tools.pop(name)
        server.tool(name=name)(fn)

    from pydantic import create_model

    from mini_project_4.src import step1_read_company_data as d

    def variant(base, drop=(), **fields):
        """Typ rekordu jak `base`, z usuniętymi polami albo zmienionymi typami: schemat ORAZ dane mutanta."""
        kept = {n: (f.annotation, f) for n, f in base.model_fields.items() if n not in drop and n not in fields}
        return create_model(f"Mutant{base.__name__}", **kept, **fields)

    if kind == "pln_floats":
        Model = variant(InvoiceResult, invoiced_grosze=(float | None, None))

        def get_invoice_value(supplier: str, month: str):
            r = d.get_invoice_value(company, supplier, month).model_dump()
            r["invoiced_grosze"] = r["invoiced_grosze"] / 100 if r["invoiced_grosze"] is not None else None
            return Model(**r)
        get_invoice_value.__annotations__["return"] = Model
        patch("get_invoice_value", get_invoice_value)
    elif kind == "dropped_missing":
        Model = variant(OtifResult, drop=("missing_months",))

        def get_supplier_otif(supplier: str, from_month: str, to_month: str):
            r = d.get_supplier_otif(company, supplier, from_month, to_month).model_dump()
            r.pop("missing_months")
            return Model(**r)
        get_supplier_otif.__annotations__["return"] = Model
        patch("get_supplier_otif", get_supplier_otif)
    elif kind == "wrong_function":
        def get_invoice_value(supplier: str, month: str) -> OtifResult:
            return d.get_supplier_otif(company, supplier, month, month)
        patch("get_invoice_value", get_invoice_value)
    elif kind == "static":
        def get_contract_terms(supplier: str) -> ContractTermsResult:
            return d.get_contract_terms(company, "SUP-114")
        patch("get_contract_terms", get_contract_terms)
    elif kind == "renamed":
        Model = variant(ContractTermsResult, drop=("terms_version",), version=(str | None, None))

        def get_contract_terms(supplier: str):
            r = d.get_contract_terms(company, supplier).model_dump()
            r["version"] = r.pop("terms_version")
            return Model(**r)
        get_contract_terms.__annotations__["return"] = Model
        patch("get_contract_terms", get_contract_terms)
    else:
        raise ValueError(kind)
    return server
