"""KROK 3: Graf rozmowy (punkt kontrolny 3a: kierowanie, stan, odpowiedzi)

CEL
    Połącz swoje kroki w przepływ pracy (ang. workflow) w LangGraph, który prowadzi rozmowę. Każda wiadomość
    użytkownika przechodzi przez jeden węzeł „understand”, a potem krawędź warunkowa
    kieruje ją dalej: pytania o dokumenty do answer_question z Miniprojektu 2, pytania
    o politykę do twojego silnika reguł (tylko do odczytu: wyjaśnia, nigdy nie
    rozpoczyna akceptacji), wnioski o akceptację do stanu wniosku, a wszystko inne do
    krótkiej odpowiedzi. Mechanizm zapisu stanu (ang. checkpointer) przechowuje każdą rozmowę
    jako osobny wątek (ang. thread).

WYNIK
    conversation_nodes(deps) zwraca twoje funkcje węzłów jako słownik {nazwa: funkcja},
    żeby krok 4 mógł ich użyć ponownie. build_conversation_graph(deps, checkpointer)
    łączy je i zwraca skompilowany graf:

        graph = build_conversation_graph(deps, new_checkpointer())
        cfg = {"configurable": {"thread_id": "manager-1"}}
        graph.invoke({"messages": [HumanMessage("Kto zatwierdza rabat 15% dla zwykłego klienta?")]}, cfg)
        graph.get_state(cfg).values["decision"].approvers   -> ['Dyrektor handlowy']
        graph.get_state(cfg).values["status"]                -> 'answered'

WYMAGANIA (sprawdzają je testy)
    - Stan: helpers.workflow.CopilotState. Wejście w każdej turze rozmowy:
      {"messages": [HumanMessage(...)]}.
    - understand: understand_turn(<wcześniejsze wiadomości>, <tekst ostatniej wiadomości>,
      deps.llm, deps.config); zapisz wynik w "turn" i wyczyść pola dotyczące jednej tury
      ("decision", "record", "error").
    - Kieruj według turn.kind:
      document_question -> answer_question(turn.standalone, deps.store, deps.llm,
          deps.config) (Miniprojekt 2); zachowaj RunRecord w "record"
          (record.model_dump()); odpowiedz treścią odpowiedzi; status "answered".
          Nieudana odpowiedź (record.error albo wyjątek z wyszukiwania) -> status
          "error", nigdy awaria programu.
      policy_question -> required_approvers dla DiscountRequest zbudowanego z Turn
          (flagi o wartości None liczą się jako False); zapisz wynik w "decision";
          odpowiedz listą osób zatwierdzających i uzasadnieniami; status "answered".
          NIE wolno zmienić "request" ani "approvals". Brak podanego rabatu ->
          odpowiedź z pytaniem o rabat.
      approval_request -> update_request(state["request"], turn) rozpoczyna albo
          wznawia CYKL ŻYCIA wniosku, w jednym miejscu:
          - zachowaj "approvals" tylko wtedy, gdy wniosek się nie zmienił ORAZ każda
            wymagana rola już zatwierdziła (role wymagane dla tego wniosku policz
            ponownie przez required_approvers: "decision" z poprzedniej tury jest już
            wyczyszczona w understand); w przeciwnym razie (nowe warunki albo
            ponowne złożenie po odrzuceniu lub anulowaniu) "approvals" staje się {}
            – nowy cykl;
          - ustaw "status" od nowa: "pending_clarification", gdy brakuje marży (a towar
            nie jest wyprzedażą końcówek), w przeciwnym razie "pending_approval";
          potem (krok 3) required_approvers -> "decision". ValueError z update_request
          albo z reguł -> status "error" z komunikatem jako odpowiedzią; nic innego
          się nie zmienia.
      other -> krótka odpowiedź, bez wyszukiwania i bez wywołania LLM-a; status
          "answered".
      error -> odpowiedź z prośbą o przeformułowanie; status "error".
    - Każda gałąź dodaje do "messages" jedną odpowiedź AIMessage i kończy turę.
    - Skompiluj graf z podanym checkpointerem (do wypróbowania grafu: new_checkpointer()
      z helpers/workflow.py, checkpointer w pamięci, który zna typy workflow).
    Wskazówka projektowa (krok 4 od niej zależy): krok 4 używa tych węzłów ponownie
    i pyta o brakującą marżę PO aktualizacji wniosku, a PRZED decyzją (do podjęcia decyzji
    potrzebna jest marża). Dlatego aktualizacja wniosku powinna być jednym węzłem, który
    NIE dodaje odpowiedzi, a decyzja z odpowiedzią – drugim. W kroku 4 tura z wnioskiem
    o akceptację może wtedy mieć więcej niż jedną odpowiedź (decyzję, a potem wynik
    akceptacji); zasada jednej odpowiedzi powyżej dotyczy tego grafu.

ZALECANE NARZĘDZIA
    StateGraph, START, END, add_conditional_edges z langgraph.graph;
    AIMessage. Przykłady: „Przybornik” w mini_project_3/README.md.

NA KONIEC SPRAWDŹ KOD POLECENIEM
    uv run pytest mini_project_3/tests/test_step3_conversation_graph.py -v
"""

from langchain_core.messages import AIMessage
from langgraph.graph import END, START, StateGraph

from helpers.workflow import CopilotDeps, CopilotState, DiscountRequest, new_checkpointer
from mini_project_2.src.step2_answer_question import answer_question
from mini_project_3.src.step1_required_approvers import required_approvers
from mini_project_3.src.step2_understand_turn import update_request, understand_turn


def conversation_nodes(deps: CopilotDeps) -> dict:
    # TODO: twój kod – zobacz CEL, WYNIK i WYMAGANIA na początku pliku
    raise NotImplementedError("TODO: conversation_nodes")


def build_conversation_graph(deps: CopilotDeps, checkpointer):
    # TODO: twój kod – zobacz CEL, WYNIK i WYMAGANIA na początku pliku
    raise NotImplementedError("TODO: build_conversation_graph")
