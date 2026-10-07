"""Testy kroku 3: narzędzia, które widzi model, i pętla agenta (z modelem według scenariusza, bez wywołań API)."""

from langchain_core.messages import SystemMessage

from helpers.agent_trace import ALLOWED_TOOLS, Budget, run_question
from mini_project_4.src.step3_build_agent import build_agent, build_tools
from mini_project_4.tests.conftest import answer, call

ARGUMENTS = {
    "search_documents": {"question"},
    "get_supplier_otif": {"supplier", "from_month", "to_month"},
    "get_invoice_value": {"supplier", "month"},
    "get_contract_terms": {"supplier"},
    "calculate_otif_penalty": {"otif_pct", "target_pct", "rate_per_full_point_pct", "cap_pct", "invoice_grosze"},
    "check_discount_policy": {"discount_pct", "margin_after_pct", "clearance", "strategic_account",
                              "competitor_offer", "contractual_volume_rebate"},
}


def tools_by_name(deps):
    return {t.name: t for t in build_tools(deps)}


def test_exactly_the_allowed_tools(deps_for):
    tools = build_tools(deps_for([]))
    names = [t.name for t in tools]
    assert sorted(names) == sorted(ALLOWED_TOOLS), "dokładnie sześć narzędzi tylko do odczytu: nic, co zatwierdza albo zapisuje"
    assert len(names) == len(set(names))


def test_the_model_sees_names_descriptions_and_arguments_only(deps_for):
    for name, t in tools_by_name(deps_for([])).items():
        assert len(t.description) > 40, f"{name}: opisz, co zwraca, i formaty argumentów"
        assert set(t.args) == ARGUMENTS[name], f"{name}: argumenty {set(t.args)}; data, store i config nigdy nie są argumentami modelu"


def test_tools_return_json_ready_records(deps_for):
    tools = tools_by_name(deps_for([]))
    otif = tools["get_supplier_otif"].invoke({"supplier": "SUP-114", "from_month": "2026-08", "to_month": "2026-10"})
    assert isinstance(otif, dict) and otif["status"] == "ok" and otif["missing_months"] == ["2026-10"]
    terms = tools["get_contract_terms"].invoke({"supplier": "TransBałt"})
    assert terms["status"] == "not_applicable"
    penalty = tools["calculate_otif_penalty"].invoke({"otif_pct": 94.6, "target_pct": 97, "rate_per_full_point_pct": 2,
                                                       "cap_pct": 10, "invoice_grosze": 18240000})
    assert penalty["penalty_grosze"] == 729600
    policy = tools["check_discount_policy"].invoke({"discount_pct": 22, "margin_after_pct": 7, "strategic_account": True})
    assert policy["approvers"] == ["Dyrektor handlowy", "CFO"]
    assert tools["get_invoice_value"].invoke({"supplier": "SUP-114", "month": "2026-06"})["invoiced_grosze"] == 18120000


def test_search_uses_the_pinned_top_k(deps_for, config, store):
    result = tools_by_name(deps_for([]))["search_documents"].invoke({"question": "palety"})
    assert result["status"] == "ok" and store.ks == [config.get("retrieval.top_k")]


def test_the_agent_calls_tools_and_the_trace_records_them(deps_for, config):
    deps = deps_for([call("get_contract_terms", supplier="SUP-114"),
                     call("get_supplier_otif", supplier="SUP-114", from_month="2026-06", to_month="2026-06"),
                     answer("Czerwiec: 95,2%.")])
    trace = run_question(build_agent(deps), "OTIF w czerwcu?", Budget(20, 60))
    assert trace.status == "answered" and trace.answer == "Czerwiec: 95,2%."
    assert [e.tool for e in trace.events] == ["get_contract_terms", "get_supplier_otif"]
    assert all(e.status == "ok" and e.origin == "data" for e in trace.events)
    assert trace.events[1].result["observations"] == [{"month": "2026-06", "otif_pct": 95.2}]
    assert sorted(deps.llm.bound) == sorted(ALLOWED_TOOLS), "agent musi dostać build_tools(deps)"
    first = deps.llm.seen[0]
    assert isinstance(first[0], SystemMessage) and first[0].content == config.get("prompts.agent_system")


def test_every_question_starts_fresh(deps_for):
    deps = deps_for([answer("pierwsza"), answer("druga")])
    agent = build_agent(deps)
    run_question(agent, "pierwsze pytanie", Budget(10, 60))
    run_question(agent, "drugie pytanie", Budget(10, 60))
    texts = [m.content for m in deps.llm.seen[1]]
    assert "pierwsze pytanie" not in texts, "bez pamięci między pytaniami"


def test_invalid_arguments_and_unknown_tools_are_recorded(deps_for):
    deps = deps_for([call("get_supplier_otif", supplier="SUP-114"),           # brak to_month
                     call("approve_discount", discount_pct=14),                 # nie ma takiego narzędzia
                     answer("Nie udało mi się pobrać danych.")])
    trace = run_question(build_agent(deps), "OTIF?", Budget(20, 60))
    assert trace.status == "answered"
    assert [(e.tool, e.status) for e in trace.events] == [("get_supplier_otif", "error"), ("approve_discount", "error")]
    assert trace.events[1].origin == "unknown"


def test_a_model_failure_after_a_call_keeps_the_call(deps_for):
    deps = deps_for([call("get_contract_terms", supplier="SUP-207"), RuntimeError("provider unavailable")])
    trace = run_question(build_agent(deps), "Warunki Aqua?", Budget(20, 60))
    assert trace.status == "error" and "provider unavailable" in trace.error
    assert [(e.tool, e.status) for e in trace.events] == [("get_contract_terms", "ok")]
    assert trace.events[0].result["penalty_clause"] is False


def test_a_repeating_tool_hits_the_step_limit_and_keeps_its_events(deps_for):
    deps = deps_for([lambda messages: call("get_supplier_otif", supplier="SUP-114", from_month="2026-06",
                                           to_month="2026-06")] * 50)
    trace = run_question(build_agent(deps), "OTIF?", Budget(max_steps=6, timeout_s=60))
    assert trace.status == "limit" and "limit kroków" in trace.error
    assert len(trace.events) >= 2 and trace.answer is None


class BrokenStore:
    """Indeks wyszukiwania, który zawodzi, jak store, gdy usługa embeddingów nie działa."""

    def similarity_search_with_score(self, *args, **kwargs):
        raise RuntimeError("embedding service unavailable")


def test_an_exception_inside_a_valid_call_is_an_error_the_model_can_read(config, small_data):
    from helpers.agent_trace import AgentDeps
    from mini_project_4.tests.conftest import ScriptedModel

    model = ScriptedModel(script=[call("search_documents", question="TransBałt palety"),
                                  answer("Nie mogę teraz przeszukać dokumentów.")])
    deps = AgentDeps(llm=model, store=BrokenStore(), data=small_data, config=config)
    trace = run_question(build_agent(deps), "Palety TransBałtu?", Budget(20, 60))
    assert trace.status == "answered", "przebieg trwa dalej: model dostaje błąd i odpowiada"
    assert [(e.tool, e.status) for e in trace.events] == [("search_documents", "error")]
    assert "RuntimeError" in trace.events[0].error and "embedding service unavailable" in trace.events[0].error
    assert model.calls == 2
