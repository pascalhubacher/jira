"""Jira Cloud MCP Server entry point."""

import asyncio
import json
import logging
import os
import time
from pathlib import Path
from typing import Any

import jsonschema
from dotenv import load_dotenv
from mcp import types
from mcp.server import NotificationOptions, Server
from mcp.server.stdio import stdio_server
from mcp.shared.exceptions import McpError

from .client import JiraClient
from .tools import ToolRegistry

load_dotenv()

logger = logging.getLogger(__name__)

_SENSITIVE_KEYS = frozenset(
    {
        "password",
        "passwd",
        "secret",
        "token",
        "apikey",
        "api_key",
        "authorization",
        "credential",
        "credentials",
        "private_key",
    }
)


def _sanitize_response(data: Any) -> Any:
    """Redact sensitive keys and truncate excessively long strings in API responses."""
    if isinstance(data, dict):
        return {
            k: "[REDACTED]" if k.lower() in _SENSITIVE_KEYS else _sanitize_response(v)
            for k, v in data.items()
        }
    if isinstance(data, list):
        return [_sanitize_response(item) for item in data]
    if isinstance(data, str) and len(data) > 10_000:
        return data[:10_000] + "...[truncated]"
    return data


class _RateLimiter:
    """Token-bucket rate limiter for tool invocations.

    Reads JIRA_MCP_RATE_LIMIT (calls/second, default 10) from the environment.
    """

    def __init__(self) -> None:
        self._rate = float(os.environ.get("JIRA_MCP_RATE_LIMIT", "10"))
        self._tokens = self._rate
        self._last_refill = time.monotonic()
        self._lock = asyncio.Lock()

    async def acquire(self) -> None:
        async with self._lock:
            now = time.monotonic()
            elapsed = now - self._last_refill
            self._tokens = min(self._rate, self._tokens + elapsed * self._rate)
            self._last_refill = now

            if self._tokens < 1:
                wait = (1.0 - self._tokens) / self._rate
                await asyncio.sleep(wait)
                self._tokens = 0.0
            else:
                self._tokens -= 1.0


# Path to the Jira OpenAPI spec bundled inside the package directory
_SPEC_PATH = Path(__file__).parent / "jira-swagger-v3.v3.json"


def create_server(spec_path: Path = _SPEC_PATH) -> tuple[Server, ToolRegistry]:
    """Create and configure the MCP server with all Jira tools."""
    registry = ToolRegistry()
    registry.load_from_spec(spec_path)

    server = Server("jira-cloud-mcp")
    rate_limiter = _RateLimiter()

    @server.list_tools()
    async def list_tools() -> list[types.Tool]:
        return registry.tools

    @server.call_tool()
    async def call_tool(name: str, arguments: dict) -> types.CallToolResult:
        await rate_limiter.acquire()

        dispatch = registry.get_dispatch(name)
        if dispatch is None:
            # Raise a proper JSON-RPC -32602 (Invalid Params) protocol error so
            # the client receives a structured error response, not a soft isError result.
            raise McpError(
                types.ErrorData(code=-32602, message=f"Unknown tool: {name}")
            )

        http_method, api_path, params, has_body = dispatch

        # Validate arguments against the tool's inputSchema before dispatching.
        tool_def = registry.get_tool(name)
        if tool_def is not None:
            try:
                jsonschema.validate(instance=arguments, schema=tool_def.inputSchema)
            except jsonschema.ValidationError as exc:
                return types.CallToolResult(
                    content=[
                        types.TextContent(
                            type="text", text=f"Input validation error: {exc.message}"
                        )
                    ],
                    isError=True,
                )

        # Separate path, query params and body from arguments
        path_params: dict = {}
        query_params: dict = {}
        body = None

        for param in params:
            pname = param["name"]
            location = param.get("in", "query")
            value = arguments.get(pname)
            if value is None:
                continue
            if location == "path":
                path_params[pname] = value
            elif location == "query":
                query_params[pname] = value
            # header/cookie params are handled by the HTTP client itself

        if has_body:
            body = arguments.get("body")

        client = JiraClient()
        try:
            result = await client.request(
                http_method, api_path, path_params, query_params, body
            )
        except Exception as exc:
            return types.CallToolResult(
                content=[types.TextContent(type="text", text=str(exc))],
                isError=True,
            )
        finally:
            await client.close()

        sanitized = _sanitize_response(result)
        text = json.dumps(sanitized, indent=2, default=str)
        structured = sanitized if isinstance(sanitized, dict) else {"result": sanitized}
        # Return both unstructured (TextContent) and structured (dict) content.
        # The SDK validates structured against outputSchema when present.
        return types.CallToolResult(
            content=[types.TextContent(type="text", text=text)],
            structuredContent=structured,
        )

    return server, registry


async def run_server() -> None:
    """Run the MCP server with stdio transport."""
    server, registry = create_server()
    logger.info(f"Jira Cloud MCP: loaded {len(registry.tools)} tools")

    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            # tools_changed=False: tools are static after startup; we never
            # emit notifications/tools/list_changed, so we advertise listChanged
            # as False to be honest with clients.
            server.create_initialization_options(
                notification_options=NotificationOptions(tools_changed=False)
            ),
        )


def main() -> None:
    """Entry point for the jira-mcp command."""
    import asyncio
    import sys

    logging.basicConfig(level=logging.WARNING, stream=sys.stderr)
    asyncio.run(run_server())


if __name__ == "__main__":
    main()
