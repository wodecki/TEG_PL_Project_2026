"""Gotowy test: gwarancje środowiska MCP (helpers/mcp_runtime.py, helpers/assistant.py). W pamięci, bez klucza."""

import asyncio
import threading
import time
from concurrent.futures import ThreadPoolExecutor

import pytest
from langchain.agents import create_agent
from mcp.server.fastmcp import FastMCP

from helpers.agent_trace import Budget, load_traces, run_question
from helpers.assistant import (agent_trace_envelope, assistant_config, replace_node, trace_from_record)
from helpers.company import InvoiceResult, OtifResult
from helpers.mcp_runtime import McpCallError, check_record, in_memory_connection
from helpers.workflow import CopilotDeps, new_checkpointer
from mini_project_5.tests.conftest import (ROOT, FakeStore, ScriptedChat, answer, call, mutant_server, turn)

INVOICE = {"status": "ok", "supplier_id": "SUP-114", "supplier": "Mleczna Dolina", "month": "2026-07",
           "invoiced_grosze": 18240000, "currency": "PLN", "message": None}


# --- rozstrzyga kanoniczny kontrakt --------------------------------------------------------------

def test_a_valid_record_is_returned_unchanged():
    assert check_record("get_invoice_value", dict(INVOICE), []) == INVOICE


@pytest.mark.parametrize("change, says", [
    ({"invoiced_grosze": True}, "invoiced_grosze"),                  # bool to nie pieniądze
    ({"invoiced_grosze": "18240000"}, "invoiced_grosze"),            # napis z liczbą też nie
    ({"invoiced_grosze": 182400.0}, "invoiced_grosze"),              # ani złotówki jako float
    ({"invoiced_grosze": None}, "nie może być null"),                 # null tam, gdzie "ok" wymaga wartości
    ({"extra": 1}, "spoza kontraktu"),
])
def test_wrong_values_break_the_contract(change, says):
    with pytest.raises(McpCallError, match=says):
        check_record("get_invoice_value", {**INVOICE, **change}, [])


def test_absent_is_not_null():
    record = dict(INVOICE)
    record.pop("message")                                            # pole z wartością domyślną, po prostu pominięte
    with pytest.raises(McpCallError, match="message: brak"):
        check_record("get_invoice_value", record, [])


def test_nested_records_are_checked_item_by_item():
    otif = {"status": "ok", "supplier_id": "SUP-114", "supplier": "M", "requested": {"from": "2026-07", "to": "2026-07"},
            "observations": [{"month": "2026-07"}], "missing_months": [], "complete": True, "message": None}
    with pytest.raises(McpCallError, match=r"observations\[0\]\.otif_pct: brak"):
        check_record("get_supplier_otif", otif, [])


def test_text_and_structured_content_must_agree():
    with pytest.raises(McpCallError, match="nie zgadzają"):
        check_record("calculate_otif_penalty", {"penalty_grosze": 729600}, ['{"penalty_grosze": 1}'])


def test_no_structured_content_is_a_validation_error():
    with pytest.raises(McpCallError, match=r"\[błąd walidacji lokalnej\].*nie ma structuredContent"):
        check_record("get_invoice_value", None, ["{}"])


@pytest.mark.parametrize("kind, tool, args, says", [
    ("dropped_missing", "get_supplier_otif", {"supplier": "SUP-114", "from_month": "2026-08", "to_month": "2026-10"},
     "missing_months: brak"),
    ("renamed", "get_contract_terms", {"supplier": "SUP-114"}, "terms_version: brak"),
    ("pln_floats", "get_invoice_value", {"supplier": "SUP-114", "month": "2026-07"}, "invoiced_grosze"),
])
def test_a_wrapper_cannot_define_away_its_own_defect(config, company, kind, tool, args, says):
    # mutant usuwa pole albo zmienia jego typ ZARÓWNO w ogłaszanym schemacie, jak i w danych
    with in_memory_connection(mutant_server(kind, config, company, FakeStore())) as conn:
        with pytest.raises(McpCallError, match=says):
            conn.call(tool, args)
        capture = conn.captures[-1]
    assert capture["outcome"] == "validation" and capture["structured"] is not None, "surowe dane nadal można obejrzeć"


def test_a_rejected_record_is_never_evidence(config, company):
    with in_memory_connection(mutant_server("pln_floats", config, company, FakeStore())) as conn:
        model = ScriptedChat(script=[call("get_invoice_value", supplier="SUP-114", month="2026-07"),
                                     answer("Faktura wyniosła 182 400 PLN.")])
        trace = run_question(create_agent(model, conn.tools()), "faktura?", Budget(10, 60))
    event = trace.events[0]
    assert event.status == "error" and event.result is None and "[błąd walidacji lokalnej]" in event.error


# --- cztery warstwy błędów -----------------------------------------------------------------------

