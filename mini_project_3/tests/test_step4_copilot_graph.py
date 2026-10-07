from helpers.workflow import CopilotDeps, run_turn, new_checkpointer

from mini_project_3.src.step4_copilot_graph import build_copilot_graph
from mini_project_3.tests.conftest import NoStore, ReplayLLM, turn


def graph_with(config, turns):
    llm = ReplayLLM(turns)
    return build_copilot_graph(CopilotDeps(llm=llm, store=NoStore(), config=config), new_checkpointer()), llm


def answers(*values):
    it = iter(values)
    return lambda payload: next(it)


def test_clarification_then_role_by_role_approval(config):
    graph, llm = graph_with(config, [turn(kind="approval_request", request_action="new", discount_pct=8)])
    t = run_turn(graph, "t", "Prześlij rabat 8% na chipsy.", answers("nie wiem", 7, "approved", "approved"))
    assert t["pauses"] == [["clarification", "margin_after_pct"], ["clarification", "margin_after_pct"],
                           ["approval", "Regionalny kierownik sprzedaży"], ["approval", "CFO"]], \
        "zapytaj o marżę (ponownie, jeśli odpowiedź nie jest liczbą), a potem jedna pauza akceptacji na każdą rolę"
    assert t["status"] == "approved" and t["request"]["margin_after_pct"] == 7 and t["request"]["revision"] == 1
    assert llm.calls["Turn"] == 1, "wznowienie nie może ponownie uruchomić zrozumienia wiadomości"


def test_rejection_ends_and_cancel_cancels(config):
    graph, _ = graph_with(config, [turn(kind="approval_request", request_action="new", discount_pct=22, margin_after_pct=10),
                                   turn(kind="approval_request", request_action="new", discount_pct=22, margin_after_pct=10)])
    t = run_turn(graph, "t", "Prześlij rabat 22%.", answers("approved", "rejected"))
    assert t["pauses"] == [["approval", "CEO"], ["approval", "CFO"]] and t["status"] == "rejected"
    t = run_turn(graph, "t", "Prześlij ponownie rabat 22%.", answers("cancel"))
    assert t["pauses"] == [["approval", "CEO"]] and t["status"] == "cancelled"


def test_an_update_needs_new_approval(config):
    graph, _ = graph_with(config, [turn(kind="approval_request", request_action="new", discount_pct=14, margin_after_pct=10),
                                   turn(kind="approval_request", request_action="update", discount_pct=18)])
    first = run_turn(graph, "t", "Prześlij rabat 14%.", answers("approved"))
    assert first["status"] == "approved"
    second = run_turn(graph, "t", "Zmień na 18%.", answers("approved"))
    assert second["request"]["revision"] == 2 and second["pauses"] == [["approval", "Dyrektor handlowy"]], \
        "zmieniony wniosek (nowa wersja) trzeba zatwierdzić ponownie"


def test_clearance_without_margin_needs_no_clarification(config):
    graph, _ = graph_with(config, [turn(kind="approval_request", request_action="new", discount_pct=30, clearance=True)])
    t = run_turn(graph, "t", "Prześlij rabat 30% na wyprzedaż końcówek.", answers("approved"))
    assert t["pauses"] == [["approval", "Regionalny kierownik sprzedaży"]], "minimalna marża nie dotyczy wyprzedaży końcówek"


def test_policy_questions_never_pause(config):
    graph, _ = graph_with(config, [turn(kind="policy_question", discount_pct=22, margin_after_pct=7)])
    t = run_turn(graph, "t", "Kto zatwierdza rabat 22% przy marży 7%?", answers())
    assert t["pauses"] == [] and t["status"] == "answered" and t["approvers"] == ["CEO", "CFO"]


# --- Przejścia cyklu życia: każdy wynik approved musi znaczyć,
# --- że każda wymagana rola zatwierdziła BIEŻĄCY wniosek.

def assert_fully_approved(t):
    assert t["status"] == "approved"
    assert t["approvers"] and all(t["approvals"].get(role) == "approved" for role in t["approvers"]), \
        f"'approved' wymaga, żeby wartość każdej wymaganej roli była 'approved'; jest {t['approvals']}"


