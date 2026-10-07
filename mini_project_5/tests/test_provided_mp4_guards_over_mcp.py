"""Gotowy test: poprawione zabezpieczenia z Miniprojektu 4 nadal działają, gdy narzędzia agenta
przychodzą przez MCP (pochodzenie dowodów, jednostki, limity). Serwer w pamięci, model ze skryptem,
ocena z MP4."""

from langchain_core.messages import AIMessage
from langchain.agents import create_agent

from helpers.agent_trace import AgentGold, Budget, Need, run_question
from mini_project_4.src.step4_score_trace import score_trace
from mini_project_5.tests.conftest import ScriptedChat, answer, call


class EmptyStore:
    def similarity_search_with_score(self, query, k=4, **kwargs):
        return []


def agent_over(connection, script):
    return create_agent(ScriptedChat(script=list(script)), connection.tools())


def gold(question, **fields):
    return AgentGold(id="mcp", question=question, kind="mcp", **fields)


def test_an_invented_search_query_is_not_evidence_over_mcp(config, company):
    from helpers.agent_trace import AgentDeps
    from helpers.mcp_runtime import in_memory_connection
    from mini_project_5.src.step1_build_server import build_server

    with in_memory_connection(build_server(AgentDeps(None, EmptyStore(), company, config))) as conn:
        trace = run_question(agent_over(conn, [call("search_documents", question="Czy kara wynosi 123456 PLN?"),
                                               answer("Kara wynosi 123456 PLN.")]), "Jaka kara?", Budget(10, 60))
    assert trace.events[0].transport == "mcp" and trace.events[0].result["passages"] == []
    assert score_trace(trace, gold("Jaka kara?"))["uncovered_numbers"] == ["123456"]


def test_grosze_from_an_mcp_calculation_back_pln_only(connection):
    question = "Ile wynosi kara za lipiec?"
    script = [call("calculate_otif_penalty", otif_pct=94.6, target_pct=97, rate_per_full_point_pct=2, cap_pct=10,
                   invoice_grosze=18240000), answer("Kara wynosi 7296 PLN, a nie 729 600 PLN.")]
    trace = run_question(agent_over(connection, script), question, Budget(10, 60))
    assert trace.events[0].result["penalty_grosze"] == 729600
    assert score_trace(trace, gold(question))["uncovered_numbers"] == ["729 600"]


def test_parallel_mcp_results_crossing_the_limit_are_all_kept(connection):
    batch = AIMessage(content="", tool_calls=[
        {"id": s, "name": "get_invoice_value", "args": {"supplier": "SUP-114", "month": m}}
        for s, m in [("a", "2026-05"), ("b", "2026-06"), ("c", "2026-07")]])
    model = ScriptedChat(script=[batch, answer("gotowe")])
    trace = run_question(create_agent(model, connection.tools()), "faktury?", Budget(2, 60))
    assert trace.status == "limit" and model.agent_calls == 1
    assert sorted((e.call_id, e.status, e.transport) for e in trace.events) == \
        [("a", "ok", "mcp"), ("b", "ok", "mcp"), ("c", "ok", "mcp")]
    assert len({e.invocation_id for e in trace.events}) == 3


def test_a_missing_month_needs_the_reported_absence_over_mcp(connection):
    question = "OTIF za październik?"
    trace = run_question(agent_over(connection, [call("get_supplier_otif", supplier="SUP-114", from_month="2026-10",
                                                      to_month="2026-10"), answer("Brak danych za październik.")]),
                         question, Budget(10, 60))
    need = Need(tool="get_supplier_otif", supplier_id="SUP-114", missing=["2026-10"])
    assert score_trace(trace, gold(question, needs=[need]))["tool_coverage"] == 1.0
