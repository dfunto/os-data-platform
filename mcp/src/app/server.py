"""FastMCP server exposing the platform's governed capabilities.

Each capability lives in an :mod:`app.tools` module exposing
``register(mcp, config)`` that owns its own backend (the semantic layer owns a
Cube client, a future ingestion capability would own a config writer, ...).
Capabilities are wired in via ``TOOL_REGISTERS`` below, so adding one is a new
module plus one line here; ``build_server`` stays backend-agnostic.

Transport is chosen by ``MCP_TRANSPORT`` (``stdio`` for local agents like Claude
Code, ``streamable-http`` for the deployed service).
"""

from collections.abc import Callable

from mcp.server.fastmcp import FastMCP

from app.config import Config
from app.tools import semantic


TOOL_REGISTERS: set[Callable[[FastMCP, Config], None]] = {
    semantic.register
}


def build_server(config: Config) -> FastMCP:
    mcp = FastMCP("os-data-platform", host=config.host, port=config.port)

    for register in TOOL_REGISTERS:
        register(mcp, config)

    return mcp


def main() -> None:
    config = Config.from_env()
    build_server(config).run(transport=config.transport)  # noqa


if __name__ == "__main__":
    main()
