"""Uruchomienie agenta na jednym pytaniu i zapis tego, co zrobił. Gotowy plik: nie edytujesz go.

run_question() strumieniuje kroki agenta i tworzy obiekt Trace, czyli zapis przebiegu (ang. trace):
ostateczną odpowiedź (albo błąd) i każde wywołanie narzędzia po kolei, z argumentami, wynikiem
i POCHODZENIEM (ang. origin):
  data            rekord z narzędzia danych albo fragmenty z wyszukiwania: dowód ze źródła
  calculation     deterministyczne obliczenie (kara, polityka): dowód ze źródła
  worker_summary  wygenerowana odpowiedź agenta-specjalisty zwrócona supervisorowi:
                  NIE jest dowodem ze źródła, choć przychodzi jako wynik narzędzia
  unknown         wywołanie narzędzia, które nie istnieje
Jeden budżet obejmuje całe pytanie, razem ze specjalistami: limit, który zerowałby się przy każdym
wywołaniu specjalisty, nie byłby limitem. Budżet jest sprawdzany przed startem każdego nowego
zadania grafu (tura modelu, wywołanie narzędzia) i jeszcze raz na końcu. Wyniki już dostarczone
są zawsze zapisywane najpierw; po wyczerpaniu budżetu żadne nowe zadanie nie startuje, a status
to "limit", nawet jeśli nadeszła ostateczna odpowiedź (odpowiedź zostaje zachowana). Krok, który
już trwa, najpierw się kończy: czas oczekiwania na zawieszone wywołanie ogranicza limit czasu klienta
dostawcy modelu (ang. timeout), a nie ten budżet.

Tylko niektóre pola wyniku narzędzia są DOWODEM (`evidence_values`): to, co narzędzie znalazło
lub obliczyło. Dane wejściowe wysłane przez model, które wynik powtarza (zapytanie wyszukiwania,
miesiące z zapytania, dane wejściowe kalkulatora), oraz komunikaty dowodem nie są, bez względu
na to, jakie liczby zawierają.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

import yaml
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from pydantic import BaseModel, Field

from helpers.config import Config
from helpers.quantities import Quantity, source_values


# Narzędzia, które agent może mieć, i rodzaj dowodu, jaki każde z nich daje. Żadne z nich nie
# może niczego zatwierdzić, zapisać ani obiecać: to ograniczenie możliwości, sprawdzane w testach.
ORIGINS = {
    "search_documents": "data",
    "get_supplier_otif": "data",
    "get_invoice_value": "data",
    "get_contract_terms": "data",
    "calculate_otif_penalty": "calculation",
    "check_discount_policy": "calculation",
}
ALLOWED_TOOLS = frozenset(ORIGINS)
SOURCE_ORIGINS = frozenset({"data", "calculation"})

# Część wyniku każdego narzędzia, która jest dowodem: tylko wartości znalezione lub obliczone.
EVIDENCE_FIELDS = {
    "search_documents": ("passages",),                     # znaleziony tekst, a nie zapytanie
    "get_supplier_otif": ("observations",),                # a nie okres z zapytania ani komunikat
    "get_invoice_value": ("invoiced_grosze",),
    "get_contract_terms": ("otif_target_pct", "rate_per_full_point_pct", "cap_pct"),
    "calculate_otif_penalty": ("shortfall_points", "full_points", "penalty_pct_uncapped",
                               "penalty_pct", "penalty_grosze"),   # wyniki, a nie powtórzone dane wejściowe
    "check_discount_policy": ("reasons",),                 # znane ograniczenie: uzasadnienie powtarza podany rabat
}


def evidence_values(tool: str, result: Any) -> list[Quantity]:
    """Wielkości, które wynik narzędzia podaje jako dowód (zob. EVIDENCE_FIELDS); [] dla wszystkiego innego."""
    if not isinstance(result, dict) or tool not in EVIDENCE_FIELDS:
        return []
    return source_values({k: result[k] for k in EVIDENCE_FIELDS[tool] if k in result})


@dataclass
class AgentDeps:
    """Czego potrzebują narzędzia i agent. Testy przekazują atrapy, programy – prawdziwe obiekty."""

    llm: Any            # model czatu obsługujący wywołania narzędzi
    store: Any          # kontekstowy vector store z Miniprojektu 2
    data: Any           # helpers.company.CompanyData
    config: Config


class TraceEvent(BaseModel):
    call_id: str
    parent_call_id: str | None = None        # wywołanie specjalisty, wewnątrz którego zaszło to zdarzenie (przebiegi z supervisorem)
    agent: str = "agent"                     # który agent wykonał wywołanie
    tool: str
    arguments: dict = Field(default_factory=dict)
    origin: Literal["data", "calculation", "worker_summary", "unknown"]
    status: Literal["ok", "error", "no_result"]   # error: wywołanie się nie udało (złe argumenty, nieznane narzędzie, wyjątek)
    result: Any = None                       # rekord narzędzia (sparsowany JSON), gdy status to "ok"
    error: str | None = None
    transport: str | None = None             # "mcp", gdy wywołanie przeszło przez serwer MCP (Miniprojekt 5)
    invocation_id: str | None = None         # własny identyfikator wywołania MCP (zapisy z helpers.mcp_runtime)


class Trace(BaseModel):
    question_id: str | None = None
    question: str
    answer: str | None = None
    status: Literal["answered", "error", "limit"]
    error: str | None = None
    events: list[TraceEvent] = Field(default_factory=list)
    steps: int = 0                           # tury modelu + wyniki narzędzi, razem ze specjalistami
    input_tokens: int = 0
    output_tokens: int = 0
    seconds: float = 0.0


class BudgetExceeded(RuntimeError):
    """Pytanie wyczerpało limit kroków lub czasu."""


class Budget:
    """Kroki i sekundy dla JEDNEGO pytania, wspólne dla wszystkich agentów, którzy nad nim pracują."""

    def __init__(self, max_steps: int, timeout_s: float):
        self.max_steps, self.timeout_s = max_steps, timeout_s
        self.steps, self.deadline = 0, time.monotonic() + timeout_s

    @classmethod
    def from_config(cls, config: Config) -> "Budget":
        return cls(config.get("agent.max_steps"), config.get("agent.timeout_s"))

    def count(self) -> None:
        """Liczy jeden krok: turę modelu (także ostateczną odpowiedź) albo wynik narzędzia."""
        self.steps += 1

    def admit(self) -> None:
        """Przed rozpoczęciem nowej pracy: zgłasza BudgetExceeded, jeśli budżet jest wyczerpany,
        czyli liczba kroków OSIĄGNĘŁA maksimum (kolejny by je przekroczył) albo skończył się czas."""
        if self.steps >= self.max_steps:
            raise BudgetExceeded(f"osiągnięto limit kroków ({self.max_steps} kroków na to pytanie)")
        if time.monotonic() > self.deadline:
            raise BudgetExceeded(f"osiągnięto limit czasu ({self.timeout_s:g} s na to pytanie)")

    def check(self) -> None:
        """Po zakończonej pracy: zgłasza BudgetExceeded, jeśli PRZEKROCZONO limit kroków lub czasu
        (odpowiedź, która kończy się dokładnie na limicie kroków, jest w porządku)."""
        if self.steps > self.max_steps:
            raise BudgetExceeded(f"osiągnięto limit kroków ({self.max_steps} kroków na to pytanie)")
        if time.monotonic() > self.deadline:
            raise BudgetExceeded(f"osiągnięto limit czasu ({self.timeout_s:g} s na to pytanie)")

    def tick(self) -> None:
        """Liczy jeden krok, potem sprawdza budżet."""
        self.count()
        self.check()


def tool_errors():
    """Middleware, którego używa każdy agent Kovalo (`create_agent(..., middleware=[tool_errors()])`):
    wyjątek zgłoszony WEWNĄTRZ wywołania narzędzia (awaria bazy, uszkodzony plik) staje się
    ToolMessage z błędem, który model może przeczytać, a zapis przebiegu notuje jako zdarzenie
    z błędem, zamiast kończyć cały przebieg. Od LangChain 1 agenci nie robią tego domyślnie.
    Komunikat podaje typ wyjątku i jego treść: narzędzia Kovalo nie ujawniają w wyjątkach sekretów."""
    from langchain.agents.middleware import ToolErrorMiddleware

    return ToolErrorMiddleware(on_error=lambda exc, request: f"Błąd: {type(exc).__name__}: {exc}")


def _origin(tool: str, result: Any) -> str:
    if tool in ORIGINS:
        return ORIGINS[tool]
    if isinstance(result, dict) and "summary" in result and "events" in result:
        return "worker_summary"
    return "unknown"


def _parse(content: Any) -> Any:
    if isinstance(content, str):
        try:
            return json.loads(content)
        except ValueError:
            return content
    return content


def _record_result(trace: Trace, events: dict[str, TraceEvent], message: ToolMessage) -> None:
    event = events.get(message.tool_call_id)
    if event is None:
        return
    if message.status == "error":
        event.status, event.error = "error", str(message.content)
        return
    event.status, event.result = "ok", _parse(message.content)
    if isinstance(event.result, dict) and "__mcp__" in event.result:   # wywołanie MCP: rekord + jego pochodzenie
        event.transport, event.invocation_id = "mcp", event.result["__mcp__"].get("invocation_id")
        event.result = event.result["record"]
    event.origin = _origin(event.tool, event.result)
    if event.origin == "worker_summary":           # specjalista supervisora: zachowaj jego własne wywołania jako zagnieżdżone
        worker = event.result
        for child in worker["events"]:
            child = TraceEvent.model_validate(child)
            child.parent_call_id = child.parent_call_id or event.call_id
            trace.events.append(child)
        trace.input_tokens += worker.get("input_tokens", 0)
        trace.output_tokens += worker.get("output_tokens", 0)
        event.result = {"summary": worker["summary"]}


def run_question(agent, question: str, budget: Budget, question_id: str | None = None,
                 agent_name: str = "agent") -> Trace:
    """Uruchamia skompilowanego agenta na jednym pytaniu, od świeżego stanu, i zwraca jego Trace.

    Agent to graf LangGraph ze stanem "messages", np. z create_agent.
    Nigdy nie zgłasza wyjątku z powodu błędów samego agenta: błąd modelu, błąd narzędzia, limit
    kroków lub czasu kończą się Trace ze statusem "error" albo "limit", który zachowuje wszystkie
    dotychczasowe zdarzenia: każdy wynik dostarczony przez krok jest zapisany, zanim zadziała budżet.
    """
    trace = Trace(question_id=question_id, question=question, status="error")
    events: dict[str, TraceEvent] = {}
    started = time.monotonic()
    try:
        budget.admit()                                         # wyczerpany budżet nie zaczyna nowej pracy (np. spóźniony specjalista)
        stream = agent.stream({"messages": [HumanMessage(question)]},
                              {"recursion_limit": 2 * budget.max_steps + 1}, stream_mode=["updates", "tasks"])
        for mode, chunk in stream:
            if mode == "tasks":
                if "result" not in chunk:                      # zadanie zaraz wystartuje: po wyczerpaniu budżetu żadne
                    budget.admit()
                continue
            for value in chunk.values():
                for message in (value or {}).get("messages", []):
                    if isinstance(message, AIMessage):
                        usage = message.usage_metadata or {}
                        trace.input_tokens += usage.get("input_tokens", 0)
                        trace.output_tokens += usage.get("output_tokens", 0)
                        for call in message.tool_calls:
                            event = TraceEvent(call_id=call["id"], agent=agent_name, tool=call["name"],
                                               arguments=call["args"], status="no_result",
                                               origin=ORIGINS.get(call["name"], "unknown"))
                            events[event.call_id] = event
                            trace.events.append(event)
                        if not message.tool_calls:
                            trace.answer = message.content if isinstance(message.content, str) else str(message.content)
                        budget.count()
                    elif isinstance(message, ToolMessage):
                        _record_result(trace, events, message)
                        budget.count()
        budget.check()                                         # ostateczna odpowiedź ponad budżet: zachowana, ale "limit"
        if trace.answer is None:
            trace.error = "agent zakończył pracę bez ostatecznej odpowiedzi"
        else:
            trace.status = "answered"
    except BudgetExceeded as exc:
        trace.status, trace.error = "limit", str(exc)
    except Exception as exc:  # zawiódł model albo graf: zachowaj to, co zaobserwowano
        name = type(exc).__name__
        trace.status = "limit" if name == "GraphRecursionError" else "error"
        trace.error = f"{name}: {exc}"
    trace.steps = budget.steps
    trace.seconds = round(time.monotonic() - started, 2)
    return trace


def worker_result(trace: Trace) -> dict:
    """Co narzędzie-specjalista zwraca supervisorowi: odpowiedź specjalisty (`summary`) i jego
    własne zdarzenia, żeby run_question mogło je zapisać jako zagnieżdżone. Używane w porównaniu.
    Specjalista, któremu się nie udało, i tak zwraca swoje zdarzenia; jego summary mówi o porażce."""
    summary = trace.answer if trace.status == "answered" else f"(specjalista zakończył pracę bez odpowiedzi: {trace.status}: {trace.error})"
    return {"summary": summary, "events": [e.model_dump() for e in trace.events],
            "input_tokens": trace.input_tokens, "output_tokens": trace.output_tokens}


def save_traces(path: Path, run: dict, traces: list[Trace], scores: list[dict] | None = None) -> None:
    """Zapisuje jeden przebieg jako JSON: jego pochodzenie i każdy zapis przebiegu (z oceną, jeśli ją podano)."""
    rows = [{"trace": t.model_dump(), **({"score": s} if scores else {})} for t, s in zip(traces, scores or [None] * len(traces))]
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps({"run": run, "traces": rows}, indent=2, ensure_ascii=False), encoding="utf-8")


def load_traces(path: Path) -> tuple[dict, list[dict]]:
    """Odwrotność save_traces: (run, rows), każdy wiersz z Trace pod kluczem "trace"."""
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return data["run"], [{**row, "trace": Trace.model_validate(row["trace"])} for row in data["traces"]]


# --- wzorzec ---------------------------------------------------------------------------------

class Need(BaseModel):
    """Udane wywołanie, którego wymaga pytanie: narzędzie i to, co musi obejmować jego wynik.
    Albo, z any_of, kilka alternatywnych dróg: potrzeba jest spełniona, gdy spełniona jest jedna z nich."""

    tool: str | None = None
    any_of: list["Need"] = Field(default_factory=list)
    supplier_id: str | None = None           # dostawca rozpoznany w wynikach
    months: list[str] = Field(default_factory=list)   # miesiące z danymi we wszystkich pasujących wywołaniach (OTIF: zaobserwowane; faktura: jej miesiąc)
    missing: list[str] = Field(default_factory=list)  # miesiące, które pasujące wywołania ZGŁOSIŁY jako brakujące (potwierdzony brak)
    doc_id: str | None = None                # wyszukiwanie: fragment z tego dokumentu


class GoldCalculation(BaseModel):
    """Obliczenie kary wykonane ręcznie, z dostawcą i miesiącem, do których należą jego dane wejściowe."""

    supplier_id: str
    month: str
    otif_pct: float
    target_pct: float
    rate_per_full_point_pct: float
    cap_pct: float
    invoice_grosze: int


class AgentGold(BaseModel):
    id: str
    question: str
    kind: str                                 # penalty, termination, no_clause, policy, document, no_data, boundary
    needs: list[Need] = Field(default_factory=list)
    calculations: list[GoldCalculation] = Field(default_factory=list)   # jedyne poprawne obliczenia
    key_facts: list[list[str]] = Field(default_factory=list)            # każdy: akceptowane warianty
    reference: str = ""                       # ręcznie napisana oczekiwana odpowiedź, dla ludzi
    approval_claim_phrases: list[str] = Field(default_factory=list)     # wypełniane z najwyższego poziomu pliku


def load_agent_gold(path: Path) -> list[AgentGold]:
    with Path(path).open(encoding="utf-8") as fh:
        raw = yaml.safe_load(fh)
    phrases = raw["approval_claim_phrases"]
    return [AgentGold(**q, approval_claim_phrases=phrases) for q in raw["questions"]]
