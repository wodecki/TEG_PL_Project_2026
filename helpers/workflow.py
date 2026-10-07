"""Schematy wspólne dla kroków i programów Miniprojektu 3. Gotowy plik: nie edytujesz go.

Cztery struktury danych mają odrębne zadania:
  Turn             co LLM zrozumiał z jednej wiadomości (krok 2)
  DiscountRequest  kanoniczny wniosek, którego dotyczy rozmowa (krok 2 go aktualizuje)
  Decision         czego kursowa polityka wymaga dla wniosku (krok 1, zwykły kod)
  CopilotState     co graf przepływu pracy (ang. workflow) przekazuje między węzłami i turami rozmowy (kroki 3–4)
"""

from __future__ import annotations

from dataclasses import dataclass

from typing import Annotated, Any, Literal, TypedDict

from langchain_core.messages import AnyMessage

from langgraph.checkpoint.memory import MemorySaver
from langgraph.checkpoint.serde.jsonplus import JsonPlusSerializer
from langgraph.graph.message import add_messages
from pydantic import BaseModel, Field


class Turn(BaseModel):
    """Jak obsłużyć najnowszą wiadomość menedżera."""

    kind: Literal["document_question", "policy_question", "approval_request", "other", "error"] = Field(
        description="zobacz instrukcje; 'error' ustawia program, nigdy go nie wybieraj")
    request_action: Literal["new", "update", "none"] = Field(
        description="new: nowy wniosek o rabat; update: zmienia bieżący wniosek; none: ani jedno, ani drugie")
    standalone: str = Field(description="wiadomość przepisana tak, żeby była zrozumiała bez wcześniejszej rozmowy")
    discount_pct: float | None = Field(default=None, description="rabat w procentach, jeśli został podany w wiadomości lub przejęty z wcześniejszej rozmowy")
    margin_after_pct: float | None = Field(default=None, description="marża brutto PO rabacie, w procentach, jeśli została podana w wiadomości lub przejęta z wcześniejszej rozmowy")
    clearance: bool | None = Field(default=None, description="wyprzedaż końcówek? null, jeśli nie wspomniano")
    strategic_account: bool | None = Field(default=None, description="klient strategiczny? null, jeśli nie wspomniano")
    competitor_offer: bool | None = Field(default=None, description="udokumentowana oferta konkurencji? null, jeśli nie wspomniano")
    customer: str | None = Field(default=None, description="klient, jeśli został wymieniony")
    product: str | None = Field(default=None, description="produkt, jeśli został wymieniony")


class DiscountRequest(BaseModel):
    """Wniosek o rabat, którego dotyczy rozmowa. Flagi mają tu zawsze wartość true/false."""

    revision: int = 1
    discount_pct: float | None = None
    margin_after_pct: float | None = None
    clearance: bool = False
    strategic_account: bool = False
    competitor_offer: bool = False
    customer: str | None = None
    product: str | None = None


class Decision(BaseModel):
    """Czego kursowa polityka wymaga dla jednego wniosku."""

    approvers: list[str]                 # role w kolejności pytania o zgodę, np. ["CEO", "CFO"]
    reasons: list[str]                   # jeden wiersz na każdą regułę, która wpłynęła na wynik
    margin_checked: bool                 # False, gdy marża po rabacie była nieznana
    version: str                         # interpretacja polityki, np. "course-v1"


Status = Literal["answered", "pending_clarification", "pending_approval", "approved", "rejected", "cancelled", "error"]


class CopilotState(TypedDict, total=False):
    """Co przenosi graf. `messages` rośnie z każdą turą; reszta opisuje bieżącą sytuację."""

    messages: Annotated[list[AnyMessage], add_messages]
    turn: Turn | None                    # najnowsze zrozumienie wiadomości
    request: DiscountRequest | None      # kanoniczny wniosek
    decision: Decision | None            # wynik polityki dla `request` (albo dla pytania o politykę)
    approvals: dict[str, str]            # rola -> "approved" / "rejected", tylko dla bieżącej wersji wniosku
    status: Status
    record: dict | None                  # RunRecord z MP2 (jako dict) dla pytania o dokumenty
    error: str | None