def test_rejection_then_unchanged_resubmission_starts_a_fresh_cycle(config):
    graph, _ = graph_with(config, [turn(kind="approval_request", request_action="new", discount_pct=22, margin_after_pct=10),
                                   turn(kind="approval_request", request_action="update", discount_pct=22)])
    first = run_turn(graph, "t", "Prześlij rabat 22%, marża 10%.", answers("approved", "rejected"))
    assert first["status"] == "rejected"
    again = run_turn(graph, "t", "Prześlij go ponownie, 22%.", answers("approved", "approved"))
    assert again["pauses"] == [["approval", "CEO"], ["approval", "CFO"]], "odrzucenie nigdy nie zamienia się w akceptację"
    assert again["request"]["revision"] == 1
    assert_fully_approved(again)


def test_rejection_by_the_first_role_ends_the_attempt(config):
    graph, _ = graph_with(config, [turn(kind="approval_request", request_action="new", discount_pct=22, margin_after_pct=10)])
    t = run_turn(graph, "t", "Prześlij rabat 22%.", answers("rejected"))
    assert t["pauses"] == [["approval", "CEO"]] and t["status"] == "rejected"


def test_cancel_after_one_approval_then_retry_starts_fresh(config):
    graph, _ = graph_with(config, [turn(kind="approval_request", request_action="new", discount_pct=22, margin_after_pct=10),
                                   turn(kind="approval_request", request_action="update", discount_pct=22)])
    assert run_turn(graph, "t", "Prześlij rabat 22%.", answers("approved", "cancel"))["status"] == "cancelled"
    retry = run_turn(graph, "t", "Prześlij go ponownie.", answers("approved", "approved"))
    assert retry["pauses"] == [["approval", "CEO"], ["approval", "CFO"]], "akceptacje z anulowanej próby nie przechodzą dalej"
    assert_fully_approved(retry)


def test_approved_unchanged_resubmission_needs_no_new_pause(config):
    graph, _ = graph_with(config, [turn(kind="approval_request", request_action="new", discount_pct=14, margin_after_pct=10),
                                   turn(kind="approval_request", request_action="update", discount_pct=14)])
    run_turn(graph, "t", "Prześlij rabat 14%.", answers("approved"))
    again = run_turn(graph, "t", "Prześlij ponownie rabat 14%.", answers())
    assert again["pauses"] == [] and "Już zatwierdzone" in again["reply"]
    assert_fully_approved(again)


def test_cancellation_does_not_leak_into_the_next_request(config):
    graph, _ = graph_with(config, [turn(kind="approval_request", request_action="new", discount_pct=8, margin_after_pct=10),
                                   turn(kind="approval_request", request_action="new", discount_pct=8)])
    assert run_turn(graph, "t", "Prześlij rabat 8%, marża 10%.", answers("cancel"))["status"] == "cancelled"
    t = run_turn(graph, "t", "Nowe zamówienie: rabat 8% na chipsy.", answers(10, "approved"))
    assert t["pauses"] == [["clarification", "margin_after_pct"], ["approval", "Regionalny kierownik sprzedaży"]], \
        "poprawne doprecyzowanie NOWEGO wniosku musi przejść do akceptacji niezależnie od statusu poprzedniego wniosku"
    assert_fully_approved(t)


def test_cancel_at_the_clarification_itself(config):
    graph, _ = graph_with(config, [turn(kind="approval_request", request_action="new", discount_pct=8)])
    t = run_turn(graph, "t", "Prześlij rabat 8%.", answers("cancel"))
    assert t["pauses"] == [["clarification", "margin_after_pct"]] and t["status"] == "cancelled"


def test_the_clarification_answer_is_in_the_next_prompt(config):
    graph, llm = graph_with(config, [turn(kind="approval_request", request_action="new", discount_pct=22),
                                     turn(kind="policy_question", discount_pct=18, margin_after_pct=7.37)])
    run_turn(graph, "t", "Prześlij rabat 22%.", answers(7.37, "approved", "approved"))
    run_turn(graph, "t", "Kto zatwierdziłby rabat 18% przy tej samej marży?", answers())
    human_lines = [m.content for m in llm.prompts[-1] if m.type == "human"]
    assert any("7,37" in line for line in human_lines[:-1]), \
        "odpowiedź z doprecyzowania musi trafić do rozmowy jako wiadomość menedżera, żeby następne zrozumienie wiadomości ją widziało"
