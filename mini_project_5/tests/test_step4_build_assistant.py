"""Testy kroku 4: całą rozmową zarządza jeden graf; każda ścieżka działa tak, jak opisują to Miniprojekty 3 i 4.
Wszystko przez JEDEN publiczny punkt wejścia, assistant_turn. Model ze skryptem, serwer MCP w pamięci."""

import pytest
from langchain_core.messages import HumanMessage

from helpers.assistant import assistant_turn, trace_from_record
from helpers.workflow import new_checkpointer
from mini_project_5.src.step4_build_assistant import build_assistant
from mini_project_5.tests.conftest import ScriptedChat, answer, answers, call, turn

DATA_Q = turn(kind="document_question", standalone="Na jaką kwotę Mleczna Dolina wystawiła fakturę za lipiec 2026 r.?")
SUBMIT_14 = turn(kind="approval_request", request_action="new", standalone="Prześlij do akceptacji rabat 14%, marża po rabacie 10%.",
                 discount_pct=14, margin_after_pct=10, customer="Biedronka")


def assistant_with(connection, config, turns, script=()):
    llm = ScriptedChat(turns=list(turns), script=list(script))
    return llm, build_assistant(llm, connection.tools(), config, new_checkpointer())


def test_a_data_question_goes_to_the_agent_over_mcp(connection, config):
    llm, a = assistant_with(connection, config, [DATA_Q],
                            [call("get_invoice_value", supplier="SUP-114", month="2026-07"), answer("182 400 PLN.")])
    entry = assistant_turn(a, "t", "Ile zafakturowała Mleczna Dolina w lipcu?", answers(), connection, turn=1)
    assert entry["turn"]["kind"] == "document_question" and entry["status"] == "answered"
    assert entry["reply"] == "182 400 PLN."
    trace = trace_from_record(entry["record"])
    assert trace.events[0].transport == "mcp" and llm.understand_calls == 1
    assert connection.captures[0]["thread_id"] == "t" and connection.captures[0]["turn"] == 1


def test_the_mp5_prompt_is_used_and_the_config_is_untouched(connection, config):
    before = config.get("prompts.understand_system")
    llm, a = assistant_with(connection, config, [turn(kind="other")])
    assistant_turn(a, "t", "Cześć", answers())
    assert llm.seen_systems == [config.get("prompts.assistant_understand_system")]
    assert config.get("prompts.understand_system") == before, "nigdy nie modyfikuj otrzymanej konfiguracji"


def test_a_policy_question_uses_mp3s_rules_with_no_tool_call(connection, config):
    llm, a = assistant_with(connection, config, [turn(kind="policy_question", discount_pct=22, margin_after_pct=7,
                                                      strategic_account=True)])
    entry = assistant_turn(a, "t", "Kto zatwierdza rabat 22% dla klienta strategicznego przy marży po rabacie 7%?", answers())
    assert entry["approvers"] == ["Dyrektor handlowy", "CFO"] and entry["pauses"] == []
    assert llm.agent_calls == 0 and connection.captures == [] and trace_from_record(entry["record"]) is None


def test_policy_then_submit_that(connection, config):
    policy = turn(kind="policy_question", discount_pct=22, margin_after_pct=7, strategic_account=True)
    submit = turn(kind="approval_request", request_action="new", discount_pct=22, margin_after_pct=7, strategic_account=True)
    llm, a = assistant_with(connection, config, [policy, submit])
    assistant_turn(a, "t", "Kto zatwierdza 22%...?", answers())
    entry = assistant_turn(a, "t", "Prześlij to.", answers("approved", "approved"))
    assert entry["pauses"] == [["approval", "Dyrektor handlowy"], ["approval", "CFO"]] and entry["status"] == "approved"
    assert llm.understand_calls == 2, "wznowienie nigdy nie uruchamia ponownie rozumienia wiadomości"
    assert llm.agent_calls == 0


