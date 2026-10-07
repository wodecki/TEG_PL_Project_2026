"""Miniprojekt 5: co oferuje serwer MCP Kovalo, tak jak widzi to dowolny klient MCP. Gotowy program –
uruchom go z katalogu głównego repozytorium:

    uv run python mini_project_5/src/show_mcp.py
    uv run python mini_project_5/src/show_mcp.py --call get_supplier_otif '{"supplier": "SUP-114", "from_month": "2026-08", "to_month": "2026-10"}'

Uruchamia serwer przez stdio i wypisuje jego trzy rodzaje elementów: narzędzia (ze schematami
wejścia i wyjścia), zasoby i szablony zasobów oraz prompty. Czyta jeden zasób i generuje treść
promptu. Z opcją --call wywołuje jedno narzędzie i wypisuje surowe structuredContent. Bez LLM-a;
bez klucza API, chyba że wywołasz search_documents.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from helpers.config import ConfigError, load_config
from helpers.mcp_runtime import McpCallError, connect_kovalo

ROOT = Path(__file__).resolve().parents[2]


def main() -> None:
    parser = argparse.ArgumentParser(description="Lista narzędzi, zasobów i promptów serwera MCP Kovalo.")
    parser.add_argument("--call", nargs=2, metavar=("TOOL", "JSON_ARGUMENTS"), help="wywołaj jedno narzędzie")
    args = parser.parse_args()
    config = load_config(ROOT / "config.yaml")
    with connect_kovalo(config) as conn:
        print("NARZĘDZIA (model decyduje, kiedy je wywołać)")
        for tool in conn.run(lambda s: s.list_tools()).tools:
            ins = ", ".join(tool.inputSchema.get("properties", {}))
            outs = ", ".join((tool.outputSchema or {}).get("properties", {}))
            ro = "tylko odczyt" if tool.annotations and tool.annotations.readOnlyHint else "MOŻE ZAPISYWAĆ"
            print(f"  {tool.name}({ins})  [{ro}]\n      -> {outs}")
        print("\nZASOBY (aplikacja decyduje, co przeczytać)")
        for res in conn.run(lambda s: s.list_resources()).resources:
            print(f"  {res.uri}  {res.mimeType or ''}")
        for tmpl in conn.run(lambda s: s.list_resource_templates()).resourceTemplates:
            print(f"  {tmpl.uriTemplate}  (szablon)  {tmpl.description or ''}")
        doc = conn.run(lambda s: s.read_resource("kovalo://documents/CON-103")).contents[0].text
        print(f"\n  read kovalo://documents/CON-103 -> {doc.splitlines()[0]} (znaki: {len(doc)})")
        print("\nPROMPTY (wybiera je użytkownik)")
        for prompt in conn.run(lambda s: s.list_prompts()).prompts:
            print(f"  {prompt.name}({', '.join(a.name for a in prompt.arguments or [])})")
        rendered = conn.run(lambda s: s.get_prompt("supplier_review", {"supplier": "Mleczna Dolina"}))
        print(f"  supplier_review('Mleczna Dolina') -> {rendered.messages[0].content.text[:110]}...")
        if args.call:
            try:
                result = conn.call(args.call[0], json.loads(args.call[1]))
                print(f"\nWYWOŁANIE {args.call[0]} -> invocation_id {result['__mcp__']['invocation_id']}")
                print(json.dumps(result["record"], indent=2, ensure_ascii=False))
            except McpCallError as exc:
                print(f"\nWYWOŁANIE {args.call[0]} nie powiodło się: {exc}")


if __name__ == "__main__":
    try:
        main()
    except ConfigError as exc:
        sys.exit(f"{exc}\n(zob. „Jeśli utkniesz” w mini_project_5/README.md)")
