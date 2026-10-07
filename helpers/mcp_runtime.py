"""Połączenie z serwerem MCP i korzystanie z jego narzędzi w zwykłym (synchronicznym) kodzie.
Gotowy plik: nie edytujesz go.

McpConnection prowadzi jedną sesję klienta MCP w pętli zdarzeń działającej w tle, dzięki czemu
reszta projektu (LangGraph, run_question z Miniprojektu 4) pozostaje synchroniczna. Udostępnia:

  tools()    narzędzia LangChain, które wywołują serwer. Wynik każdego wywołania to SUROWY
             structuredContent serwera, sprawdzony z kanonicznym rekordem z Miniprojektu 4,
             ZANIM cokolwiek uzupełni wartości domyślne; dokładnie to trafia do zapisu przebiegu
             (zob. helpers.agent_trace).
  captures   każde wywołanie tak, jak przebiegło: identyfikator wywołania, wątek i tura, narzędzie,
             argumenty, surowy structuredContent, jego tekstowa kopia, isError i wynik.
  close()    zamknięcie z limitem czasu: SDK zamyka stdin serwera, czeka, a następnie kończy
             drzewo procesów, w razie potrzeby wymuszając jego zakończenie; połączenie, w którym minął limit czasu, nigdy nie jest używane ponownie.

Cztery warstwy błędów są rozdzielone i nazwane w każdym komunikacie:
  [błąd narzędzia]         serwer odpowiedział z isError=true (złe argumenty, wyjątek w narzędziu)
  [błąd protokołu]         serwer odpowiedział obiektem błędu JSON-RPC
  [błąd transportu]        brak jakiejkolwiek odpowiedzi: serwer się zakończył, potok się zerwał,
                           minął limit czasu wywołania
  [błąd walidacji lokalnej] odpowiedź nadeszła, ale jest niezgodna z kanonicznym kontraktem (zgodność sprawdza ten moduł)
Zwykły wynik dziedzinowy ("no_data", "not_applicable", ...) nie jest żadnym z nich: to wynik.
"""

from __future__ import annotations

import asyncio
import concurrent.futures
import json
import sys
import threading
import uuid
from contextlib import AbstractAsyncContextManager, asynccontextmanager
from pathlib import Path
from typing import Any, Callable

from langchain_core.tools import StructuredTool, ToolException
from pydantic import BaseModel, ValidationError

from helpers.company import (ContractTermsResult, InvoiceResult, OtifResult, PenaltyCalculation, PolicyCheck,
                             SearchResult)
from helpers.config import Config, ConfigError

# Kanoniczny kontrakt: rekord, który musi zwrócić każde narzędzie (Miniprojekt 4). O poprawności
# rozstrzyga TA tabela, nigdy schemat ogłaszany przez testowany serwer.
CANONICAL: dict[str, type[BaseModel]] = {
    "search_documents": SearchResult,
    "get_supplier_otif": OtifResult,
    "get_invoice_value": InvoiceResult,
    "get_contract_terms": ContractTermsResult,
    "calculate_otif_penalty": PenaltyCalculation,
    "check_discount_policy": PolicyCheck,
}
# Pola, które nie mogą być null dla danej pary (narzędzie, status).
STATUS_RULES: dict[tuple[str, str], tuple[str, ...]] = {
    ("get_supplier_otif", "ok"): ("supplier_id",),
    ("get_invoice_value", "ok"): ("supplier_id", "invoiced_grosze"),
    ("get_contract_terms", "ok"): ("supplier_id", "source_doc_id", "otif_target_pct", "penalty_clause", "terms_version"),
    ("calculate_otif_penalty", "ok"): ("shortfall_points", "full_points", "penalty_pct_uncapped", "penalty_pct",
                                       "penalty_grosze"),
    ("check_discount_policy", "ok"): ("version",),
}
# Pola, które dla danej pary (narzędzie, status) muszą mieć jedną konkretną wartość: kwoty to całkowite grosze PLN.
STATUS_VALUES: dict[tuple[str, str], dict[str, Any]] = {
    ("get_invoice_value", "ok"): {"currency": "PLN"},
    ("calculate_otif_penalty", "ok"): {"currency": "PLN"},
}


# Zamykanie stdio w przypiętej wersji SDK: zamknij stdin, czekaj do 2 s, zakończ drzewo procesów,
# po kolejnych 2 s je zabij. Krótszy limit sprzątania zatrzymałby pętlę, zanim proces potomny zniknie.
MIN_STDIO_CLEANUP_S = 5.0


