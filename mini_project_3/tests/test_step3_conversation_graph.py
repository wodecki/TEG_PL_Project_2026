from langchain_core.messages import HumanMessage

from helpers.workflow import CopilotDeps, new_checkpointer
from mini_project_3.src.step3_conversation_graph import build_conversation_graph
from mini_project_3.tests.conftest import NoStore, ReplayLLM, turn


def ask(graph, thread, text):
    cfg = {"configurable": {"thread_id": thread}}
    graph.invoke({"messages": [HumanMessage(text)]}, cfg)
    return graph.get_state(cfg).values


def test_policy_question_answers_without_touching_the_request(config):
    llm = ReplayLLM([turn(kind="policy_question", discount_pct=22)])
    graph = build_conversation_graph(CopilotDeps(llm=llm, store=NoStore(), config=config), new_checkpointer())
    state = ask(graph, "t", "Kto zatwierdza rabat 22%?")
    assert state["decision"].approvers == ["CEO", "CFO"] and state["status"] == "answered"
    assert state.get("request") is None, "pytanie o politykę nie może utworzyć ani zmienić wniosku"
    assert state["messages"][-1].type == "ai", "każda tura kończy się jedną odpowiedzią"


def test_document_question_keeps_the_run_record(config, toy_store):
    llm = ReplayLLM([turn(kind="document_question", standalone="Co komitet postanowił w sprawie wody?")])
    graph = build_conversation_graph(CopilotDeps(llm=llm, store=toy_store, config=config), new_checkpointer())
    state = ask(graph, "t", "A ceny wody?")
    assert state["status"] == "answered" and state["record"]["question"] == "Co komitet postanowił w sprawie wody?", \
        "odpowiedz na pytanie STANDALONE funkcją answer_question z Miniprojektu 2 i zachowaj jej RunRecord w 'record'"


def test_other_and_error_never_search(config):
    llm = ReplayLLM([turn(kind="other"), turn(kind="error")])
    graph = build_conversation_graph(CopilotDeps(llm=llm, store=NoStore(), config=config), new_checkpointer())
    assert ask(graph, "t", "Dzięki!")["status"] == "answered"
    assert ask(graph, "t", "???")["status"] == "error"


def test_approval_request_updates_state_and_decides(config):
    llm = ReplayLLM([turn(kind="approval_request", request_action="new", discount_pct=14, margin_after_pct=10),
                     turn(kind="approval_request", request_action="update", discount_pct=22)])
    graph = build_conversation_graph(CopilotDeps(llm=llm, store=NoStore(), config=config), new_checkpointer())
    state = ask(graph, "t", "Prześlij rabat 14%, marża 10%.")
    assert state["status"] == "pending_approval" and state["decision"].approvers == ["Dyrektor handlowy"]
    assert state["request"].revision == 1
    state = ask(graph, "t", "Zmień na 22%.")
    assert state["request"].revision == 2 and state["request"].margin_after_pct == 10, "aktualizacja zachowuje pozostałe pola"
    assert state["decision"].approvers == ["CEO", "CFO"]


def test_threads_do_not_share_state(config):
    llm = ReplayLLM([turn(kind="approval_request", request_action="new", discount_pct=14, margin_after_pct=10),
                     turn(kind="policy_question", discount_pct=3)])
    graph = build_conversation_graph(CopilotDeps(llm=llm, store=NoStore(), config=config), new_checkpointer())
    ask(graph, "manager-a", "Prześlij rabat 14%.")
    other = ask(graph, "manager-b", "Kto zatwierdza rabat 3%?")
    assert other.get("request") is None and len(other["messages"]) == 2, "wątek manager-b nie może widzieć wniosku z wątku manager-a"


def test_an_ambiguous_approval_request_changes_nothing(config):
    llm = ReplayLLM([turn(kind="approval_request", request_action="new", discount_pct=8, margin_after_pct=10),
                     turn(kind="approval_request", request_action="none", discount_pct=22)])
    graph = build_conversation_graph(CopilotDeps(llm=llm, store=NoStore(), config=config), new_checkpointer())
    ask(graph, "t", "Prześlij rabat 8%, marża 10%.")
    state = ask(graph, "t", "22%?")
    assert state["status"] == "error" and state["request"].discount_pct == 8 and state["request"].revision == 1, \
        "request_action 'none' przy wniosku o akceptację nie może zmienić wniosku"
