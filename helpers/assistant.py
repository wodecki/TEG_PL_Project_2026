"""Konfiguracja końcowego asystenta (Miniprojekt 5). Gotowy plik: nie edytujesz go.

Asystent TO graf copilota z Miniprojektu 3 z podmienionym działaniem jednego węzła: węzeł
odpowiadający na pytania o dokumenty staje się agentem, który używa narzędzi serwera MCP Kovalo.
Cała reszta (jednokrotne zrozumienie każdej wiadomości, wniosek i jego kolejne wersje,
doprecyzowanie, pauzy na akceptację, statusy) zostaje dokładnie taka jak w Miniprojekcie 3.

  replace_node(compiled, name, fn, checkpointer)   podmienia jeden węzeł i kompiluje graf od nowa
  assistant_config(config)                         głęboka kopia z promptem rozumienia z MP5
  assistant_turn(assistant, thread_id, text, ...)  JEDYNY publiczny punkt wejścia: używają go czat,
                                                   ewaluacja i testy (zachowuje ochronę pauz)
  agent_trace_envelope(trace) / trace_from_record  jak zapis przebiegu agenta jest przechowywany w stanie

replace_node korzysta z wewnętrznych struktur LangGraph (`compiled.builder`, `StateNodeSpec`). Funkcję sprawdzono
z LangGraph 1.x. Weryfikuje ona wymagane struktury, więc niezgodna aktualizacja spowoduje
zgłoszenie jednoznacznego błędu w tym miejscu.
"""

from __future__ import annotations

import copy
import dataclasses
from importlib.metadata import version

from langchain_core.runnables import RunnableLambda

from helpers.agent_trace import Trace
from helpers.config import Config
from helpers.workflow import run_turn

ENVELOPE_KIND, ENVELOPE_VERSION = "agent_trace", 1


def replace_node(compiled, name: str, fn, checkpointer):
    """Nowy skompilowany graf: te same węzły, krawędzie, trasy i stan co `compiled`, tyle że węzeł
    `name` uruchamia teraz `fn(state) -> dict`. Oryginalny graf się nie zmienia."""
    if not version("langgraph").startswith("1."):
        raise RuntimeError(f"replace_node napisano dla LangGraph 1.x (znaleziono {version('langgraph')}): "
                           "sprawdź je ponownie przed aktualizacją")
    builder = getattr(compiled, "builder", None)
    if builder is None or not hasattr(builder, "nodes") or name not in builder.nodes:
        raise RuntimeError(f"nie można podmienić węzła {name!r}: skompilowany graf nie ma takiego węzła w builderze")
    spec = builder.nodes[name]
    if not dataclasses.is_dataclass(spec) or "runnable" not in {f.name for f in dataclasses.fields(spec)}:
        raise RuntimeError("zmieniła się specyfikacja węzła w LangGraph: trzeba zaktualizować replace_node")
    new_builder = copy.copy(builder)
    new_builder.nodes = dict(builder.nodes)
    new_builder.nodes[name] = dataclasses.replace(spec, runnable=RunnableLambda(fn, name=name))
    return new_builder.compile(checkpointer=checkpointer)


def assistant_config(config: Config) -> Config:
    """Głęboka kopia konfiguracji, w której rozumienie wiadomości z MP3 używa promptu z MP5
    (prompts.assistant_understand_system). Oryginalna konfiguracja się nie zmienia."""
    raw = copy.deepcopy(config.raw)
    raw["prompts"]["understand_system"] = raw["prompts"]["assistant_understand_system"]
    return Config(root=config.root, raw=raw)


def agent_trace_envelope(trace: Trace) -> dict:
    """Jak podmieniony węzeł zapisuje przebieg agenta w kanale `record` z MP3 (dla każdej tury)."""
    return {"kind": ENVELOPE_KIND, "version": ENVELOPE_VERSION, "trace": trace.model_dump(mode="json")}


def trace_from_record(record: dict | None) -> Trace | None:
    """Zapis przebiegu agenta z `record` danej tury albo None (tura o politykę, akceptację lub inna go nie ma)."""
    if isinstance(record, dict) and record.get("kind") == ENVELOPE_KIND:
        if record.get("version") != ENVELOPE_VERSION:
            raise ValueError(f"nieznana wersja koperty agent_trace: {record.get('version')!r}")
        return Trace.model_validate(record["trace"])
    return None


def assistant_turn(assistant, thread_id: str, text: str, answer_pause, connection=None, turn: int | None = None) -> dict:
    """Jedna wiadomość użytkownika przez asystenta: run_turn z MP3 (wątek na pauzie odrzuca nową
    wiadomość; na każdą pauzę odpowiada answer_pause; nieudana odpowiedź anuluje pauzę i zachowuje
    to, co zaobserwowano), a połączenie MCP wie, do którego wątku i tury należą jego wywołania.
    Zwraca wpis transkryptu z run_turn; entry["record"] zawiera kopertę z zapisem przebiegu agenta,
    jeśli taki jest. Jedna tura naraz na połączenie: nakładająca się tura na tym samym połączeniu
    zgłasza RuntimeError, więc wątek i tura każdego zapisu to te, które wykonały wywołanie."""
    if connection is None:
        return run_turn(assistant, thread_id, text, answer_pause)
    if not connection.turn_lock.acquire(blocking=False):   # jedna tura naraz na połączenie (klient dydaktyczny)
        raise RuntimeError("tego połączenia MCP używa już inna tura asystenta: jedna tura naraz na połączenie "
                           "(dla równoległych rozmów otwórz osobne połączenia)")
    try:
        connection.context = {"thread_id": thread_id, "turn": turn}
        return run_turn(assistant, thread_id, text, answer_pause)
    finally:
        connection.context = {"thread_id": None, "turn": None}
        connection.turn_lock.release()