def test_approval_then_a_data_question_then_an_unchanged_resubmission(connection, config):
    again = turn(kind="approval_request", request_action="update", discount_pct=14, margin_after_pct=10)
    llm, a = assistant_with(connection, config, [SUBMIT_14, DATA_Q, again],
                            [call("get_invoice_value", supplier="SUP-114", month="2026-07"), answer("182 400 PLN.")])
    first = assistant_turn(a, "t", "Prześlij do akceptacji rabat 14%, marża po rabacie 10%.", answers("approved"))
    assert first["status"] == "approved" and first["pauses"] == [["approval", "Dyrektor handlowy"]]
    question = assistant_turn(a, "t", "Ile zafakturowała Mleczna Dolina w lipcu?", answers())
    assert question["request"]["revision"] == 1 and question["approvals"] == {"Dyrektor handlowy": "approved"}, \
        "pytanie o dane nie zmienia zatwierdzonego wniosku"
    resubmitted = assistant_turn(a, "t", "Prześlij jeszcze raz ten sam rabat.", answers())
    assert resubmitted["pauses"] == [] and resubmitted["status"] == "approved" and resubmitted["request"]["revision"] == 1
    assert trace_from_record(resubmitted["record"]) is None, "na innej ścieżce nie zostaje nieaktualny trace agenta"
    assert llm.understand_calls == 3


def test_a_revised_resubmission_needs_new_approval(connection, config):
    revised = turn(kind="approval_request", request_action="update", discount_pct=22, margin_after_pct=10)
    _, a = assistant_with(connection, config, [SUBMIT_14, revised])
    assistant_turn(a, "t", "Prześlij rabat 14%.", answers("approved"))
    entry = assistant_turn(a, "t", "Jednak zróbmy 22%.", answers("approved", "approved"))
    assert entry["request"]["revision"] == 2 and entry["pauses"] == [["approval", "CEO"], ["approval", "CFO"]]


@pytest.mark.parametrize("outcome", ["rejected", "cancel"])
def test_a_rejected_or_cancelled_request_retries_from_the_first_role(connection, config, outcome):
    again = turn(kind="approval_request", request_action="update", discount_pct=14, margin_after_pct=10)
    _, a = assistant_with(connection, config, [SUBMIT_14, again])
    assistant_turn(a, "t", "Prześlij rabat 14%.", answers(outcome))
    retry = assistant_turn(a, "t", "Spróbuj jeszcze raz na tych samych warunkach.", answers("approved"))
    assert retry["pauses"] == [["approval", "Dyrektor handlowy"]] and retry["status"] == "approved"


def test_a_clarified_margin_is_used_by_a_later_question(connection, config):
    missing = turn(kind="approval_request", request_action="new", discount_pct=8)
    later = turn(kind="policy_question", discount_pct=12, margin_after_pct=7)
    llm, a = assistant_with(connection, config, [missing, later])
    first = assistant_turn(a, "t", "Prześlij do akceptacji rabat 8% na chipsy.", answers(7, "approved", "approved"))
    assert first["pauses"][0] == ["clarification", "margin_after_pct"] and first["status"] == "approved"
    entry = assistant_turn(a, "t", "Przy tej samej marży kto zatwierdziłby 12%?", answers())
    assert entry["approvers"] == ["Regionalny kierownik sprzedaży", "CFO"]
    assert llm.understand_calls == 2
    assert any("Marża po rabacie: 7" in text for text in llm.seen_understand[1]), \
        "doprecyzowana marża jest w historii, którą widzi następne rozumienie"


def test_a_paused_thread_refuses_a_new_message(connection, config):
    _, a = assistant_with(connection, config, [SUBMIT_14])
    cfg = {"configurable": {"thread_id": "t"}}
    a.invoke({"messages": [HumanMessage("Prześlij rabat 14%.")]}, cfg)            # zostaw go zatrzymanego, jak zrobiłby to klient, który uległ awarii
    assert a.get_state(cfg).next
    with pytest.raises(RuntimeError, match="pauza"):
        assistant_turn(a, "t", "Ile zafakturowała Mleczna Dolina?", answers())
    with pytest.raises(RuntimeError, match="pauza"):
        assistant_turn(a, "t", "Ile zafakturowała Mleczna Dolina?", answers(), connection, turn=2)
    assert connection.captures == []


