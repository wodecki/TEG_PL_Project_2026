"""KROK 3: Narzędzia, z których może korzystać model, i agent, który z nich korzysta

CEL
    Zamień kroki 1–2 w narzędzia i przekaż je jednemu agentowi. Dla modelu narzędzie TO jego
    nazwa, opis i schemat argumentów: tylko to widzi, gdy decyduje, co wywołać i z jakimi
    argumentami. Potem zbuduj agenta: pętlę, w której model wywołuje narzędzia, czyta ich
    wyniki i wywołuje kolejne, aż odpowie. Model wybiera wywołania, ale każda liczba nadal
    pochodzi z twojego deterministycznego kodu.

WYNIK
        tools = build_tools(deps)
        [t.name for t in tools]
        -> ['search_documents', 'get_supplier_otif', 'get_invoice_value', 'get_contract_terms',
            'calculate_otif_penalty', 'check_discount_policy']          (w dowolnej kolejności)
        tools[1].invoke({"supplier": "SUP-114", "from_month": "2026-07", "to_month": "2026-07"})
        -> {'status': 'ok', 'supplier_id': 'SUP-114', ..., 'observations': [{'month': '2026-07', 'otif_pct': 94.6}], ...}

        agent = build_agent(deps)
        run_question(agent, "Ile wynosi kara, którą Mleczna Dolina jest winna Kovalo za lipiec 2026 r.? "
                            "Podaj kwotę w PLN.", budget)  (gotowa funkcja)
        -> Trace(status='answered', answer='Kara wynosi **7296,00 PLN**. ...', events=[get_contract_terms ..., ...])

WYMAGANIA (sprawdzają je testy)
    build_tools(deps) zwraca dokładnie sześć powyższych narzędzi (helpers.agent_trace.ALLOWED_TOOLS)
    i nic więcej: żadnego, które zatwierdza, zapisuje albo coś obiecuje.
    - Każde narzędzie wywołuje twoją funkcję z kroku 1–2 z zależnością, której ona potrzebuje
      (deps.data, deps.store, deps.config), i zwraca jej rekord jako słownik możliwy do zapisania w formacie JSON
      (record.model_dump(mode="json")). Zależności nigdy nie są argumentami, które wypełnia model.
    - Każde narzędzie ma opis (ang. docstring), który mówi, co zwraca, i podaje format każdego
      argumentu (identyfikator lub nazwa, miesiące YYYY-MM, grosze). Model nie widzi nic więcej.
    - Nazwy argumentów: search_documents(question); get_supplier_otif(supplier, from_month,
      to_month); get_invoice_value(supplier, month); get_contract_terms(supplier);
      calculate_otif_penalty(otif_pct, target_pct, rate_per_full_point_pct, cap_pct,
      invoice_grosze); check_discount_policy(discount_pct, margin_after_pct, clearance,
      strategic_account, competitor_offer, contractual_volume_rebate), z wartościami
      domyślnymi z kroku 2.
    - search_documents używa k = wartość "retrieval.top_k" z konfiguracji.
    build_agent(deps) zwraca skompilowanego agenta (create_agent z LangChaina) z deps.llm,
    build_tools(deps), promptem systemowym z konfiguracji "prompts.agent_system" i gotową warstwą obsługi błędów:
    middleware=[tool_errors()] (helpers/agent_trace.py): wyjątek wewnątrz wywołania narzędzia
    staje się komunikatem o błędzie, który model może przeczytać, zamiast kończyć przebieg.
    Bez pamięci między pytaniami: run_question daje każdemu pytaniu nowy, pusty stan.

ZALECANE NARZĘDZIA
    langchain_core.tools.tool (dekorator @tool odczytuje nazwę funkcji, docstring i adnotacje
    typów); langchain.agents.create_agent. Przykłady: „Przybornik” w mini_project_4/README.md.

NA KONIEC SPRAWDŹ KOD POLECENIEM
    uv run pytest mini_project_4/tests/test_step3_build_agent.py -v
"""

from langchain_core.tools import BaseTool, tool
from langchain.agents import create_agent

from helpers.agent_trace import AgentDeps, tool_errors
from mini_project_4.src import step1_read_company_data as data_tools
from mini_project_4.src import step2_compute_and_search as compute_tools


def build_tools(deps: AgentDeps) -> list[BaseTool]:
    # TODO: twój kod – zobacz CEL, WYNIK i WYMAGANIA na początku pliku
    raise NotImplementedError("TODO: build_tools")


def build_agent(deps: AgentDeps):
    # TODO: twój kod – zobacz CEL, WYNIK i WYMAGANIA na początku pliku
    raise NotImplementedError("TODO: build_agent")
