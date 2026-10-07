"""KROK 3: Węzeł, który odpowiada za pomocą narzędzi przez MCP

CEL
    Copilot z Miniprojektu 3 odpowiada na pytania o dokumenty za pomocą systemu RAG z Miniprojektu 2.
    W końcowym asystencie odpowiedzi generuje agent z Miniprojektu 4, korzystający z narzędzi serwera
    MCP. Napisz ten węzeł: jedną funkcję stanu rozmowy, żeby krok 4 mógł wstawić go do grafu
    z Miniprojektu 3 w miejsce odpowiedzi na podstawie dokumentów.

WYNIK
    node = answer_with_tools(deps, tools)       # tools: connection.tools() (helpers/mcp_runtime.py)
    node(state), gdzie state["turn"].standalone ==
        "Ile wynosi kara, którą Mleczna Dolina jest winna Kovalo za lipiec 2026 r.? Podaj kwotę w PLN."
    -> {"status": "answered",
        "messages": [AIMessage("Kara wynosi **7296,00 PLN**. Podstawa: umowa **CON-101** ...")],
        "record": {"kind": "agent_trace", "version": 1, "trace": {... każde wywołanie MCP, transport "mcp" ...}}}

WYMAGANIA (sprawdzają je testy)
    - Agent: create_agent z LangChaina z deps.llm, middleware=[tool_errors()] (jak
      w Miniprojekcie 4), dokładnie podanymi `tools` (narzędziami MCP; nigdy bezpośrednimi
      funkcjami z Miniprojektu 4) i promptem systemowym z konfiguracji "prompts.agent_system".
      Agenta budujesz raz, nie przy każdym wywołaniu.
    - Węzeł uruchamia go funkcją run_question z Miniprojektu 4 na state["turn"].standalone
      (pytaniu przeredagowanym już tak, żeby było zrozumiałe bez kontekstu), z nowym
      Budget.from_config(deps.config) w każdej turze.
    - Zwraca słownik z kluczami:
      - "record": agent_trace_envelope(trace) (helpers/assistant.py), żeby zapis przebiegu (ang. trace)
        przetrwał w stanie rozmowy, niezależnie od wyniku tury;
      - "status": "answered", jeśli status zapisu przebiegu to "answered", w przeciwnym razie
        "error" (koperta zachowuje własny status zapisu: "limit" albo "error");
      - "error": None albo błąd z zapisu przebiegu;
      - "messages": JEDNA AIMessage: odpowiedź agenta, a jeśli jej nie ma, krótkie przeprosiny
        z błędem z zapisu przebiegu.
    - LLM wywołuje tylko przez agenta i nigdy nie prosi o akceptację: akceptacje należą do węzłów
      z Miniprojektu 3.

ZALECANE NARZĘDZIA
    langchain.agents.create_agent; helpers.agent_trace (Budget, run_question);
    helpers.assistant.agent_trace_envelope. Przykłady: „Przybornik” w mini_project_5/README.md.

NA KONIEC SPRAWDŹ KOD POLECENIEM
    uv run pytest mini_project_5/tests/test_step3_answer_with_tools.py -v
"""

from langchain_core.messages import AIMessage
from langchain.agents import create_agent

from helpers.agent_trace import AgentDeps, Budget, run_question, tool_errors
from helpers.assistant import agent_trace_envelope


def answer_with_tools(deps: AgentDeps, tools: list):
    # TODO: twój kod – zobacz CEL, WYNIK i WYMAGANIA na początku pliku
    raise NotImplementedError("TODO: answer_with_tools")