def test_unknown_tool_is_a_tool_error(connection):
    with pytest.raises(McpCallError, match=r"\[błąd narzędzia\]"):
        connection.call("approve_discount", {"discount_pct": 14})


def test_a_closed_connection_is_a_transport_error(server):
    conn = in_memory_connection(server)
    conn.close()
    conn.close()                                                     # idempotentne
    with pytest.raises(McpCallError, match=r"\[błąd transportu\]"):
        conn.call("get_invoice_value", {"supplier": "SUP-114", "month": "2026-07"})
    assert not conn.alive


# --- tożsamość, wywołania równoległe, limity czasu -----------------------------------------------

def test_parallel_identical_calls_stay_distinct(connection):
    args = {"supplier": "SUP-114", "month": "2026-07"}
    with ThreadPoolExecutor(4) as pool:
        results = list(pool.map(lambda _: connection.call("get_invoice_value", args), range(4)))
    ids = [r["__mcp__"]["invocation_id"] for r in results]
    assert len(set(ids)) == 4 and sorted(ids) == sorted(c["invocation_id"] for c in connection.captures)


def slow_server(seconds: float):
    server = FastMCP("slow", log_level="WARNING")

    @server.tool()
    async def get_invoice_value(supplier: str, month: str) -> InvoiceResult:
        """Wolna faktura (dubler testowy)."""
        await asyncio.sleep(seconds)
        return InvoiceResult(status="ok", supplier_id="SUP-114", supplier="M", month=month, invoiced_grosze=1)
    return server


def test_a_timed_out_call_is_cancelled_and_never_comes_back():
    conn = in_memory_connection(slow_server(1.0), call_timeout_s=0.2, cleanup_timeout_s=3)
    started = time.monotonic()
    with pytest.raises(McpCallError, match=r"\[błąd transportu\].*limit czasu"):
        conn.call("get_invoice_value", {"supplier": "SUP-114", "month": "2026-07"})
    assert time.monotonic() - started < 3, "wywołujący czeka tylko do terminu wywołania (i sprzątania)"
    time.sleep(1.3)                                                  # serwer zdążyłby już odpowiedzieć
    assert conn.captures[0]["structured"] is None and conn.captures[0]["outcome"] == "transport", "żadnych spóźnionych dowodów"
    with pytest.raises(McpCallError, match="nie nadaje się do użycia"):
        conn.call("get_invoice_value", {"supplier": "SUP-114", "month": "2026-07"})
    conn.close()
    assert not conn.alive


def test_close_while_a_call_is_pending_is_bounded():
    conn = in_memory_connection(slow_server(30), call_timeout_s=60, cleanup_timeout_s=1)
    errors = []
    worker = threading.Thread(target=lambda: errors.append(
        pytest.raises(McpCallError, conn.call, "get_invoice_value", {"supplier": "S", "month": "2026-07"})))
    worker.start()
    time.sleep(0.3)
    started = time.monotonic()
    conn.close()
    assert time.monotonic() - started < 8 and not conn.alive
    worker.join(timeout=10)
    assert not worker.is_alive(), "oczekujący wywołujący zostaje zwolniony"


# --- połączenia wewnątrz asystenta ---------------------------------------------------------------

def mp3_graph(config, llm):
    from mini_project_3.src.step4_copilot_graph import build_copilot_graph
    return build_copilot_graph(CopilotDeps(llm=llm, store=None, config=config), new_checkpointer())


def test_replace_node_swaps_one_node_and_keeps_everything_else(config):
    original = mp3_graph(config, ScriptedChat())
    swapped = replace_node(original, "answer_documents", lambda state: {"status": "answered"}, new_checkpointer())
    assert set(swapped.builder.nodes) == set(original.builder.nodes)
    assert swapped.builder.edges == original.builder.edges
    assert set(swapped.builder.branches) == set(original.builder.branches)
    assert original.builder.nodes["answer_documents"] is not swapped.builder.nodes["answer_documents"]
    assert swapped.builder.channels.keys() == original.builder.channels.keys(), "te same kanały stanu i reducery"


def test_replace_node_refuses_an_unknown_node_or_langgraph_version(config, monkeypatch):
    graph = mp3_graph(config, ScriptedChat())
    with pytest.raises(RuntimeError, match="nie ma takiego węzła"):
        replace_node(graph, "nope", lambda s: {}, new_checkpointer())
    monkeypatch.setattr("helpers.assistant.version", lambda name: "2.0.0")
    with pytest.raises(RuntimeError, match="LangGraph 1.x"):
        replace_node(graph, "answer_documents", lambda s: {}, new_checkpointer())


