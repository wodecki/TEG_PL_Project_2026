"""Sprawdza gotową obsługę tury (helpers/workflow.run_turn) i pytanie o akceptację w chat.py. Nic tu nie piszesz."""

import pytest

from helpers.workflow import CopilotDeps, run_turn, new_checkpointer
from mini_project_3.src.step4_copilot_graph import build_copilot_graph
from mini_project_3.tests.conftest import NoStore, ReplayLLM, turn


def test_an_unexpected_extra_pause_keeps_the_evidence_and_cancels(config):
    """F3: wiadomość zrozumiano poprawnie, ale wniosek wymagał o jedną osobę zatwierdzającą więcej, niż przewidział skrypt."""
    llm = ReplayLLM([turn(kind="approval_request", request_action="new", discount_pct=14, margin_after_pct=7),
                     turn(kind="other")])
    graph = build_copilot_graph(CopilotDeps(llm=llm, store=NoStore(), config=config), new_checkpointer())
    scripted = iter(["approved"])

    def answer(payload):
        return next(scripted)

    t = run_turn(graph, "t", "Prześlij rabat 14%, marża 7%.", answer)
    assert t["turn"]["kind"] == "approval_request", "faktyczne zrozumienie wiadomości zostaje zachowane"
    assert t["pauses"] == [["approval", "Dyrektor handlowy"], ["approval", "CFO"]], "każda zaobserwowana pauza zostaje zachowana"
    assert t["status"] == "error" and "CFO" in t["error"]
    later = run_turn(graph, "t", "Dzięki!", lambda p: None)
    assert later["status"] == "answered", "zawieszoną pauzę anulowano, więc wątek przyjmuje nowe wiadomości"


def test_a_paused_thread_refuses_a_new_message(config):
    llm = ReplayLLM([turn(kind="approval_request", request_action="new", discount_pct=14, margin_after_pct=10)])
    graph = build_copilot_graph(CopilotDeps(llm=llm, store=NoStore(), config=config), new_checkpointer())
    from langchain_core.messages import HumanMessage

    graph.invoke({"messages": [HumanMessage("Prześlij rabat 14%.")]}, {"configurable": {"thread_id": "t"}})  # zostaje zatrzymany
    with pytest.raises(RuntimeError, match="pauza"):
        run_turn(graph, "t", "Dzięki!", lambda p: None)


def test_chat_shows_the_interpreted_request_before_asking(monkeypatch, capsys):
    """F6: osoba zatwierdzająca widzi, jak copilot zrozumiał wniosek, łącznie ze zmienioną wersją."""
    import mini_project_3.src.chat as chat

    monkeypatch.setattr("builtins.input", lambda prompt: "approved")
    payload = {"type": "approval", "role": "CFO", "revision": 2, "approvers": ["CEO", "CFO"],
               "request": {"revision": 2, "discount_pct": 22.0, "margin_after_pct": 7.0, "clearance": False,
                           "strategic_account": True, "competitor_offer": False, "customer": "Carrefour Express", "product": None}}
    assert chat.ask_human(payload) == "approved"
    shown = capsys.readouterr().out
    for value in ("Carrefour Express", "22%", "7%", "klient strategiczny", "wersja wniosku: 2"):
        assert value in shown, f"pytanie o akceptację musi pokazać {value!r}"
