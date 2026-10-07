from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from helpers.workflow import DiscountRequest, Turn
from mini_project_3.src.step2_understand_turn import understand_turn, update_request
from mini_project_3.tests.conftest import ReplayLLM, turn


def test_messages_are_system_history_message(config):
    llm = ReplayLLM([turn(kind="policy_question", discount_pct=22)])
    history = [HumanMessage("Kto zatwierdza rabat 15%?"), AIMessage("Dyrektor handlowy.")]
    result = understand_turn(history, "A rabat 22%?", llm, config)
    assert result.kind == "policy_question"
    sent = llm.prompts[0]
    assert isinstance(sent[0], SystemMessage) and sent[0].content == config.get("prompts.understand_system")
    assert sent[1:3] == history, "przekaż historię bez zmian, między wiadomością systemową a nową wiadomością"
    assert isinstance(sent[-1], HumanMessage) and sent[-1].content == "A rabat 22%?"


def test_model_failure_gives_an_error_turn(config):
    result = understand_turn([], "Prześlij rabat 10%.", ReplayLLM(fail=True), config)
    assert result.kind == "error" and result.request_action == "none" and result.standalone == "Prześlij rabat 10%."


def test_new_request_resets_flags():
    old = DiscountRequest(revision=3, discount_pct=30, margin_after_pct=4, clearance=True)
    new = update_request(old, turn(kind="approval_request", request_action="new", discount_pct=30, margin_after_pct=11))
    assert new.revision == 1 and new.clearance is False and new.margin_after_pct == 11, \
        "nowy wniosek zaczyna się od zera: nic nie przechodzi ze starego"


def test_update_patches_only_given_fields():
    old = DiscountRequest(revision=1, discount_pct=14, margin_after_pct=10, strategic_account=True)
    new = update_request(old, turn(kind="approval_request", request_action="update", discount_pct=18))
    assert (new.revision, new.discount_pct, new.margin_after_pct, new.strategic_account) == (2, 18, 10, True)
    reset = update_request(new, turn(kind="approval_request", request_action="update", strategic_account=False))
    assert reset.strategic_account is False and reset.revision == 3, "jawne False zeruje flagę"


def test_unchanged_update_keeps_the_revision():
    old = DiscountRequest(revision=2, discount_pct=18, margin_after_pct=10)
    assert update_request(old, turn(kind="approval_request", request_action="update", discount_pct=18)).revision == 2


def test_only_approval_requests_change_the_request():
    old = DiscountRequest(revision=1, discount_pct=14)
    assert update_request(old, turn(kind="policy_question", discount_pct=22)) is old
    assert update_request(None, turn(kind="other")) is None


def test_an_approval_request_must_say_new_or_update():
    import pytest

    with pytest.raises(ValueError):
        update_request(DiscountRequest(revision=1, discount_pct=8), turn(kind="approval_request", request_action="none", discount_pct=22))
    with pytest.raises(ValueError):
        update_request(None, turn(kind="approval_request", request_action="none", discount_pct=22))


def test_update_without_a_current_request_starts_one():
    new = update_request(None, turn(kind="approval_request", request_action="update", discount_pct=8, margin_after_pct=10))
    assert new.revision == 1 and new.discount_pct == 8