def test_messages_still_accumulate_after_the_swap(config):
    llm = ScriptedChat(turns=[turn(kind="document_question"), turn(kind="other")])
    graph = replace_node(mp3_graph(config, llm), "answer_documents",
                         lambda state: {"status": "answered", "messages": [answer("A")]}, new_checkpointer())
    from helpers.workflow import run_turn
    run_turn(graph, "t", "q1", lambda p: None)
    run_turn(graph, "t", "thanks", lambda p: None)
    contents = [m.content for m in graph.get_state({"configurable": {"thread_id": "t"}}).values["messages"]]
    assert contents[:3] == ["q1", "A", "thanks"], "reducer messages nadal dopisuje wiadomości"


def test_the_envelope_round_trips_and_checks_its_version():
    from helpers.agent_trace import Trace
    trace = Trace(question="q", status="limit", error="osiągnięto limit kroków")
    assert trace_from_record(agent_trace_envelope(trace)).status == "limit"
    assert trace_from_record({"status": "answered"}) is None and trace_from_record(None) is None
    with pytest.raises(ValueError, match="wersja"):
        trace_from_record({"kind": "agent_trace", "version": 99, "trace": {}})


def test_assistant_config_is_a_deep_copy(config):
    copy = assistant_config(config)
    assert copy.get("prompts.understand_system") == config.get("prompts.assistant_understand_system")
    assert config.get("prompts.understand_system") != copy.get("prompts.understand_system")
    copy.raw["policy"]["margin_floor"] = 0
    assert config.get("policy.margin_floor") == 9


def test_mini_project_4_reference_traces_still_load():
    for name in ("agent_run", "supervisor_run"):
        run, rows = load_traces(ROOT / "mini_project_4" / "reference_traces" / f"{name}.json")
        assert rows and all(e.transport is None for r in rows for e in r["trace"].events)


# --- waluta i każdy blok tekstu ------------------------------------------------------------------

def test_an_ok_invoice_must_be_in_pln():
    with pytest.raises(McpCallError, match="currency musi mieć wartość 'PLN'"):
        check_record("get_invoice_value", {**INVOICE, "currency": "USD"}, [])


@pytest.mark.parametrize("second, says", [
    ('{"invoiced_grosze": 1}', "nie zgadzają"),                       # druga, sprzeczna kopia
    ("szczegóły w logu", "nie jest kopią JSON"),                      # drugi blok, który nie jest kopią
])
def test_every_text_block_must_agree(second, says):
    import json as _json
    first = _json.dumps(INVOICE)                                  # kompletny, poprawny rekord: różnią się tylko bloki
    assert check_record("get_invoice_value", dict(INVOICE), [first]) == INVOICE
    with pytest.raises(McpCallError, match=says):
        check_record("get_invoice_value", dict(INVOICE), [first, second])


def two_block_server(currency="PLN", second='{"invoiced_grosze": 1}'):
    """Prawdziwy serwer, którego narzędzie odpowiada structuredContent i DWOMA blokami tekstu."""
    from mcp.types import CallToolResult, TextContent
    server = FastMCP("two-blocks", log_level="WARNING")
    record = {**INVOICE, "currency": currency}

    @server.tool()
    def get_invoice_value(supplier: str, month: str) -> CallToolResult:
        """Faktura z dwoma blokami tekstu (dubler testowy)."""
        import json as _json
        return CallToolResult(content=[TextContent(type="text", text=_json.dumps(record)), TextContent(type="text", text=second)],
                              structuredContent=record)
    return server


@pytest.mark.parametrize("server_args", [{"second": '{"invoiced_grosze": 1}'}, {"currency": "USD", "second": None}])
def test_conflicting_or_foreign_records_are_rejected_over_mcp_and_back_no_numbers(server_args):
    second = server_args.get("second")
    server = two_block_server(currency=server_args.get("currency", "PLN"),
                              second=second if second is not None else __import__("json").dumps({**INVOICE, "currency": "USD"}))
    with in_memory_connection(server) as conn:
        with pytest.raises(McpCallError, match=r"\[błąd walidacji lokalnej\]"):
            conn.call("get_invoice_value", {"supplier": "SUP-114", "month": "2026-07"})
        assert conn.captures[-1]["outcome"] == "validation" and conn.captures[-1]["structured"] is not None
        model = ScriptedChat(script=[call("get_invoice_value", supplier="SUP-114", month="2026-07"),
                                     answer("Faktura wyniosła 182 400 PLN.")])
        trace = run_question(create_agent(model, conn.tools()), "faktura?", Budget(10, 60))
    from helpers.agent_trace import AgentGold
    from mini_project_4.src.step4_score_trace import score_trace
    assert trace.events[0].status == "error"
    assert score_trace(trace, AgentGold(id="x", question="faktura?", kind="x"))["uncovered_numbers"] == ["182 400"], \
        "odrzucony rekord nigdy nie stanowi pokrycia dla liczby"
