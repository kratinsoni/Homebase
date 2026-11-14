import os
import sys
from contextlib import AsyncExitStack

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

DEFAULT_SERVERS = {
    "files": StdioServerParameters(
        command=sys.executable,
        args=["-m", "worker.tools.mcp_servers.files_server"],
        env=dict(os.environ),
    ),
}


class MCPManager:
    def __init__(self, servers: dict[str, StdioServerParameters]):
        self.servers = servers
        self.stack = AsyncExitStack()
        self.sessions: dict[str, ClientSession] = {}
        self.tool_owner: dict[str, str] = {}  # tool name -> server name
        self.schemas: list[dict] = []

    async def start(self):
        for name, params in self.servers.items():
            read, write = await self.stack.enter_async_context(stdio_client(params))
            session = await self.stack.enter_async_context(ClientSession(read, write))
            await session.initialize()
            listing = await session.list_tools()
            for tool in listing.tools:
                self.tool_owner[tool.name] = name
                self.schemas.append({
                    "type": "function",
                    "function": {
                        "name": tool.name,
                        "description": tool.description or "",
                        "parameters": tool.input_schema,
                    },
                })
            self.sessions[name] = session

    async def call(self, tool_name: str, args: dict) -> str:
        server = self.tool_owner.get(tool_name)
        if server is None:
            return f"Error: unknown tool '{tool_name}'."
        result = await self.sessions[server].call_tool(tool_name, args)
        text = "\n".join(c.text for c in result.content if c.type == "text")
        return f"Error: {text}" if result.is_error else text

    async def close(self):
        await self.stack.aclose()