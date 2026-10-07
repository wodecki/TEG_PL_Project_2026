"""Testy kroku 3: węzeł odpowiada agentem przez narzędzia MCP i zachowuje zapis przebiegu (trace)."""

from langchain_core.messages import AIMessage

from helpers.agent_trace import AgentDeps, ALLOWED_TOOLS
from helpers.assistant import trace_from_record
from mini_project_5.src.step3_answer_with_tools import answer_with_tools
from mini_project_5.tests.conftest import ScriptedChat, answer, call, turn


def node_for(connection, config, script):
    llm = ScriptedChat(script=list(script))
    return llm, answer_with_tools(AgentDeps(llm=llm, store=None, data=None, config=config), connection.tools())


def test_the_agent_uses_the_mcp_tools_and_the_trace_is_kept(connection, config):
    llm, node = node_for(connection, config, [
        call("get_contract_terms", supplier="SUP-114"),
        call("get_invoice_value", supplier="SUP-114", month="2026-07"),
        answer("Faktura za lipiec: 182 400 PLN (warunki CON-101 sprawdzone).")])
    update = node({"turn": turn(kind="document_question", standalone="Na jaką kwotę Mleczna Dolina wystawiła fakturę za lipiec 2026 r.?")})
    assert update["status"] == "answered" and update["error"] is None
    assert [m.content for m in update["messages"]] == ["Faktura za lipiec: 182 400 PLN (warunki CON-101 sprawdzone)."]
    assert isinstance(update["messages"][0], AIMessage)
    trace = trace_from_record(update["record"])
    assert trace.question == "Na jaką kwotę Mleczna Dolina wystawiła fakturę za lipiec 2026 r.?", "pytanie przeredagowane (standalone), nie surowa wiadomość"
    assert [(e.tool, e.status, e.transport) for e in trace.events] == [
        ("get_contract_terms", "ok", "mcp"), ("get_invoice_value", "ok", "mcp")]
    captured = [c["invocation_id"] for c in connection.captures]
    assert [e.invocation_id for e in trace.events] == captured, "każde zdarzenie jest powiązane ze swoim wywołaniem MCP przez identyfikator"
    assert trace.events[1].result["invoiced_grosze"] == 18240000
    assert sorted(llm.bound) == sorted(ALLOWED_TOOLS), "agent dostaje dokładnie narzędzia MCP"


def test_the_system_prompt_is_the_agents(connection, config):
    seen = []

    def reply(messages):
        seen.append(messages[0].content)
        return answer("ok")
    _, node = node_for(connection, config, [reply])
    node({"turn": turn(kind="document_question", standalone="q")})
    assert seen == [config.get("prompts.agent_system")]


def test_a_limit_is_an_error_turn_that_keeps_the_trace(connection, config):
    looping = [lambda m: call("get_contract_terms", supplier="SUP-114")] * 40
    _, node = node_for(connection, config, looping)
    update = node({"turn": turn(kind="document_question", standalone="warunki?")})
    trace = trace_from_record(update["record"])
    assert update["status"] == "error" and trace.status == "limit", "koperta zachowuje własny wynik zapisu przebiegu"
    assert trace.events and "limit kroków" in update["error"]
    assert len(update["messages"]) == 1 and "limit kroków" in update["messages"][0].content


def test_a_model_failure_after_a_call_keeps_the_call(connection, config):
    _, node = node_for(connection, config, [call("get_contract_terms", supplier="SUP-207"), RuntimeError("provider down")])
    update = node({"turn": turn(kind="document_question", standalone="Warunki Aqua?")})
    trace = trace_from_record(update["record"])
    assert update["status"] == "error" and trace.status == "error"
    assert [(e.tool, e.status) for e in trace.events] == [("get_contract_terms", "ok")]


def test_every_turn_starts_fresh(connection, config):
    seen = []

    def reply(messages):
        seen.append([m.content for m in messages])
        return answer("ok")
    _, node = node_for(connection, config, [reply, reply])
    node({"turn": turn(kind="document_question", standalone="pierwsze")})
    node({"turn": turn(kind="document_question", standalone="drugie")})
    assert "pierwsze" not in seen[1]


def test_an_exception_inside_a_tool_call_is_an_error_event(config):
    from langchain_core.tools import tool

    @tool
    def get_contract_terms(supplier: str) -> dict:
        """Warunki umowy (dubler testowy, którego proces zawodzi)."""
        raise RuntimeError("connection reset")
    llm = ScriptedChat(script=[call("get_contract_terms", supplier="SUP-114"), answer("Nie udało mi się pobrać warunków.")])
    node = answer_with_tools(AgentDeps(llm=llm, store=None, data=None, config=config), [get_contract_terms])
    update = node({"turn": turn(kind="document_question", standalone="warunki?")})
    trace = trace_from_record(update["record"])
    assert update["status"] == "answered" and llm.agent_calls == 2
    assert [(e.tool, e.status) for e in trace.events] == [("get_contract_terms", "error")]