def test_two_interleaved_threads_keep_their_own_state(connection, config):
    llm, a = assistant_with(connection, config, [DATA_Q, SUBMIT_14, DATA_Q],
                            [call("get_invoice_value", supplier="SUP-114", month="2026-07"), answer("A"),
                             call("get_invoice_value", supplier="SUP-207", month="2026-07"), answer("B")])
    one = assistant_turn(a, "one", "q1", answers(), connection, turn=1)
    two = assistant_turn(a, "two", "Prześlij rabat 14%.", answers("approved"), connection, turn=1)
    one_again = assistant_turn(a, "one", "q2", answers(), connection, turn=2)
    assert two["request"]["discount_pct"] == 14 and one_again["request"] is None, "wnioski nie przeciekają między wątkami"
    assert trace_from_record(one["record"]).answer == "A" and trace_from_record(one_again["record"]).answer == "B"
    assert [(c["thread_id"], c["turn"]) for c in connection.captures] == [("one", 1), ("one", 2)]


def test_the_trace_survives_a_checkpoint(connection, config):
    _, a = assistant_with(connection, config, [DATA_Q],
                          [call("get_invoice_value", supplier="SUP-114", month="2026-07"), answer("182 400 PLN.")])
    assistant_turn(a, "t", "q", answers())
    stored = a.get_state({"configurable": {"thread_id": "t"}}).values["record"]
    assert trace_from_record(stored).events[0].result["invoiced_grosze"] == 18240000


def test_overlapping_turns_on_one_connection_are_refused_and_captures_keep_their_owner(connection, config):
    # Dwie rozmowy, jedno połączenie. Pierwsza tura jest wstrzymana wewnątrz wywołania agenta;
    # druga tura na tym samym połączeniu musi zostać odrzucona, nigdy nie może błędnie oznaczyć dowodów pierwszej.
    import threading
    entered, release = threading.Event(), threading.Event()

    def held(messages):
        entered.set()
        release.wait(10)
        return answer("A")
    _, first = assistant_with(connection, config, [DATA_Q], [call("get_invoice_value", supplier="SUP-114", month="2026-07"), held])
    _, second = assistant_with(connection, config, [DATA_Q], [answer("B")])
    results = {}
    worker = threading.Thread(target=lambda: results.setdefault("one", assistant_turn(first, "one", "q", answers(), connection, turn=1)))
    worker.start()
    assert entered.wait(10)
    with pytest.raises(RuntimeError, match="jedna tura naraz"):
        assistant_turn(second, "two", "q", answers(), connection, turn=1)
    release.set()
    worker.join(10)
    assert results["one"]["status"] == "answered"
    assert [(c["thread_id"], c["turn"]) for c in connection.captures] == [("one", 1)]
    event = trace_from_record(results["one"]["record"]).events[0]
    assert event.invocation_id == connection.captures[0]["invocation_id"]


def test_the_chat_path_accepts_polish_answers_at_the_pauses(connection, config, monkeypatch):
    from mini_project_3.src import chat

    submit = turn(kind="approval_request", request_action="new", standalone="Prześlij rabat 8%.", discount_pct=8)
    llm, a = assistant_with(connection, config, [submit])
    typed = iter(["7,5", "zatwierdź", "zatwierdź"])
    monkeypatch.setattr("builtins.input", lambda prompt="": next(typed))
    monkeypatch.setattr(chat, "describe_request", lambda request: "…")
    entry = assistant_turn(a, "t", "Prześlij rabat 8% na chipsy.", chat.ask_human)
    assert entry["request"]["margin_after_pct"] == 7.5 and entry["status"] == "approved"
