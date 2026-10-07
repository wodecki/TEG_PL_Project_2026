"""Gotowe testy: mechanika zapisu przebiegu i reguły rozpoznawania liczb, na których opiera się twoja ocena (bez wywołań API)."""

from decimal import Decimal

import pytest
from langchain_core.tools import tool
from langchain.agents import create_agent

from helpers.agent_trace import Budget, run_question, worker_result
from helpers.quantities import grosze_to_pln, mentions, numbers_in, round_grosze, same_quantity, source_values
from mini_project_4.tests.conftest import ScriptedModel, answer, call


def supervisor_with_one_worker(worker_script, supervisor_script, budget_box):
    @tool
    def get_contract_terms(supplier: str) -> dict:
        """Warunki umowy (dubler testowy)."""
        return {"status": "ok", "supplier_id": "SUP-207", "penalty_clause": False, "otif_target_pct": 96.0}

    worker = create_agent(ScriptedModel(script=worker_script), [get_contract_terms])

    @tool
    def ask_data_analyst(task: str) -> dict:
        """Zadanie dla specjalisty od danych (dubler testowy)."""
        return worker_result(run_question(worker, task, budget_box["budget"], agent_name="data_analyst"))

    return create_agent(ScriptedModel(script=supervisor_script), [ask_data_analyst])


def test_worker_calls_are_nested_and_its_summary_is_not_a_source():
    box = {"budget": Budget(20, 60)}
    supervisor = supervisor_with_one_worker(
        [call("get_contract_terms", supplier="SUP-207"), answer("Aqua jest winna 1926 PLN.")],
        [call("ask_data_analyst", task="Czy Aqua jest winna karę?"), answer("Aqua jest winna 1926 PLN.")], box)
    trace = run_question(supervisor, "Czy Aqua jest winna karę?", box["budget"])
    assert trace.status == "answered"
    wrapper, nested = trace.events
    assert (wrapper.tool, wrapper.origin, wrapper.result) == ("ask_data_analyst", "worker_summary", {"summary": "Aqua jest winna 1926 PLN."})
    assert (nested.tool, nested.origin, nested.agent, nested.parent_call_id) == \
        ("get_contract_terms", "data", "data_analyst", wrapper.call_id)
    assert trace.steps == 6, "jeden limit liczy kroki supervisora ORAZ specjalisty"


def test_one_budget_for_the_whole_question():
    box = {"budget": Budget(max_steps=5, timeout_s=60)}
    looping = [lambda m: call("get_contract_terms", supplier="SUP-207")] * 20
    supervisor = supervisor_with_one_worker(looping, [call("ask_data_analyst", task="warunki?")] * 5, box)
    trace = run_question(supervisor, "warunki?", box["budget"])
    assert trace.status == "limit", "specjalista nie może wyzerować limitu pytania"
    assert any(e.agent == "data_analyst" for e in trace.events), "zdarzenia specjalisty zostają zachowane"


def test_a_time_limit():
    budget = Budget(max_steps=100, timeout_s=-1)
    with pytest.raises(Exception, match="limit czasu"):
        budget.tick()


# angielskie zapisy celowo: moduł czyta je obok polskich (polskie przykłady: test_polish_notation)
@pytest.mark.parametrize("text, expected", [
    ("7,296 PLN", [("7296", "PLN")]),
    ("PLN 7,296.00", [("7296.00", "PLN")]),
    ("7 296,00 zł", [("7296.00", "PLN")]),
    ("94.6% and 2 full percentage points", [("94.6", "%"), ("2", "pp")]),
    ("2,5%", [("2.5", "%")]),
    ("SUP-114, CON-101, 2026-07, Q2, July 2026, 20 August", []),
    ("1. pierwszy\n2. drugi", []),
    ("1926 PLN w 1926 r.", [("1926", "PLN")]),
    ("18,240,000 grosze = 182,400 PLN", [("18240000", "grosze"), ("182400", "PLN")]),
])
def test_numbers_in(text, expected):
    assert [(str(q.value), q.unit) for q in numbers_in(text)] == expected


def test_source_values_use_the_field_units():
    values = {(str(q.value), q.unit) for q in source_values(
        {"penalty_grosze": 729600, "full_points": 2, "rate_per_full_point_pct": 2.0, "complete": True,
         "passages": [{"doc_id": "CON-101", "text": "jeśli OTIF przez trzy kolejne miesiące wynosi mniej niż 94%"}]})}
    assert values == {("7296", "PLN"), ("729600", "grosze"), ("2", "pp"), ("2.0", "%"), ("94", "%")}


