"""Testy kroku 2: compare_call nazywa każdą różnicę; gotowa macierz wywołań i mutanty działają na TWOIM serwerze."""

import copy

import pytest

from helpers.mcp_runtime import McpCallError, in_memory_connection
from mini_project_5.src.step2_compare_call import compare_call
from mini_project_5.tests.conftest import FakeStore, PARITY_MATRIX, direct_record, mutant_server


def kinds(result):
    return [(d["path"], d["kind"]) for d in result["differences"]]


def test_identical_records_are_the_same():
    record = {"status": "ok", "observations": [{"month": "2026-07", "otif_pct": 94.6}], "message": None}
    assert compare_call(record, copy.deepcopy(record)) == {"same": True, "differences": []}


def test_missing_and_extra_fields():
    result = compare_call({"a": 1, "b": 2}, {"a": 1, "c": 3})
    assert kinds(result) == [("b", "missing"), ("c", "extra")] and result["same"] is False
    assert result["differences"][0] == {"path": "b", "kind": "missing", "direct": 2, "mcp": None}


def test_grosze_turned_into_pln_is_a_unit_difference():
    assert kinds(compare_call({"invoiced_grosze": 18240000}, {"invoiced_grosze": 182400.0})) == [("invoiced_grosze", "unit")]
    assert kinds(compare_call({"penalty_grosze": 729600}, {"penalty_grosze": 7296})) == [("penalty_grosze", "unit")]


@pytest.mark.parametrize("direct, mcp", [(97, 97.0), (5, "5"), (True, 1), (None, "None")])
def test_representation_is_part_of_the_contract(direct, mcp):
    assert kinds(compare_call({"x": direct}, {"x": mcp})) == [("x", "type")]


def test_nested_paths_and_list_items():
    direct = {"observations": [{"month": "2026-07", "otif_pct": 94.6}, {"month": "2026-08", "otif_pct": 93.8}]}
    mcp = {"observations": [{"month": "2026-07", "otif_pct": 94.5}]}
    assert kinds(compare_call(direct, mcp)) == [("observations[0].otif_pct", "changed"), ("observations[1]", "missing")]


def test_inputs_are_not_modified():
    direct, mcp = {"a": [1, {"b": 2}]}, {"a": [1, {"b": 3}], "z": 0}
    before = (copy.deepcopy(direct), copy.deepcopy(mcp))
    compare_call(direct, mcp)
    assert (direct, mcp) == before


def raw(connection, tool, args):
    try:
        connection.call(tool, args)
    except McpCallError:
        pass                                   # mutant może łamać kontrakt: do zgodności i tak potrzebne są jego surowe dane
    return connection.captures[-1]["structured"]


@pytest.mark.parametrize("tool, args", PARITY_MATRIX)
def test_your_server_matches_the_direct_calls(connection, config, company, tool, args):
    # FakeStore z fixture'a server i ten tutaj zawierają te same fragmenty
    direct = direct_record(tool, args, config, company, FakeStore())
    result = compare_call(direct, raw(connection, tool, args))
    assert result["same"], f"{tool}{args}: {result['differences']}"


@pytest.mark.parametrize("kind, tool, args, expected", [
    ("pln_floats", "get_invoice_value", {"supplier": "SUP-114", "month": "2026-07"}, ("invoiced_grosze", "unit")),
    ("dropped_missing", "get_supplier_otif", {"supplier": "SUP-114", "from_month": "2026-08", "to_month": "2026-10"},
     ("missing_months", "missing")),
    ("wrong_function", "get_invoice_value", {"supplier": "SUP-114", "month": "2026-07"}, ("invoiced_grosze", "missing")),
    ("static", "get_contract_terms", {"supplier": "SUP-207"}, ("supplier_id", "changed")),
    ("renamed", "get_contract_terms", {"supplier": "SUP-114"}, ("terms_version", "missing")),
])
def test_each_mutant_wrapper_is_diagnosed(config, company, kind, tool, args, expected):
    store = FakeStore()
    with in_memory_connection(mutant_server(kind, config, company, store)) as conn:
        result = compare_call(direct_record(tool, args, config, company, store), raw(conn, tool, args))
    assert expected in kinds(result), f"{kind}: oczekiwano {expected}, otrzymano {kinds(result)}"
