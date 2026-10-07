"""Gotowy test: każda rozmowa (te z Miniprojektu 5, które łączą ścieżki, i dialogi z Miniprojektu 3)
odtworzona przez TWOJEGO asystenta z IDEALNYM rozumieniem wiadomości, oceniana według OCZEKIWANEJ
ścieżki każdej tury.

Bez LLM-a: udawany model zwraca wzorcowe `understand` każdej tury, a agent odpowiada na pytania
o dane stałym tekstem. Test sprawdza więc kierowanie na ścieżki, stan wniosku, pauzy i to, gdzie
trafiają zapisy przebiegu (trace). To, co odpowiada agent (sprawdzenia z Miniprojektu 4), mierzy
się na żywo: run_assistant_eval.py.
"""

import pytest

from helpers.assistant import assistant_turn
from helpers.assistant_eval import score_assistant_turn, summarise
from helpers.workflow import Turn, new_checkpointer
from mini_project_4.src.step4_score_trace import score_trace
from mini_project_5.src.step4_build_assistant import build_assistant
from mini_project_5.tests.conftest import ScriptedChat, all_conversations, answer


def replay(dialogue, connection, config):
    turns = [Turn(**t["understand"]) for t in dialogue["turns"]]
    data_turns = sum(t.kind == "document_question" for t in turns)
    llm = ScriptedChat(turns=turns, script=[answer("(odpowiedź agenta)")] * data_turns)
    assistant = build_assistant(llm, connection.tools(), config, new_checkpointer())
    scores = []
    for n, t in enumerate(dialogue["turns"], start=1):
        scripted = iter(t["resume"])
        entry = assistant_turn(assistant, dialogue["id"], t["user"], lambda payload: next(scripted), connection, turn=n)
        expect = {k: v for k, v in t["expect"].items() if k != "agent"}   # odpowiedź agenta sprawdza się tylko na żywo
        scores.append((t["user"], score_assistant_turn(entry, expect, [], score_trace)))
    assert llm.understand_calls == len(turns), "każda wiadomość jest rozumiana dokładnie raz, wznowienia nigdy"
    assert llm.agent_calls == data_turns, "agent działa tylko w turach z pytaniami o dane"
    return scores


@pytest.mark.parametrize("dialogue", all_conversations(), ids=lambda d: d["id"])
def test_every_conversation_replays_perfectly(dialogue, connection, config):
    scores = replay(dialogue, connection, config)
    wrong = [(user, {k: v for k, v in s.items() if v is False}) for user, s in scores if not all(v for v in s.values())]
    assert not wrong, f"przy idealnym rozumieniu każde sprawdzenie oczekiwanej ścieżki musi przejść; błędne: {wrong}"
    assert all(passed == assessed for passed, assessed in summarise([s for _, s in scores]).values())