def test_same_quantity():
    pln = numbers_in("7296,00 PLN")[0]
    assert same_quantity(pln, source_values({"penalty_grosze": 729600})[0])
    grosze = source_values({"penalty_grosze": 729600})
    assert not any(same_quantity(numbers_in("729 600 PLN")[0], s) for s in grosze), "729600 groszy to nie 729 600 PLN"
    assert any(same_quantity(numbers_in("729 600 groszy")[0], s) for s in grosze)
    assert not any(same_quantity(numbers_in("729,600 grosze")[0], s) for s in grosze), "niejednoznaczne: po polsku 729,6"
    assert not same_quantity(numbers_in("2%")[0], source_values({"full_points": 2})[0])
    assert same_quantity(numbers_in("94,6")[0], source_values({"otif_pct": 94.6})[0]), "liczba bez jednostki zgadza się z każdą jednostką"


def test_money_helpers():
    assert grosze_to_pln(729600) == Decimal("7296.00")
    assert [round_grosze(Decimal(x)) for x in ("2.5", "2.49", "3.5", "246.4")] == [3, 2, 4, 246]


@pytest.mark.parametrize("text, phrase, found", [
    ("zapisano w notatce", "nota", False), ("warunek nie jest spełniony", "nie jest spełniony", True),
    ("27 296 PLN", "7 296", False),
    ("marża 19,9%", "9%", False), ("1 500 000 PLN", "500 000", False), ("zgoda (CFO).", "CFO", True),
])
def test_mentions_whole_phrases(text, phrase, found):
    assert mentions(text, phrase) is found


# --- zabezpieczenia: limit nigdy nie gubi dostarczonych wyników i nie pozwala zacząć nowej pracy

def invoice_tool(performed):
    @tool
    def get_invoice_value(supplier: str, month: str = "2026-07") -> dict:
        """Faktura (dubler testowy)."""
        performed.append(supplier)
        return {"status": "ok", "supplier_id": supplier, "month": month, "invoiced_grosze": 10000, "currency": "PLN"}
    return get_invoice_value


def parallel_calls(*suppliers):
    from langchain_core.messages import AIMessage
    return AIMessage(content="", tool_calls=[{"id": s.lower(), "name": "get_invoice_value", "args": {"supplier": s}}
                                             for s in suppliers])


def test_parallel_results_straddling_the_limit_are_all_kept():
    # model zużywa krok 1 z 2; paczka trzech narzędzi zostaje dopuszczona, a jej wyniki przekraczają limit
    performed = []
    model = ScriptedModel(script=[parallel_calls("A", "B", "C"), answer("gotowe")])
    trace = run_question(create_agent(model, [invoice_tool(performed)]), "faktury?", Budget(2, 60))
    assert sorted(performed) == ["A", "B", "C"]
    assert trace.status == "limit"
    assert sorted((e.call_id, e.status) for e in trace.events) == [("a", "ok"), ("b", "ok"), ("c", "ok")], \
        "każdy dostarczony wynik jest zapisany"
    assert model.calls == 1, "po wyczerpaniu limitu nie ma nowej tury modelu"


def test_parallel_workers_when_one_spends_the_shared_budget():
    from langchain_core.messages import AIMessage
    box = {"budget": Budget(max_steps=6, timeout_s=60)}
    performed = []
    looping = create_agent(ScriptedModel(script=[lambda m: call("get_invoice_value", supplier="L")] * 20),
                                 [invoice_tool(performed)])
    quick = create_agent(ScriptedModel(script=[call("get_invoice_value", supplier="Q"), answer("100 PLN")]),
                               [invoice_tool(performed)])

    @tool
    def ask_looping(task: str) -> dict:
        """Specjalista, który się zapętla (dubler testowy)."""
        return worker_result(run_question(looping, task, box["budget"], agent_name="looping"))

    @tool
    def ask_quick(task: str) -> dict:
        """Szybki specjalista (dubler testowy)."""
        return worker_result(run_question(quick, task, box["budget"], agent_name="quick"))

    both = AIMessage(content="", tool_calls=[{"id": "w1", "name": "ask_looping", "args": {"task": "t"}},
                                             {"id": "w2", "name": "ask_quick", "args": {"task": "t"}}])
    supervisor = create_agent(ScriptedModel(script=[both, answer("gotowe")]), [ask_looping, ask_quick])
    trace = run_question(supervisor, "q", box["budget"])
    assert trace.status == "limit"
    wrappers = {e.call_id: e for e in trace.events if e.origin == "worker_summary"}
    assert set(wrappers) == {"w1", "w2"}, "wyniki obu specjalistów są zapisane"
    assert {e.agent for e in trace.events if e.origin == "data"} <= {"looping", "quick"}
    assert all(e.parent_call_id in wrappers for e in trace.events if e.origin == "data"), "zagnieżdżone dowody zostają zachowane"