class McpCallError(ToolException):
    """Nieudane wywołanie MCP; `layer` to "tool", "protocol", "transport" albo "validation"."""

    def __init__(self, layer: str, message: str, invocation_id: str | None = None):
        names = {"tool": "błąd narzędzia", "protocol": "błąd protokołu", "transport": "błąd transportu",
                 "validation": "błąd walidacji lokalnej"}
        self.layer, self.invocation_id = layer, invocation_id
        suffix = f" (wywołanie {invocation_id})" if invocation_id else ""
        super().__init__(f"[{names[layer]}] {message}{suffix}")


class McpStartupError(ConfigError):
    """Nie udało się uruchomić serwera albo nie zakończył inicjalizacji na czas."""


def _leaf(exc: BaseException) -> BaseException:
    """Pierwszy prawdziwy wyjątek wewnątrz (zagnieżdżonych) grup wyjątków: grupy zadań anyio opakowują błędy."""
    while isinstance(exc, BaseExceptionGroup) and exc.exceptions:
        exc = exc.exceptions[0]
    return exc


def _missing_and_extra(model: type[BaseModel], raw: Any, path: str = "") -> list[str]:
    """Problemy z kontraktem w surowych danych: brakujące pola kanonicznego rekordu i pola, których
    rekord nie ma. Zagnieżdżone rekordy (listy modeli) są sprawdzane element po elemencie."""
    if not isinstance(raw, dict):
        return [f"{path or 'result'}: expected an object, got {type(raw).__name__}"]
    problems = [f"{path}{name}: brak" for name in model.model_fields if name not in raw]
    problems += [f"{path}{name}: spoza kontraktu" for name in raw if name not in model.model_fields]
    for name, field in model.model_fields.items():
        inner = getattr(field.annotation, "__args__", ())
        if name in raw and isinstance(raw[name], list) and inner and isinstance(inner[0], type) \
                and issubclass(inner[0], BaseModel):
            for i, item in enumerate(raw[name]):
                problems += _missing_and_extra(inner[0], item, f"{path}{name}[{i}].")
    return problems


def check_record(tool: str, structured: Any, text: list[str]) -> dict:
    """Wiążący rekord udanego wywołania albo McpCallError("validation").
    Kolejność: rekord w ogóle jest -> KAŻDY blok tekstu to równa mu kopia JSON (dodatkowy lub inny
    blok jest odrzucany, nigdy pomijany) -> są wszystkie pola kanoniczne i żadne inne (zanim
    jakakolwiek wartość domyślna mogłaby je uzupełnić) -> ścisłe typy (żadnego bool ani "123"
    zamiast liczby) -> reguły statusu (pola różne od null, konkretne wartości, np. waluta PLN).
    Zwraca surowe dane bez zmian, więc null i brak pola dalej da się rozróżnić."""
    model = CANONICAL.get(tool)
    if model is None:
        raise McpCallError("validation", f"{tool}: brak kanonicznego kontraktu dla tego narzędzia")
    if structured is None:
        raise McpCallError("validation", f"{tool}: wynik nie ma structuredContent")
    for block in text:
        try:
            mirror = json.loads(block)
        except ValueError:
            raise McpCallError("validation", f"{tool}: blok tekstu nie jest kopią JSON structuredContent") from None
        if mirror != structured:
            raise McpCallError("validation", f"{tool}: treść tekstowa i structuredContent się nie zgadzają")
    problems = _missing_and_extra(model, structured)
    if problems:
        raise McpCallError("validation", f"{tool}: " + "; ".join(problems[:6]))
    try:
        model.model_validate_json(json.dumps(structured), strict=True)
    except ValidationError as exc:
        first = exc.errors()[0]
        raise McpCallError("validation", f"{tool}: {'.'.join(map(str, first['loc']))}: {first['msg']}") from None
    for name in STATUS_RULES.get((tool, structured.get("status")), ()):
        if structured.get(name) is None:
            raise McpCallError("validation", f"{tool}: {name} nie może być null, gdy status to {structured['status']!r}")
    for name, value in STATUS_VALUES.get((tool, structured.get("status")), {}).items():
        if structured.get(name) != value:
            raise McpCallError("validation", f"{tool}: {name} musi mieć wartość {value!r}, gdy status to {structured['status']!r}, "
                                             f"otrzymano {structured.get(name)!r}")
    return structured


