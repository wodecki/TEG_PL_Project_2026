"""KROK 4: Graf copilota (punkt kontrolny 3b: doprecyzowanie, akceptacja, wznowienie)

CEL
    Rozbuduj obsługę statusu "pending_approval" w pełny przepływ pracy (ang. workflow).
    Najpierw uzupełnij wniosek o brakujące informacje (marżę po rabacie), a następnie
    poproś kolejno o decyzję osoby pełniące role wskazane przez politykę. Graf się ZATRZYMUJE
    (interrupt() z LangGraph) i kontynuuje działanie, gdy program wznowi go odpowiedzią.
    To symulacja do nauki: osoba, która odpowiada, odgrywa rolę; nic nie trafia do
    CRM-u i nikt nic nie obiecuje klientowi.

WYNIK
    build_copilot_graph(deps, checkpointer) zwraca skompilowany graf:

        out = graph.invoke({"messages": [HumanMessage(
            "Prześlij do akceptacji rabat 22% dla naszego klienta strategicznego "
            "Carrefour Express; marża po rabacie wynosi 7%.")]}, cfg)
        out["__interrupt__"][0].value
        -> {'type': 'approval', 'role': 'Dyrektor handlowy', 'revision': 1,
            'approvers': ['Dyrektor handlowy', 'CFO'], 'request': {...}}
        out = graph.invoke(Command(resume="approved"), cfg)      # następna pauza: CFO
        out = graph.invoke(Command(resume="approved"), cfg)
        graph.get_state(cfg).values["status"]                     -> 'approved'

WYMAGANIA (sprawdzają je testy)
    - Do wszystkiego, co robi krok 3, użyj ponownie węzłów z kroku 3 (conversation_nodes).
    - Po aktualizacji wniosku: jeśli margin_after_pct to None, a towar nie jest
      wyprzedażą końcówek, ZATRZYMAJ graf przed decyzją, żeby doprecyzować marżę:
          interrupt({"type": "clarification", "field": "margin_after_pct", "question": ...})
      Wartość wznowienia: liczba (marża) albo "cancel". Cokolwiek innego: zapytaj ponownie.
      Liczba uzupełnia bieżącą wersję wniosku (to brakująca informacja, nie zmiana),
      ustawia status "pending_approval" i trafia do "messages" jako wiadomość człowieka
      („Marża po rabacie: 7%”), żeby kolejne tury były rozumiane z jej
      uwzględnieniem.
      Kieruj według wyniku TEJ pauzy: cancel -> koniec; nadal brak -> zapytaj ponownie;
      w przeciwnym razie -> decyzja.
    - Po decyzji: ZATRZYMAJ graf raz dla każdej wymaganej roli, w kolejności
      decision.approvers, z pominięciem ról, które już są w "approvals":
          interrupt({"type": "approval", "role": <rola>, "revision": <revision>,
                     "approvers": <wszystkie role>, "request": <wniosek jako dict>})
      Wartość wznowienia: "approved", "rejected" albo "cancel"; cokolwiek innego:
      zapytaj ponownie. "rejected" -> status "rejected"; "cancel" -> status "cancelled".
      Status to "approved" tylko wtedy, gdy wartość KAŻDEJ wymaganej roli to dokładnie
      "approved" (jeśli tak jest już na starcie, zakończ bez pauzy, z odpowiedzią
      zawierającą „Już zatwierdzone”).
      Każde zakończenie dodaje odpowiedź.
    - Doprecyzowanie i akceptacja to osobne węzły. Wewnątrz nich przed interrupt() nie
      może się wykonać nic, co wywołuje LLM-a albo wywołuje skutki zewnętrzne, np. zapisuje dane: przy wznowieniu
      LangGraph uruchamia zatrzymany węzeł od początku, a zrozumienie wiadomości NIE
      może się wykonać ponownie.
    - Skompiluj graf z podanym mechanizmem zapisu stanu (ang. checkpointer), wymaganym do wznawiania po pauzie.

ZALECANE NARZĘDZIA
    interrupt z langgraph.types; add_conditional_edges; krawędź warunkowa, która
    prowadzi z węzła z powrotem do niego samego. Przykłady: „Przybornik”
    w mini_project_3/README.md.

NA KONIEC SPRAWDŹ KOD POLECENIEM
    uv run pytest mini_project_3/tests/test_step4_copilot_graph.py -v
"""

import math

from langchain_core.messages import AIMessage, HumanMessage
from langgraph.graph import END, START, StateGraph
from langgraph.types import interrupt

from helpers.text_pl import number
from helpers.workflow import CopilotDeps, CopilotState
from mini_project_3.src.step1_required_approvers import required_approvers  # jeśli któryś węzeł musi zdecydować ponownie
from mini_project_3.src.step3_conversation_graph import conversation_nodes


def build_copilot_graph(deps: CopilotDeps, checkpointer):
    # TODO: twój kod – zobacz CEL, WYNIK i WYMAGANIA na początku pliku
    raise NotImplementedError("TODO: build_copilot_graph")
