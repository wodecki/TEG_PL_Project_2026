"""KROK 4: Końcowy asystent: jedna rozmowa, wszystkie ścieżki

CEL
    Zbuduj asystenta z przygotowanych wcześniej komponentów: grafu copilota z Miniprojektu 3 (interpretuje każdą
    wiadomość RAZ, pamięta wniosek i jego kolejne wersje, dopytuje o brakujące dane i zatrzymuje
    się, żeby wymagane osoby mogły zatwierdzić wniosek), w którym węzeł z kroku 3 zastępuje
    odpowiedź na podstawie dokumentów. Dzięki temu na pytania o dokumenty ORAZ o dane firmy
    odpowiada agent przez MCP. Całą rozmową zarządza jeden graf: nie ma przed nim dodatkowego komponentu kierującego wiadomości (ang. router).

WYNIK
    assistant = build_assistant(llm, tools, config, new_checkpointer())
    assistant_turn(assistant, "t1",                                         (gotowa funkcja)
                   "Ile wynosi kara, którą Mleczna Dolina jest winna Kovalo za lipiec 2026 r.? Podaj kwotę w PLN.",
                   answer_pause)
    -> {"turn": {"kind": "document_question", ...}, "status": "answered", "record": {"kind": "agent_trace", ...}, ...}
    assistant_turn(assistant, "t1",
                   "Teraz prześlij do akceptacji rabat 14% na wodę niegazowaną dla Biedronki z marżą po rabacie 10%.",
                   answer_pause)
    -> {"turn": {"kind": "approval_request", ...}, "pauses": [["approval", "Dyrektor handlowy"]], ...}

WYMAGANIA (sprawdzają je testy)
    - Użyj assistant_config(config) (helpers/assistant.py): głębokiej kopii, w której rozumienie
      wiadomości korzysta z promptu Miniprojektu 5 (kieruje on też pytania o dane firmy na ścieżkę
      dokumentów). Nigdy nie modyfikuj otrzymanej konfiguracji.
    - Zbuduj graf copilota z Miniprojektu 3 (build_copilot_graph) z CopilotDeps(llm, store=None,
      config=<ta kopia>), a potem zastąp jego węzeł "answer_documents" węzłem z kroku 3. Użyj
      replace_node (gotowa funkcja) i otrzymanego checkpointera.
    - Węzeł z kroku 3 dostaje AgentDeps(llm, store=None, data=None, config=<ta kopia>) i narzędzia:
      agent sięga do dokumentów i danych wyłącznie przez narzędzia MCP.
    - Nic więcej się nie zmienia: na pytania o politykę rabatową odpowiadają reguły z Miniprojektu 3
      (bez wywołania narzędzia), wnioski o akceptację zatrzymują graf dla każdej wymaganej roli,
      a wznowienie nigdy nie uruchamia ponownie rozumienia wiadomości.

ZALECANE NARZĘDZIA
    helpers.assistant (assistant_config, replace_node); build_copilot_graph z Miniprojektu 3;
    twój krok 3. Przykłady: „Przybornik” w mini_project_5/README.md.

NA KONIEC SPRAWDŹ KOD POLECENIEM
    uv run pytest mini_project_5/tests/test_step4_build_assistant.py -v
"""

from helpers.agent_trace import AgentDeps
from helpers.assistant import assistant_config, replace_node
from helpers.workflow import CopilotDeps, new_checkpointer
from mini_project_3.src.step4_copilot_graph import build_copilot_graph
from mini_project_5.src.step3_answer_with_tools import answer_with_tools


def build_assistant(llm, tools: list, config, checkpointer):
    # TODO: twój kod – zobacz CEL, WYNIK i WYMAGANIA na początku pliku
    raise NotImplementedError("TODO: build_assistant")