@dataclass
class CopilotDeps:
    """Czego potrzebują węzły grafu. Testy przekazują atrapy, programy – prawdziwe obiekty."""

    llm: Any                             # model czatu (w testach atrapa)
    store: Any                           # kontekstowy vector store z MP2 (w testach atrapa)
    config: Any                          # helpers.config.Config


def run_turn(graph, thread_id: str, text: str, answer_pause, max_pauses: int = 10) -> dict:
    """Wysyła jedną wiadomość użytkownika do skompilowanego grafu, odpowiada na każdą pauzę
    i zapisuje przebieg tury.

    answer_pause(payload) zwraca wartość wznowienia dla pauzy: liczbę przy doprecyzowaniu,
    "approved" / "rejected" / "cancel" przy akceptacji. W run_dialogues.py odpowiedzi pochodzą
    ze scenariusza, a chat.py pyta ciebie. Zwraca wpis transkryptu, który da się zapisać jako JSON.

    Zasady cyklu życia, których pilnuje ta funkcja:
    - wątek, który nadal czeka na pauzie, nie przyjmuje nowej wiadomości (RuntimeError):
      najpierw go wznów;
    - jeśli odpowiedź na pauzę się nie uda (np. scenariusz nie ma odpowiedzi na nieoczekiwaną
      dodatkową pauzę), pauza zostaje ANULOWANA, żeby wątek nie zawisł, a wpis zachowuje
      wszystko, co zaobserwowano do tej pory – faktyczny Turn, wniosek, osoby zatwierdzające
      i każdą pauzę – ze statusem "error" i powodem w "error".
    """
    from langchain_core.messages import AIMessage, HumanMessage
    from langgraph.types import Command

    config = {"configurable": {"thread_id": thread_id}}
    if graph.get_state(config).next:
        raise RuntimeError(f"wątek {thread_id!r} czeka na odpowiedź (pauza): odpowiedz na pauzę, zanim wyślesz nową wiadomość")
    result = graph.invoke({"messages": [HumanMessage(text)]}, config)
    pauses, failure = [], None
    while result.get("__interrupt__"):
        payload = result["__interrupt__"][0].value
        pauses.append([payload["type"], payload.get("role") or payload.get("field")])
        try:
            if len(pauses) > max_pauses:
                raise RuntimeError(f"więcej niż {max_pauses} pauz w jednej turze: graf chyba się zapętlił")
            answer = answer_pause(payload)
        except Exception as exc:  # brak odpowiedzi na tę pauzę: anuluj ją, zachowaj to, co zaobserwowano
            failure = f"{type(exc).__name__} przy pauzie {payload['type']} {payload.get('role') or payload.get('field')}: {exc}"
            result = graph.invoke(Command(resume="cancel"), config)
            break
        result = graph.invoke(Command(resume=answer), config)
    state = graph.get_state(config).values
    turn, request, decision = state.get("turn"), state.get("request"), state.get("decision")
    replies = [m.content for m in state.get("messages", []) if isinstance(m, AIMessage)]
    return {
        "user": text,
        "turn": turn.model_dump() if turn else None,
        "request": request.model_dump() if request else None,
        "approvers": decision.approvers if decision else None,
        "reasons": decision.reasons if decision else None,
        "pauses": pauses,
        "approvals": state.get("approvals") or {},
        "status": "error" if failure else state.get("status"),
        "record": state.get("record"),
        "error": failure or state.get("error"),
        "reply": replies[-1] if replies else None,
    }


CHECKPOINT_TYPES = [(__name__, "Turn"), (__name__, "DiscountRequest"), (__name__, "Decision")]


def new_checkpointer() -> MemorySaver:
    """Checkpointer w pamięci, który zna własne typy workflow (Turn, DiscountRequest, Decision).

    LangGraph odtwarza stan zapisany na pauzie; ostrzega przy typach, których nikt nie zarejestrował,
    a przyszła wersja będzie je odrzucać. Rejestracja naszych typów utrzymuje czysty wynik
    i działające grafy."""
    return MemorySaver(serde=JsonPlusSerializer(allowed_msgpack_modules=CHECKPOINT_TYPES))
