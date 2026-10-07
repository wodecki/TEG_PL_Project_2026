"""KROK 1: Narzędzia Kovalo udostępnione przez jeden standardowy interfejs: serwer MCP

CEL
    Udostępnij sześć narzędzi tylko do odczytu z Miniprojektu 4 przez serwer MCP. Wtedy każdy
    klient MCP (nasz asystent, MCP Inspector, Claude Desktop) korzysta z tej samej implementacji.
    Logika biznesowa zostaje w funkcjach Miniprojektu 4: każde narzędzie jest tu tylko CIENKĄ
    nakładką, która zwraca rekord z Miniprojektu 4. Dodaj też dwa pozostałe elementy MCP:
    zasoby (ang. resources), czyli dokumenty odczytywane przez klienta na podstawie URI,
    oraz szablon wiadomości do wielokrotnego użycia (ang. prompt).

WYNIK
    build_server(deps) zwraca serwer FastMCP. Przez dowolnego klienta MCP:

        list_tools()   -> search_documents, get_supplier_otif, get_invoice_value, get_contract_terms,
                          calculate_otif_penalty, check_discount_policy, każde z inputSchema
                          ORAZ outputSchema (z typu rekordu), readOnlyHint=True
        call_tool("get_supplier_otif", {"supplier": "SUP-114", "from_month": "2026-08", "to_month": "2026-10"})
                       -> structuredContent = OtifResult(..., missing_months=['2026-10']) jako JSON
        read_resource("kovalo://documents/CON-103")  -> tekst dokumentu CON-103
        read_resource("kovalo://policy/course-v1")   -> kursowa interpretacja polityki rabatowej (YAML)
        get_prompt("supplier_review", {"supplier": "Mleczna Dolina"}) -> jedna wiadomość użytkownika

WYMAGANIA (sprawdzają je testy)
    - FastMCP("kovalo"). Sześć narzędzi ma dokładnie te nazwy i argumenty co w Miniprojekcie 4
      (zob. mini_project_4/src/step3_build_agent.py). Każde jest oznaczone jako tylko do odczytu
      (annotations={"readOnlyHint": True}) i ma docstring, z którego model może skorzystać.
    - Każde narzędzie zwraca REKORD z twoich funkcji Miniprojektu 4, z klasą rekordu jako adnotacją
      typu zwracanego (np. -> OtifResult). Dzięki temu FastMCP publikuje outputSchema i wysyła
      structuredContent. Nie zwracaj zwykłego słownika dict zamiast rekordu. Zależności pochodzą z `deps` (domknięcie), nigdy
      z argumentów narzędzia. search_documents używa k = wartość "retrieval.top_k" z konfiguracji.
    - Szablon zasobu "kovalo://documents/{doc_id}": tekst dokumentu wyszukanego po DOKŁADNYM
      doc_id w katalogu korpusu (config "paths.corpus_catalog"). Wszystko inne (nieznany
      identyfikator, "CON-10[3]", "../x", "CON-101_x.md") zgłasza ValueError: nigdy wzorzec pliku
      ani ścieżka.
    - Zasób "kovalo://policy/course-v1": yaml.safe_dump z sekcji "policy" konfiguracji.
    - Prompt supplier_review(supplier): jedna wiadomość użytkownika z prośbą o warunki umowy tego
      dostawcy, jego ostatni OTIF i ewentualną należną karę umowną, ze źródłem każdej liczby.
    - Nic nie trafia na stdout: przy stdio stdout przenosi wyłącznie komunikaty protokołu.

ZALECANE NARZĘDZIA
    mcp.server.fastmcp.FastMCP (@server.tool, @server.resource, @server.prompt);
    helpers.catalog.load_catalog. Przykłady: „Przybornik” w mini_project_5/README.md.

NA KONIEC SPRAWDŹ KOD POLECENIEM
    uv run pytest mini_project_5/tests/test_step1_build_server.py -v
"""

import yaml
from mcp.server.fastmcp import FastMCP

from helpers.agent_trace import AgentDeps
from helpers.catalog import load_catalog
from helpers.company import (ContractTermsResult, InvoiceResult, OtifResult, PenaltyCalculation, PolicyCheck,
                             SearchResult)
from mini_project_4.src import step1_read_company_data as data_tools
from mini_project_4.src import step2_compute_and_search as compute_tools


def build_server(deps: AgentDeps) -> FastMCP:
    # TODO: twój kod – zobacz CEL, WYNIK i WYMAGANIA na początku pliku
    raise NotImplementedError("TODO: build_server")
