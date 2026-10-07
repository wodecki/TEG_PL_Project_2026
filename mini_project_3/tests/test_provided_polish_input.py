"""Gotowe testy: polskie odpowiedzi człowieka na pauzy (helpers/text_pl.py), przez prawdziwą ścieżkę czatu."""

import pytest

from helpers.text_pl import human_answer, number, parse_number
from helpers.workflow import run_turn
from mini_project_3.src import chat
from mini_project_3.tests.conftest import turn
from mini_project_3.tests.test_step4_copilot_graph import graph_with


@pytest.mark.parametrize("text, value", [("7,5", 7.5), ("7.5", 7.5), ("7", 7.0), ("-2", -2.0), (" 7,5 % ", 7.5),
                                         ("1,500", 1.5)])
def test_a_typed_margin_in_either_notation(text, value):
    assert parse_number(text) == value


@pytest.mark.parametrize("text", ["siedem", "1,5.0", "7 5", "inf", "nan", ""])
def test_anything_else_is_not_a_number(text):
    assert parse_number(text) is None


def test_polish_and_english_commands_map_to_the_workflow_values():
    assert [human_answer("approval", t) for t in ("Zatwierdź", "odrzuć", "anuluj", "approved", "cancel")] == \
        ["approved", "rejected", "cancel", "approved", "cancel"]
    assert human_answer("clarification", "anuluj") == "cancel"
    assert human_answer("approval", "może") == "może", "nieznana odpowiedź przechodzi bez zmian: graf pyta ponownie"


def test_numbers_for_people_use_the_polish_notation():
    assert [number(x) for x in (5.01, 12.0, 18240000, 7296.0, -3.25)] == ["5,01", "12", "18 240 000", "7296", "-3,25"]


def test_the_chat_path_accepts_a_polish_margin_and_polish_commands(config, monkeypatch):
    graph, _ = graph_with(config, [turn(kind="approval_request", request_action="new", discount_pct=8)])
    typed = iter(["7,5", "może", "zatwierdź", "Zatwierdź"])
    monkeypatch.setattr("builtins.input", lambda prompt="": next(typed))
    monkeypatch.setattr(chat, "describe_request", lambda request: "…")
    entry = run_turn(graph, "t", "Prześlij rabat 8% na chipsy.", chat.ask_human)
    assert entry["request"]["margin_after_pct"] == 7.5
    assert entry["pauses"][0] == ["clarification", "margin_after_pct"]
    assert [p[0] for p in entry["pauses"][1:]] == ["approval"] * 3, "„może” to nie decyzja: graf ponownie pyta tę samą rolę"
    assert entry["status"] == "approved"


def test_the_chat_path_cancels_in_polish(config, monkeypatch):
    graph, _ = graph_with(config, [turn(kind="approval_request", request_action="new", discount_pct=8)])
    monkeypatch.setattr("builtins.input", lambda prompt="": "anuluj")
    entry = run_turn(graph, "t", "Prześlij rabat 8% na chipsy.", chat.ask_human)
    assert entry["status"] == "cancelled"