class McpConnection:
    """Jedna sesja klienta MCP prowadzona przez pętlę zdarzeń w tle. Używaj jej jako menedżera kontekstu.

    open_session: fabryka asynchronicznych menedżerów kontekstu, która daje ClientSession, zainicjowaną
    lub nie (stdio: zob. connect_kovalo; testy: sesja w pamięci). Limity czasu pochodzą z sekcji "mcp" konfiguracji.
    """

    def __init__(self, open_session: Callable[[], AbstractAsyncContextManager], *, startup_timeout_s: float,
                 call_timeout_s: float, cleanup_timeout_s: float, server_name: str = "kovalo",
                 stderr_tail: Callable[[], str] | None = None):
        self.call_timeout_s, self.cleanup_timeout_s = call_timeout_s, cleanup_timeout_s
        self.server_name, self.captures, self.context = server_name, [], {"thread_id": None, "turn": None}
        self.unusable: str | None = None
        self._stderr_tail = stderr_tail or (lambda: "")
        self._closed = False
        self.turn_lock = threading.Lock()           # jedna tura asystenta naraz (helpers.assistant.assistant_turn)
        self._pending: set[concurrent.futures.Future] = set()
        self._loop = asyncio.new_event_loop()
        self._thread = threading.Thread(target=self._loop.run_forever, name="mcp-connection", daemon=True)
        self._thread.start()
        self._stop: asyncio.Event | None = None
        self._task: asyncio.Task | None = None
        try:
            ready = asyncio.run_coroutine_threadsafe(self._start(open_session, startup_timeout_s), self._loop)
            self._tools_info = ready.result(timeout=startup_timeout_s + cleanup_timeout_s + 10)
        except BaseException as exc:
            self.close()
            if isinstance(exc, McpStartupError):
                raise
            tail = self._stderr_tail()
            raise McpStartupError(f"serwer MCP się nie uruchomił: {type(exc).__name__}: {exc}"
                                  + (f"\nstderr serwera (ostatnie wiersze):\n{tail}" if tail else "")) from None

    async def _start(self, open_session, startup_timeout_s: float):
        self._stop = asyncio.Event()
        ready: asyncio.Future = asyncio.get_running_loop().create_future()

        async def hold():
            try:
                async with open_session() as session:
                    try:
                        await asyncio.wait_for(session.initialize(), startup_timeout_s)
                    except asyncio.TimeoutError:
                        raise McpStartupError(f"serwer MCP nie dokończył inicjalizacji w ciągu "
                                              f"{startup_timeout_s:g} s (config mcp.startup_timeout_s)") from None
                    self.session = session
                    listed = await asyncio.wait_for(session.list_tools(), startup_timeout_s)
                    ready.set_result(listed.tools)
                    await self._stop.wait()
            except BaseException as exc:          # błąd startu: zgłoś go od razu, nigdy nie czekaj na limit czasu
                if not ready.done():
                    leaf = _leaf(exc)
                    ready.set_exception(leaf if isinstance(leaf, Exception) else RuntimeError(str(leaf)))
                if not isinstance(exc, (Exception, asyncio.CancelledError)):
                    raise

        self._task = asyncio.create_task(hold())
        return await ready

    # --- wywołania ---------------------------------------------------------------------------------

    def call(self, tool: str, arguments: dict) -> dict:
        """Wywołuje narzędzie i zwraca jego wiążący rekord (zob. check_record) albo zgłasza McpCallError."""
        invocation_id = uuid.uuid4().hex[:12]
        identity = dict(self.context)                # ustalone teraz: koperta niżej używa tej wartości, nigdy nie czyta jej ponownie
        capture = {"invocation_id": invocation_id, **identity, "tool": tool, "arguments": arguments,
                   "server": self.server_name, "structured": None, "text": None, "is_error": None, "outcome": None}
        self.captures.append(capture)
        if self._closed or self.unusable:
            capture["outcome"] = "transport"
            raise McpCallError("transport", f"połączenie nie nadaje się do użycia: {self.unusable or 'zamknięte'}", invocation_id)
        future = asyncio.run_coroutine_threadsafe(self._call(tool, arguments), self._loop)
        self._pending.add(future)
        try:
            result = future.result(timeout=self.call_timeout_s + self.cleanup_timeout_s + 5)
        except (concurrent.futures.CancelledError, asyncio.CancelledError):   # close(), gdy wywołanie czekało na odpowiedź
            capture["outcome"] = "transport"
            raise McpCallError("transport", f"{tool}: połączenie zamknięto, gdy wywołanie czekało na odpowiedź",
                               invocation_id) from None
        except asyncio.TimeoutError:              # wywołanie zostało anulowane i dokończone w pętli (wait_for)
            self.unusable = f"wywołanie {tool} przekroczyło limit czasu {self.call_timeout_s:g} s"
            capture["outcome"] = "transport"
            raise McpCallError("transport", self.unusable + " (config mcp.call_timeout_s); połącz się ponownie", invocation_id) from None
        except Exception as exc:
            exc = _leaf(exc)
            from mcp.shared.exceptions import McpError
            from mcp.types import CONNECTION_CLOSED

            # SDK samo zgłasza zamknięty potok jako McpError(CONNECTION_CLOSED): nic nie odebrano
            if isinstance(exc, McpError) and exc.error.code != CONNECTION_CLOSED:
                capture["outcome"] = "protocol"
                raise McpCallError("protocol", f"{tool}: {exc.error.message} (kod {exc.error.code})", invocation_id) from None
            self.unusable = f"{type(exc).__name__}: {exc}"
            capture["outcome"] = "transport"
            raise McpCallError("transport", f"{tool}: serwer nie odpowiedział ({self.unusable})", invocation_id) from None
        finally:
            self._pending.discard(future)
        text = [c.text for c in result.content if getattr(c, "type", None) == "text"]
        capture.update(structured=result.structuredContent, text=text, is_error=bool(result.isError))
        if result.isError:
            capture["outcome"] = "tool"
            raise McpCallError("tool", f"{tool}: {' '.join(text)[:300]}", invocation_id)
        try:
            record = check_record(tool, result.structuredContent, text)
        except McpCallError as exc:
            capture["outcome"] = "validation"
            raise McpCallError("validation", str(exc).removeprefix("[błąd walidacji lokalnej] "), invocation_id) from None
        capture["outcome"] = "ok"
        return {"__mcp__": {"invocation_id": invocation_id, "server": self.server_name, **identity},
                "record": record}

    async def _call(self, tool: str, arguments: dict):
        return await asyncio.wait_for(self.session.call_tool(tool, arguments), self.call_timeout_s)

    def run(self, coro_factory: Callable[[Any], Any], timeout: float | None = None):
        """Uruchamia session.<coś> w pętli, np. conn.run(lambda s: s.list_resources())."""
        if self._closed or self.unusable:
            raise McpCallError("transport", f"połączenie nie nadaje się do użycia: {self.unusable or 'zamknięte'}")
        future = asyncio.run_coroutine_threadsafe(asyncio.wait_for(coro_factory(self.session), timeout or self.call_timeout_s),
                                                  self._loop)
        return future.result(timeout=(timeout or self.call_timeout_s) + self.cleanup_timeout_s + 5)

    def tools(self) -> list[StructuredTool]:
        """Narzędzia serwera jako narzędzia LangChain (synchroniczne). Każde zwraca {"__mcp__": {...}, "record": {...}}:
        run_question z Miniprojektu 4 zapisuje record jako wynik, a resztę jako pochodzenie."""
        def make(info) -> StructuredTool:
            def run(**kwargs) -> dict:
                return self.call(info.name, kwargs)
            # handle_tool_error: samo narzędzie zamienia McpCallError (ToolException) na ToolMessage
            # z błędem, który model może przeczytać; węzeł narzędzi w LangGraph 1 nie łapie już za nas wyjątków
            return StructuredTool.from_function(func=run, name=info.name, description=info.description or info.name,
                                                args_schema=info.inputSchema, handle_tool_error=True)
        return [make(info) for info in self._tools_info]

    # --- cykl życia ------------------------------------------------------------------------------

    def close(self) -> None:
        """Z limitem czasu i idempotentne: prosi sesję o zakończenie (SDK zamyka stdin, czeka, potem
        kończy i zabija drzewo procesów serwera), anuluje ją, jeśli się nie skończy, zatrzymuje pętlę."""
        if self._closed:
            return
        self._closed = True
        for future in list(self._pending):          # zwolnij każdego, kto wciąż czeka na odpowiedź
            future.cancel()
        if self._task is not None:
            self._loop.call_soon_threadsafe(self._stop.set)
            done = asyncio.run_coroutine_threadsafe(asyncio.wait({self._task}, timeout=self.cleanup_timeout_s), self._loop)
            try:
                done.result(timeout=self.cleanup_timeout_s + 5)
            except Exception:
                pass
            if not self._task.done():             # łagodne zamknięcie się nie skończyło: anuluj; sprzątanie SDK
                self._loop.call_soon_threadsafe(self._task.cancel)   # nadal działa w pętli (terminate, kill)
                waited = asyncio.run_coroutine_threadsafe(asyncio.wait({self._task}, timeout=self.cleanup_timeout_s),
                                                          self._loop)
                try:
                    waited.result(timeout=self.cleanup_timeout_s + 5)
                except Exception:
                    pass
            if not self._task.done():
                print(f"ostrzeżenie: sesja MCP nie zakończyła zamykania w ciągu {2 * self.cleanup_timeout_s:g} s",
                      file=sys.stderr)
        self._loop.call_soon_threadsafe(self._loop.stop)
        self._thread.join(timeout=self.cleanup_timeout_s + 5)

    def __enter__(self) -> "McpConnection":
        return self

    def __exit__(self, *exc) -> None:
        self.close()

    @property
    def alive(self) -> bool:
        """True, dopóki działa wątek pętli w tle."""
        return self._thread.is_alive()


