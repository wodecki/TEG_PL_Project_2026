"""Testy kroku 1: narzędzia serwera, schematy, wyniki ustrukturyzowane, zasoby i prompt (MCP w pamięci)."""

import pytest
import yaml
from mcp.shared.exceptions import McpError

from helpers.agent_trace import ALLOWED_TOOLS
from helpers.mcp_runtime import CANONICAL, McpCallError
from mini_project_5.tests.conftest import PARITY_MATRIX


def listed(connection):
    return {t.name: t for t in connection.run(lambda s: s.list_tools()).tools}


def test_exactly_the_six_read_only_tools(connection):
    tools = listed(connection)
    assert set(tools) == set(ALLOWED_TOOLS)
    for name, t in tools.items():
        assert t.annotations and t.annotations.readOnlyHint is True, f"{name}: oznacz je jako tylko do odczytu"
        assert t.description and len(t.description) > 40, f"{name}: potrzebny docstring, z którego model może skorzystać"


def test_every_tool_publishes_its_records_output_schema(connection):
    for name, t in listed(connection).items():
        assert t.outputSchema, f"{name}: zwracaj typ rekordu (-> OtifResult), nie zwykły słownik dict"
        assert set(t.outputSchema["properties"]) == set(CANONICAL[name].model_fields), \
            f"{name}: schemat wyjścia musi być rekordem z Miniprojektu 4"


def test_input_arguments_match_mini_project_4(connection):
    tools = listed(connection)
    assert set(tools["get_supplier_otif"].inputSchema["properties"]) == {"supplier", "from_month", "to_month"}
    assert set(tools["calculate_otif_penalty"].inputSchema["properties"]) == \
        {"otif_pct", "target_pct", "rate_per_full_point_pct", "cap_pct", "invoice_grosze"}
    assert "config" not in str(tools["check_discount_policy"].inputSchema), "zależności nigdy nie są argumentami"


@pytest.mark.parametrize("tool, args", PARITY_MATRIX)
def test_every_outcome_arrives_as_a_valid_structured_record(connection, tool, args):
    result = connection.call(tool, args)            # zgłasza wyjątek, jeśli rekord łamie kanoniczny kontrakt
    assert set(result["record"]) == set(CANONICAL[tool].model_fields)


def test_a_partial_period_keeps_its_missing_months(connection):
    record = connection.call("get_supplier_otif", {"supplier": "SUP-114", "from_month": "2026-08",
                                                   "to_month": "2026-10"})["record"]
    assert record["missing_months"] == ["2026-10"] and record["complete"] is False


def test_search_uses_the_pinned_top_k(connection, server, config):
    record = connection.call("search_documents", {"question": "pallets"})["record"]
    assert record["status"] == "ok" and len(record["passages"]) == 2      # udawany store zawiera dwa
    assert record["passages"][0]["doc_id"] in {"CON-103", "CON-101"}


def test_a_bad_argument_is_a_tool_error(connection):
    with pytest.raises(McpCallError, match=r"\[błąd narzędzia\]"):
        connection.call("calculate_otif_penalty", {"otif_pct": "high", "target_pct": 97, "rate_per_full_point_pct": 2,
                                                   "cap_pct": 10, "invoice_grosze": 1})


def test_documents_by_exact_catalogue_id(connection):
    text = connection.run(lambda s: s.read_resource("kovalo://documents/CON-103")).contents[0].text
    assert "98% palet" in text


@pytest.mark.parametrize("doc_id", ["CON-10[3]", "CON-10*", "XYZ-999", "CON-101_supplier_agreement_mleczna_dolina.md",
                                    "..", "con-103"])
def test_anything_but_an_exact_id_is_rejected(connection, doc_id):
    with pytest.raises(McpError):
        connection.run(lambda s: s.read_resource(f"kovalo://documents/{doc_id}"))


def test_a_path_is_never_a_document(connection):
    with pytest.raises(McpError):
        connection.run(lambda s: s.read_resource("kovalo://documents/../../config.yaml"))


def test_the_policy_resource(connection, config):
    text = connection.run(lambda s: s.read_resource("kovalo://policy/course-v1")).contents[0].text
    assert yaml.safe_load(text) == config.get("policy")


def test_the_prompt(connection):
    prompt = connection.run(lambda s: s.get_prompt("supplier_review", {"supplier": "Mleczna Dolina"}))
    assert len(prompt.messages) == 1 and "Mleczna Dolina" in prompt.messages[0].content.text


def test_nothing_is_printed_to_stdout(config, company, capfd):
    from helpers.agent_trace import AgentDeps
    from helpers.mcp_runtime import in_memory_connection
    from mini_project_5.src.step1_build_server import build_server
    from mini_project_5.tests.conftest import FakeStore

    with in_memory_connection(build_server(AgentDeps(None, FakeStore(), company, config))) as conn:
        conn.call("get_invoice_value", {"supplier": "SUP-114", "month": "2026-07"})
    assert capfd.readouterr().out == "", "przy stdio stdout przenosi wyłącznie komunikaty protokołu: loguj na stderr"
