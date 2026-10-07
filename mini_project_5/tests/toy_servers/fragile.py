"""Prawdziwy serwer FastMCP, którego narzędzia powodują awarię procesu albo się zawieszają."""
import asyncio, os, sys
open(sys.argv[1], "w").write(str(os.getpid()))
from mcp.server.fastmcp import FastMCP
server = FastMCP("fragile", log_level="WARNING")

@server.tool()
def crash() -> str:
    """Zabija proces serwera."""
    os._exit(9)

@server.tool()
async def hang() -> str:
    """Nigdy nie kończy na czas."""
    await asyncio.sleep(600)
    return "late"

@server.tool()
def ping() -> str:
    """Odpowiada."""
    return "pong"

server.run("stdio")