def test_no_new_task_starts_when_the_steps_are_exactly_used():
    # 2 kroki: model (1) i narzędzie (2) zużywają wszystkie, więc kolejne wywołanie modelu się nie zaczyna
    model = ScriptedModel(script=[call("get_invoice_value", supplier="A"), answer("gotowe")])
    trace = run_question(create_agent(model, [invoice_tool([])]), "faktura?", Budget(2, 60))
    assert (trace.status, trace.answer, trace.steps, model.calls) == ("limit", None, 2, 1)
    assert [e.status for e in trace.events] == ["ok"], "dostarczony wynik zostaje zachowany"


def test_an_answer_completing_exactly_on_the_limit_succeeds():
    model = ScriptedModel(script=[call("get_invoice_value", supplier="A"), answer("gotowe")])
    trace = run_question(create_agent(model, [invoice_tool([])]), "faktura?", Budget(3, 60))
    assert (trace.status, trace.answer, trace.steps) == ("answered", "gotowe", 3)


@pytest.mark.parametrize("budget", [Budget(0, 60), "spent"])
def test_a_zero_or_used_up_step_budget_starts_nothing(budget):
    if budget == "spent":                      # wspólny limit, który inni specjaliści supervisora już wyczerpali
        budget = Budget(24, 60)
        budget.steps = 24
    model = ScriptedModel(script=[answer("za późno")])
    trace = run_question(create_agent(model, []), "dzień dobry", budget)
    assert trace.status == "limit" and model.calls == 0


def test_a_spent_budget_starts_no_model_call():
    model = ScriptedModel(script=[answer("za późno")])
    trace = run_question(create_agent(model, []), "dzień dobry", Budget(20, -1))
    assert trace.status == "limit" and model.calls == 0


def test_a_late_final_answer_is_limit():
    import time

    def slow(messages):
        time.sleep(0.05)
        return answer("spóźniona")
    trace = run_question(create_agent(ScriptedModel(script=[slow]), []), "dzień dobry", Budget(20, 0.01))
    assert (trace.status, trace.answer) == ("limit", "spóźniona")


def test_two_levels_of_workers_keep_parents_and_origins():
    shared, performed = Budget(30, 60), []
    leaf = create_agent(ScriptedModel(script=[call("get_invoice_value", supplier="A"), answer("100 PLN")]),
                              [invoice_tool(performed)])

    @tool
    def ask_leaf(task: str) -> dict:
        """Specjalista na najniższym poziomie (dubler testowy)."""
        return worker_result(run_question(leaf, task, shared, agent_name="leaf"))

    middle = create_agent(ScriptedModel(script=[call("ask_leaf", task="faktura"), answer("100 PLN")]), [ask_leaf])

    @tool
    def ask_middle(task: str) -> dict:
        """Specjalista na środkowym poziomie (dubler testowy)."""
        return worker_result(run_question(middle, task, shared, agent_name="middle"))

    top = create_agent(ScriptedModel(script=[call("ask_middle", task="faktura"), answer("100 PLN")]), [ask_middle])
    trace = run_question(top, "faktura", shared)
    assert trace.status == "answered" and trace.steps == 9
    assert [e.origin for e in trace.events] == ["worker_summary", "worker_summary", "data"]
    assert trace.events[1].parent_call_id == trace.events[0].call_id
    assert trace.events[2].parent_call_id == trace.events[1].call_id


# --- zabezpieczenia: powtórzone dane wejściowe nigdy nie są dowodem

def test_only_retrieved_or_computed_fields_are_evidence():
    from helpers.agent_trace import evidence_values

    def values(tool, result):
        return {(str(q.value), q.unit) for q in evidence_values(tool, result)}
    assert values("search_documents", {"status": "no_results", "query": "Czy kara wynosi 123456 PLN?", "passages": []}) == set()
    assert values("search_documents", {"status": "ok", "query": "123456?", "passages": [
        {"doc_id": "CON-103", "chunk_id": "CON-103#ctx003", "text": "98% palet"}]}) == {("98", "%")}
    assert values("calculate_otif_penalty", {"status": "ok", "otif_pct": 94.6, "invoice_grosze": 18240000,
                                             "full_points": 2, "penalty_pct": 4.0, "penalty_grosze": 729600}) == \
        {("2", "pp"), ("4.0", "%"), ("7296", "PLN"), ("729600", "grosze")}, "powtórzone dane wejściowe kalkulatora nie są dowodem"
    assert values("get_supplier_otif", {"status": "no_data", "requested": {"from": "2026-10", "to": "2026-10"},
                                        "observations": [], "missing_months": ["2026-10"],
                                        "message": "brak danych za 2026-10 (szacunek: 95%)"}) == set()
    assert values("ask_data_analyst", {"summary": "1926 PLN"}) == set()