def stdio_connection(args: list[str], cwd: Path, *, startup_timeout_s: float, call_timeout_s: float,
                     cleanup_timeout_s: float, server_name: str = "kovalo", env: dict | None = None) -> McpConnection:
    """Uruchamia `python <args...>` (tym interpreterem) jako serwer MCP przez stdio i łączy się z nim."""
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import get_default_environment, stdio_client

    if cleanup_timeout_s < MIN_STDIO_CLEANUP_S:
        raise ConfigError(f"mcp.cleanup_timeout_s musi wynosić co najmniej {MIN_STDIO_CLEANUP_S:g} s dla serwera stdio "
                          f"(jest {cleanup_timeout_s:g}): zamykanie w samym SDK może trwać do 4 s "
                          f"(2 s na łagodne zakończenie, potem terminate, a po kolejnych 2 s kill)")
    params = StdioServerParameters(command=sys.executable, args=[str(a) for a in args], cwd=str(cwd),
                                   env=env if env is not None else get_default_environment())
    errlog = _StderrTail()

    @asynccontextmanager
    async def open_session():
        async with stdio_client(params, errlog=errlog) as (read, write):
            async with ClientSession(read, write) as session:
                yield session

    return McpConnection(open_session, startup_timeout_s=startup_timeout_s, call_timeout_s=call_timeout_s,
                         cleanup_timeout_s=cleanup_timeout_s, server_name=server_name, stderr_tail=errlog.tail)


