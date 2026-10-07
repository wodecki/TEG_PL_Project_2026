"""Gotowy test: ocena asystenta według ścieżki oczekiwanej we WZORCU; błąd nigdy nie usuwa sprawdzenia."""

import copy

import pytest

from helpers.agent_trace import Trace
from helpers.assistant import agent_trace_envelope
from helpers.assistant_eval import applicable, score_assistant_turn, summarise
from mini_project_4.src.step4_score_trace import score_trace
from mini_project_5.tests.conftest import all_conversations

CLAIMS = ["zatwierdziłem", "rabat został zatwierdzony", "jest już zatwierdzony"]   # frazy ze wzorca Miniprojektu 4


def gold_turn(dialogue_id: str, number: int) -> dict:
    dialogue = next(d for d in all_conversations() if d["id"] == dialogue_id)
    return dialogue["turns"][number - 1]


def entry(kind: str, *, trace: Trace | None = None, status="answered", **extra) -> dict:
    return {"user": "q", "turn": {"kind": kind, **extra.pop("turn_fields", {})}, "status": status,
            "record": agent_trace_envelope(trace) if trace else None, "pauses": [], "approvers": None,
            "request": None, **extra}


def test_d7_has_mp5_agent_gold_and_mp3s_file_is_unchanged(config):
    import yaml
    assert gold_turn("D7", 1)["expect"]["agent"]["needs"][0]["doc_id"] == "MTG-402"
    mp3 = yaml.safe_load(config.path("paths.mini_project_3_dialogues").read_text(encoding="utf-8"))
    assert "agent" not in mp3["dialogues"][6]["turns"][0]["expect"]


def test_a_fabricated_answer_with_no_tool_calls_fails_every_agent_check():
    # kontrprzykład z przeglądu: trace ze statusem answered, bez wywołań, z wymyśloną odpowiedzią
    t = gold_turn("D7", 1)
    fake = Trace(question=t["user"], answer="Zatwierdziłem rabat 99%. Ceny wody butelkowanej wzrosną o 777%.",
                 status="answered")
    score = score_assistant_turn(entry("document_question", trace=fake), t["expect"], CLAIMS, score_trace)
    assert score["route"] and score["agent_trace"] and score["status"]
    assert {k: score[k] for k in ("tool_coverage", "answer_facts", "numbers_backed", "no_approval_claim")} == \
        {"tool_coverage": False, "answer_facts": False, "numbers_backed": False, "no_approval_claim": False}


def test_a_missing_trace_fails_every_expected_agent_check():
    t = gold_turn("C1", 1)                                  # kara za lipiec: needs, obliczenie, kluczowe fakty
    score = score_assistant_turn(entry("document_question"), t["expect"], CLAIMS, score_trace)
    expected = [d for d in applicable(t["expect"])]
    assert list(score) == expected, "sprawdzenia wynikają ze wzorca, nie z tego, co się wydarzyło"
    for dim in ("agent_trace", "tool_coverage", "arguments_correct", "answer_facts", "numbers_backed", "no_approval_claim"):
        assert score[dim] is False, dim


def test_an_expected_calculation_that_never_happened_is_a_failure():
    t = gold_turn("C1", 1)
    no_calc = Trace(question=t["user"], answer="Kara wynosi 7296 PLN.", status="answered")
    score = score_assistant_turn(entry("document_question", trace=no_calc), t["expect"], CLAIMS, score_trace)
    assert score["arguments_correct"] is False, "MP4 zwraca None; wzorzec asystenta oczekiwał obliczenia"


def test_a_misrouted_data_turn_keeps_all_its_checks():
    t = gold_turn("C1", 1)
    score = score_assistant_turn(entry("policy_question", turn_fields={"discount_pct": 14}), t["expect"], CLAIMS,
                                 score_trace)
    assert score["route"] is False and list(score) == applicable(t["expect"])
    assert all(score[d] is False for d in ("tool_coverage", "arguments_correct", "answer_facts"))


def test_mp3s_extracted_fields_are_checked():
    t = gold_turn("D1", 1)                                  # fields: {discount_pct: 15}
    good = entry("policy_question", turn_fields={"discount_pct": 15.004}, approvers=["Dyrektor handlowy"])
    bad = entry("policy_question", turn_fields={"discount_pct": None}, approvers=["Dyrektor handlowy"])
    assert score_assistant_turn(good, t["expect"], CLAIMS, score_trace)["fields"] is True, "liczby równe z dokładnością do 0,01"
    assert score_assistant_turn(bad, t["expect"], CLAIMS, score_trace)["fields"] is False


def test_a_trace_on_a_policy_turn_is_a_failure():
    t = gold_turn("C2", 1)
    stray = Trace(question="q", answer="x", status="answered")
    score = score_assistant_turn(entry("policy_question", trace=stray, approvers=["Dyrektor handlowy", "CFO"]),
                                 t["expect"], CLAIMS, score_trace)
    assert score["agent_trace"] is False


@pytest.mark.parametrize("dialogue_id, number", [("C1", 1), ("C5", 1), ("D7", 1), ("C2", 1), ("D2", 2)])
def test_applicable_checks_depend_on_the_gold_only(dialogue_id, number):
    expect = gold_turn(dialogue_id, number)["expect"]
    assert applicable(copy.deepcopy(expect)) == applicable(expect)
    nothing = score_assistant_turn({"user": "q"}, expect, CLAIMS, score_trace)
    assert list(nothing) == applicable(expect), "pusty wpis jest oceniany w każdym sprawdzeniu, które definiuje wzorzec"
    assert nothing["route"] is False and nothing["status"] is False


def test_the_teaching_set_has_four_data_turns_with_agent_gold():
    data_turns = [t for d in all_conversations() for t in d["turns"]
                  if t["expect"]["kind"] == "document_question" and "agent" in t["expect"]]
    assert len(data_turns) == 4
    totals = summarise([score_assistant_turn({"user": "q"}, t["expect"], CLAIMS, score_trace) for t in data_turns])
    assert totals["numbers_backed"] == (0, 4) and totals["no_approval_claim"] == (0, 4)