# --- zabezpieczenia: formatowanie i znaki

@pytest.mark.parametrize("text, expected", [
    ("**729 600** PLN", [("729600", "PLN")]),
    ("*7296,00* zł", [("7296.00", "PLN")]),
    ("`94,6`% i __2__ punkty procentowe", [("94.6", "%"), ("2", "pp")]),
    ("-7296 PLN; (−3%)", [("-7296", "PLN"), ("-3", "%")]),
    ("przedział 5-12%", [("5", None), ("12", "%")]),
    ("**2026** PLN", [("2026", "PLN")]),
])
def test_numbers_in_formatted_text(text, expected):
    assert [(str(q.value), q.unit) for q in numbers_in(text)] == expected


def test_mentions_ignores_markdown_and_respects_signs():
    assert mentions("**7 296** PLN", "7 296")
    assert not mentions("-7 296 PLN", "7 296") and not mentions("wynosi -7 296", "7 296")
    assert mentions("przedział 5-12%", "12%")


def test_the_supervisors_workers_report_tool_exceptions_too(config):
    # gotowe porównanie używa tych samych narzędzi bezpośrednich: wyjątek w wywołaniu specjalisty to zdarzenie błędu
    from helpers.agent_trace import AgentDeps
    from helpers.company import CompanyData
    from mini_project_4.src.compare_supervisor import build_supervisor
    from mini_project_4.tests.test_step3_build_agent import BrokenStore

    model = ScriptedModel(script=[call("ask_documents_analyst", task="Czego wymaga CON-103?"),     # supervisor
                                  call("search_documents", question="CON-103 palety"),               # worker
                                  answer("Wyszukiwanie się nie powiodło."),                          # specjalista
                                  answer("Nie udało mi się sprawdzić dokumentów.")])                 # supervisor
    deps = AgentDeps(llm=model, store=BrokenStore(), data=CompanyData(suppliers={}, otif={}, invoices={}), config=config)
    box = {"budget": Budget(20, 60)}
    trace = run_question(build_supervisor(deps, box), "CON-103?", box["budget"], agent_name="supervisor")
    assert trace.status == "answered"
    nested = [e for e in trace.events if e.tool == "search_documents"]
    assert [(e.status, e.agent) for e in nested] == [("error", "documents_analyst")]
    assert "RuntimeError" in nested[0].error


@pytest.mark.parametrize("text, expected", [
    ("Kara: 7296,00 PLN, czyli 2 pełne punkty procentowe poniżej celu; lipiec: 94,6%.",
     [("7296.00", "PLN"), ("2", "pp"), ("94.6", "%")]),
    ("18 240 000 groszy = 182 400 zł", [("18240000", "grosze"), ("182400", "PLN")]),
    ("7 296,00 zł i 12 złotych", [("7296.00", "PLN"), ("12", "PLN")]),
    ("2 pkt proc., 3 proc., 4 procent, 2 punkty procentowe", [("2", "pp"), ("3", "%"), ("4", "%"), ("2", "pp")]),
    ("Spotkanie 20 sierpnia 2026 r., nota do 5 września.", []),
    ("od 2 do 6°C; 2–6 °C", [("2", None), ("6", None), ("2", None), ("6", None)]),
])
def test_polish_notation(text, expected):
    assert [(str(q.value), q.unit) for q in numbers_in(text)] == expected


def test_an_ambiguous_number_is_reported_not_guessed():
    one_comma = numbers_in("1,500 PLN")[0]
    assert one_comma.ambiguous, "1,500 to po polsku 1,5, a po angielsku 1500"
    assert not same_quantity(one_comma, numbers_in("1500 PLN")[0]) and not same_quantity(one_comma, numbers_in("1,5 PLN")[0])
    assert not any(q.ambiguous for q in numbers_in("1,5 PLN; 1 500 PLN; 1,500.00 PLN; 1,500,000 PLN; 7296,00 PLN"))


def test_polish_numeric_dates_are_not_quantities():
    assert numbers_in("Umowa obowiązuje od 1.04.2025 do 31.03.2027 r.; kara 2%.") == numbers_in("kara 2%.")
