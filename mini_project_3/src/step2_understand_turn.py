"""KROK 2: Zrozumienie wiadomości i aktualizacja wniosku

CEL
    Dwie części. Najpierw jedno wywołanie LLM-a z odpowiedzią w ustalonym schemacie
    (ang. structured output) odczytuje ostatnią wiadomość menedżera w kontekście rozmowy:
    jakiego rodzaju to wiadomość, czy zaczyna lub zmienia wniosek o rabat i jak brzmi
    przepisana tak, aby była zrozumiała bez reszty rozmowy. Następnie kod aktualizuje
    kanoniczny wniosek na podstawie tej interpretacji. Dzięki temu stan wniosku nie zależy od tego,
    jakimi słowami sformułowano wiadomości.

WYNIK
    understand_turn(history, message, llm, config) zwraca Turn (helpers/workflow.py):

        understand_turn([HumanMessage("Kto zatwierdza rabat 15% dla zwykłego klienta?"), AIMessage(...)],
                        "A 22%?", llm, config)
        -> Turn(kind='policy_question', request_action='none',
                standalone='Kto zatwierdza rabat 22% dla zwykłego klienta?',
                discount_pct=22.0, margin_after_pct=None, clearance=None, ...)

    update_request(current, turn) zwraca nowy kanoniczny DiscountRequest:

        update_request(DiscountRequest(revision=1, discount_pct=14.0, margin_after_pct=10.0,
                                       customer='Biedronka Express', product='woda', ...),
                       Turn(kind='approval_request', request_action='update', discount_pct=22.0,
                            margin_after_pct=10.0, customer=None, product=None, ...))
        -> DiscountRequest(revision=2, discount_pct=22.0, margin_after_pct=10.0, clearance=False,
                           strategic_account=False, competitor_offer=False,
                           customer='Biedronka Express', product='woda')

    (dialogi D1 i D2; pierwszy Turn pochodzi z przebiegu referencyjnego z gpt-5.4-mini)

WYMAGANIA (sprawdzają je testy)
    understand_turn:
    - Wysyłane wiadomości to kolejno: wiadomość systemowa z
      config.get("prompts.understand_system"), historia (bez zmian), a na końcu nowa
      wiadomość jako wiadomość człowieka (HumanMessage).
    - Użyj structured output z gotowym schematem Turn.
    - Nigdy nie zgłaszaj wyjątku z powodu modelu: przy każdym błędzie albo braku
      odpowiedzi zwróć Turn(kind="error", request_action="none", standalone=<wiadomość>).
    update_request:
    - Wniosek zmieniają tylko wiadomości typu approval_request: dla każdego innego
      rodzaju zwróć `current` bez zmian (może to być None).
    - Wiadomość approval_request musi mówić, co robi: request_action "none" zgłasza
      ValueError z pytaniem, czy to nowy wniosek, czy zmiana obecnego (workflow zamienia
      go w odpowiedź; nic się nie zmienia).
    - Nowy wniosek (request_action "new"; także "update", gdy nie ma jeszcze żadnego
      wniosku): nowy DiscountRequest z revision 1, wartościami z Turn i każdą flagą,
      która w Turn ma wartość None, ustawioną na False. Żadne dane nie są dziedziczone z poprzedniego
      wniosku.
    - W przeciwnym razie (aktualizacja): skopiuj `current`, zastąp tylko pola, które
      Turn ustawia (różne od None; jawne False zeruje flagę), i zwiększ revision o 1,
      jeśli cokolwiek się zmieniło. Bez zmian: ta sama revision.

ZALECANE NARZĘDZIA
    llm.with_structured_output(Turn), SystemMessage / HumanMessage z
    langchain_core.messages, DiscountRequest.model_copy(update=...).
    Przykłady: „Przybornik” w mini_project_3/README.md.

NA KONIEC SPRAWDŹ KOD POLECENIEM
    uv run pytest mini_project_3/tests/test_step2_understand_turn.py -v
"""

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AnyMessage, HumanMessage, SystemMessage

from helpers.config import Config
from helpers.workflow import DiscountRequest, Turn

FIELDS = ("discount_pct", "margin_after_pct", "clearance", "strategic_account", "competitor_offer", "customer", "product")
FLAGS = ("clearance", "strategic_account", "competitor_offer")


def understand_turn(history: list[AnyMessage], message: str, llm: BaseChatModel, config: Config) -> Turn:
    # TODO: twój kod – zobacz CEL, WYNIK i WYMAGANIA na początku pliku
    raise NotImplementedError("TODO: understand_turn")


def update_request(current: DiscountRequest | None, turn: Turn) -> DiscountRequest | None:
    # TODO: twój kod – zobacz CEL, WYNIK i WYMAGANIA na początku pliku
    raise NotImplementedError("TODO: update_request")
