import anyio


def test_server_registers_the_governed_tools():
    from mcp_server.server import build_server

    server = build_server()
    tools = anyio.run(server.list_tools)
    names = {t.name for t in tools}

    assert {"describe_schema", "query", "preview_sql"} <= names