def connect_kovalo(config: Config, server: Path | None = None) -> McpConnection:
    """Uruchamia serwer MCP Kovalo (mini_project_5/src/serve.py) przez stdio i łączy się z nim.
    Jawne ścieżki interpretera, skryptu i konfiguracji: działa z dowolnego folderu i ze spacjami w ścieżkach.
    Serwer sam czyta swoje dane uwierzytelniające z .env projektu (klient żadnych nie przekazuje)."""
    script = Path(server) if server else config.root / "mini_project_5" / "src" / "serve.py"
    return stdio_connection([script, "--config", config.root / "config.yaml"], config.root,
                            startup_timeout_s=config.get("mcp.startup_timeout_s"),
                            call_timeout_s=config.get("mcp.call_timeout_s"),
                            cleanup_timeout_s=config.get("mcp.cleanup_timeout_s"))


def in_memory_connection(server, *, startup_timeout_s: float = 10, call_timeout_s: float = 10,
                         cleanup_timeout_s: float = 5) -> McpConnection:
    """Łączy się z obiektem serwera FastMCP w tym procesie (bez podprocesu): do szybkich testów offline."""
    import anyio
    from mcp import ClientSession
    from mcp.shared.memory import create_client_server_memory_streams

    low = server._mcp_server

    @asynccontextmanager
    async def open_session():
        async with create_client_server_memory_streams() as (client_streams, server_streams):
            async with anyio.create_task_group() as group:
                group.start_soon(lambda: low.run(server_streams[0], server_streams[1],
                                                 low.create_initialization_options(), raise_exceptions=False))
                try:
                    async with ClientSession(*client_streams) as session:
                        yield session
                finally:
                    group.cancel_scope.cancel()

    return McpConnection(open_session, startup_timeout_s=startup_timeout_s, call_timeout_s=call_timeout_s,
                         cleanup_timeout_s=cleanup_timeout_s, server_name=getattr(server, "name", "kovalo"))


class _StderrTail:
    """Plikopodobne ujście stderr procesu serwera, które zachowuje ostatnie wiersze (do komunikatów o błędach)."""

    def __init__(self, lines: int = 15):
        import tempfile

        self._file = tempfile.TemporaryFile(mode="w+", encoding="utf-8")
        self._lines = lines

    def fileno(self):
        return self._file.fileno()

    def write(self, text):
        return self._file.write(text)

    def flush(self):
        self._file.flush()

    def tail(self) -> str:
        try:
            self._file.flush()
            self._file.seek(0)
            return "\n".join(self._file.read().splitlines()[-self._lines:])
        except Exception:
            return ""
