"""Tests for src/jira_mcp/server.py"""

import json
import os
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from mcp import types
from mcp.server import Server
from mcp.types import CallToolRequest, CallToolRequestParams, ListToolsRequest

from src.jira_mcp.server import create_server
from src.jira_mcp.tools import ToolRegistry


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _env(base_url="https://test.atlassian.net", email="u@e.com", token="tok"):
    return {"JIRA_BASE_URL": base_url, "JIRA_EMAIL": email, "JIRA_API_TOKEN": token}


def _make_minimal_spec(paths: dict) -> dict:
    return {
        "openapi": "3.0.0",
        "info": {"title": "Test API", "version": "1.0.0"},
        "paths": paths,
        "components": {},
    }


def _write_spec(spec: dict) -> Path:
    tmp = tempfile.NamedTemporaryFile(
        mode="w", suffix=".json", delete=False, encoding="utf-8"
    )
    json.dump(spec, tmp)
    tmp.flush()
    return Path(tmp.name)


def _simple_spec() -> Path:
    """Spec with one GET and one POST operation."""
    return _write_spec(
        _make_minimal_spec(
            {
                "/rest/api/3/issue/{issueIdOrKey}": {
                    "get": {
                        "operationId": "getIssue",
                        "summary": "Get issue",
                        "parameters": [
                            {
                                "name": "issueIdOrKey",
                                "in": "path",
                                "required": True,
                                "schema": {"type": "string"},
                            },
                            {
                                "name": "fields",
                                "in": "query",
                                "required": False,
                                "schema": {"type": "string"},
                            },
                        ],
                    }
                },
                "/rest/api/3/issue": {
                    "post": {
                        "operationId": "createIssue",
                        "summary": "Create issue",
                        "parameters": [],
                        "requestBody": {
                            "required": True,
                            "content": {
                                "application/json": {"schema": {"type": "object"}}
                            },
                        },
                    }
                },
            }
        )
    )


def _make_list_tools_request() -> ListToolsRequest:
    return ListToolsRequest(id=1, method="tools/list", params=None)


def _make_call_tool_request(name: str, arguments: dict) -> CallToolRequest:
    return CallToolRequest(
        id=1,
        method="tools/call",
        params=CallToolRequestParams(name=name, arguments=arguments),
    )


# ---------------------------------------------------------------------------
# create_server
# ---------------------------------------------------------------------------


class TestCreateServer:
    def test_returns_server_and_registry(self):
        spec_path = _simple_spec()
        server, registry = create_server(spec_path)
        assert isinstance(server, Server)
        assert isinstance(registry, ToolRegistry)

    def test_server_name_is_jira_cloud_mcp(self):
        spec_path = _simple_spec()
        server, _ = create_server(spec_path)
        assert server.name == "jira-cloud-mcp"

    def test_registry_has_expected_tools(self):
        spec_path = _simple_spec()
        _, registry = create_server(spec_path)
        names = {t.name for t in registry.tools}
        assert "get_issue" in names
        assert "create_issue" in names

    def test_empty_spec_creates_server_with_no_tools(self):
        spec_path = _write_spec(_make_minimal_spec({}))
        _, registry = create_server(spec_path)
        assert registry.tools == []

    def test_list_tools_handler_registered(self):
        spec_path = _simple_spec()
        server, _ = create_server(spec_path)
        assert types.ListToolsRequest in server.request_handlers

    def test_call_tool_handler_registered(self):
        spec_path = _simple_spec()
        server, _ = create_server(spec_path)
        assert types.CallToolRequest in server.request_handlers


# ---------------------------------------------------------------------------
# list_tools handler – tested via registry (handler just returns registry.tools)
# ---------------------------------------------------------------------------


class TestListToolsHandler:
    @pytest.mark.asyncio
    async def test_list_tools_returns_all_tools(self):
        spec_path = _simple_spec()
        server, registry = create_server(spec_path)
        handler = server.request_handlers[types.ListToolsRequest]
        result = await handler(_make_list_tools_request())
        # result is a ListToolsResult; .root wraps it
        tool_list = result.root.tools if hasattr(result, "root") else result.tools
        assert len(tool_list) == len(registry.tools)

    @pytest.mark.asyncio
    async def test_list_tools_returns_tool_instances(self):
        spec_path = _simple_spec()
        server, _ = create_server(spec_path)
        handler = server.request_handlers[types.ListToolsRequest]
        result = await handler(_make_list_tools_request())
        tool_list = result.root.tools if hasattr(result, "root") else result.tools
        for tool in tool_list:
            assert isinstance(tool, types.Tool)
            assert tool.name
            assert isinstance(tool.inputSchema, dict)

    @pytest.mark.asyncio
    async def test_list_tools_names_match_registry(self):
        spec_path = _simple_spec()
        server, registry = create_server(spec_path)
        handler = server.request_handlers[types.ListToolsRequest]
        result = await handler(_make_list_tools_request())
        tool_list = result.root.tools if hasattr(result, "root") else result.tools
        listed_names = {t.name for t in tool_list}
        registry_names = {t.name for t in registry.tools}
        assert listed_names == registry_names

    def test_registry_tools_returns_list(self):
        """list_tools handler returns registry.tools — test the registry directly."""
        spec_path = _simple_spec()
        _, registry = create_server(spec_path)
        assert isinstance(registry.tools, list)
        assert len(registry.tools) == 2


# ---------------------------------------------------------------------------
# call_tool handler – argument routing
# ---------------------------------------------------------------------------


class TestCallToolArgumentRouting:
    """Tests that call_tool correctly splits arguments into path / query / body."""

    @pytest.mark.asyncio
    async def test_unknown_tool_raises_value_error(self):
        spec_path = _simple_spec()
        server, _ = create_server(spec_path)
        handler = server.request_handlers[types.CallToolRequest]
        with patch.dict(os.environ, _env(), clear=True):
            result = await handler(_make_call_tool_request("no_such_tool", {}))
            # MCP wraps errors as isError=True in the result
            assert result.root.isError is True

    @pytest.mark.asyncio
    async def test_path_param_substituted_in_request(self):
        spec_path = _simple_spec()
        server, _ = create_server(spec_path)
        handler = server.request_handlers[types.CallToolRequest]

        with patch.dict(os.environ, _env(), clear=True):
            with patch("src.jira_mcp.server.JiraClient") as MockClient:
                instance = MockClient.return_value
                instance.request = AsyncMock(return_value={"id": "10001"})
                instance.close = AsyncMock()

                await handler(_make_call_tool_request("get_issue", {"issueIdOrKey": "ABC-1"}))

                instance.request.assert_called_once()
                _, _, path_params, _, _ = instance.request.call_args[0]
                assert path_params == {"issueIdOrKey": "ABC-1"}

    @pytest.mark.asyncio
    async def test_query_param_passed_correctly(self):
        spec_path = _simple_spec()
        server, _ = create_server(spec_path)
        handler = server.request_handlers[types.CallToolRequest]

        with patch.dict(os.environ, _env(), clear=True):
            with patch("src.jira_mcp.server.JiraClient") as MockClient:
                instance = MockClient.return_value
                instance.request = AsyncMock(return_value={"id": "10001"})
                instance.close = AsyncMock()

                await handler(
                    _make_call_tool_request(
                        "get_issue",
                        {"issueIdOrKey": "ABC-1", "fields": "summary,description"},
                    )
                )

                _, _, _, query_params, _ = instance.request.call_args[0]
                assert query_params == {"fields": "summary,description"}

    @pytest.mark.asyncio
    async def test_missing_optional_params_not_passed(self):
        spec_path = _simple_spec()
        server, _ = create_server(spec_path)
        handler = server.request_handlers[types.CallToolRequest]

        with patch.dict(os.environ, _env(), clear=True):
            with patch("src.jira_mcp.server.JiraClient") as MockClient:
                instance = MockClient.return_value
                instance.request = AsyncMock(return_value={"id": "10001"})
                instance.close = AsyncMock()

                await handler(_make_call_tool_request("get_issue", {"issueIdOrKey": "ABC-1"}))

                _, _, _, query_params, _ = instance.request.call_args[0]
                assert query_params == {}

    @pytest.mark.asyncio
    async def test_body_passed_for_post(self):
        spec_path = _simple_spec()
        server, _ = create_server(spec_path)
        handler = server.request_handlers[types.CallToolRequest]

        body_data = {"fields": {"summary": "New issue", "project": {"key": "ABC"}}}

        with patch.dict(os.environ, _env(), clear=True):
            with patch("src.jira_mcp.server.JiraClient") as MockClient:
                instance = MockClient.return_value
                instance.request = AsyncMock(return_value={"id": "10001", "key": "ABC-2"})
                instance.close = AsyncMock()

                await handler(_make_call_tool_request("create_issue", {"body": body_data}))

                _, _, _, _, body = instance.request.call_args[0]
                assert body == body_data

    @pytest.mark.asyncio
    async def test_no_body_for_get(self):
        spec_path = _simple_spec()
        server, _ = create_server(spec_path)
        handler = server.request_handlers[types.CallToolRequest]

        with patch.dict(os.environ, _env(), clear=True):
            with patch("src.jira_mcp.server.JiraClient") as MockClient:
                instance = MockClient.return_value
                instance.request = AsyncMock(return_value={"id": "10001"})
                instance.close = AsyncMock()

                await handler(_make_call_tool_request("get_issue", {"issueIdOrKey": "ABC-1"}))

                _, _, _, _, body = instance.request.call_args[0]
                assert body is None

    @pytest.mark.asyncio
    async def test_correct_http_method_used_get(self):
        spec_path = _simple_spec()
        server, _ = create_server(spec_path)
        handler = server.request_handlers[types.CallToolRequest]

        with patch.dict(os.environ, _env(), clear=True):
            with patch("src.jira_mcp.server.JiraClient") as MockClient:
                instance = MockClient.return_value
                instance.request = AsyncMock(return_value={})
                instance.close = AsyncMock()

                await handler(_make_call_tool_request("get_issue", {"issueIdOrKey": "ABC-1"}))
                method = instance.request.call_args[0][0]
                assert method == "GET"

    @pytest.mark.asyncio
    async def test_correct_http_method_used_post(self):
        spec_path = _simple_spec()
        server, _ = create_server(spec_path)
        handler = server.request_handlers[types.CallToolRequest]

        with patch.dict(os.environ, _env(), clear=True):
            with patch("src.jira_mcp.server.JiraClient") as MockClient:
                instance = MockClient.return_value
                instance.request = AsyncMock(return_value={"id": "10002"})
                instance.close = AsyncMock()

                await handler(_make_call_tool_request("create_issue", {"body": {}}))
                method = instance.request.call_args[0][0]
                assert method == "POST"


# ---------------------------------------------------------------------------
# call_tool handler – response formatting
# ---------------------------------------------------------------------------


class TestCallToolResponseFormatting:
    @pytest.mark.asyncio
    async def test_result_is_call_tool_result(self):
        spec_path = _simple_spec()
        server, _ = create_server(spec_path)
        handler = server.request_handlers[types.CallToolRequest]

        api_response = {"id": "10001", "key": "ABC-1"}

        with patch.dict(os.environ, _env(), clear=True):
            with patch("src.jira_mcp.server.JiraClient") as MockClient:
                instance = MockClient.return_value
                instance.request = AsyncMock(return_value=api_response)
                instance.close = AsyncMock()

                result = await handler(
                    _make_call_tool_request("get_issue", {"issueIdOrKey": "ABC-1"})
                )

        call_result = result.root
        assert not call_result.isError
        assert len(call_result.content) == 1
        assert isinstance(call_result.content[0], types.TextContent)

    @pytest.mark.asyncio
    async def test_result_text_is_valid_json(self):
        spec_path = _simple_spec()
        server, _ = create_server(spec_path)
        handler = server.request_handlers[types.CallToolRequest]

        api_response = {"id": "10001", "key": "ABC-1"}

        with patch.dict(os.environ, _env(), clear=True):
            with patch("src.jira_mcp.server.JiraClient") as MockClient:
                instance = MockClient.return_value
                instance.request = AsyncMock(return_value=api_response)
                instance.close = AsyncMock()

                result = await handler(
                    _make_call_tool_request("get_issue", {"issueIdOrKey": "ABC-1"})
                )

        text = result.root.content[0].text
        parsed = json.loads(text)
        assert parsed == api_response

    @pytest.mark.asyncio
    async def test_result_serializes_non_json_types(self):
        """Non-JSON-serialisable values (like datetime) should not raise."""
        from datetime import datetime

        spec_path = _simple_spec()
        server, _ = create_server(spec_path)
        handler = server.request_handlers[types.CallToolRequest]

        api_response = {"created": datetime(2024, 1, 15, 10, 30)}

        with patch.dict(os.environ, _env(), clear=True):
            with patch("src.jira_mcp.server.JiraClient") as MockClient:
                instance = MockClient.return_value
                instance.request = AsyncMock(return_value=api_response)
                instance.close = AsyncMock()

                result = await handler(
                    _make_call_tool_request("get_issue", {"issueIdOrKey": "ABC-1"})
                )

        assert result.root.content[0].text is not None

    @pytest.mark.asyncio
    async def test_result_text_type_is_text(self):
        spec_path = _simple_spec()
        server, _ = create_server(spec_path)
        handler = server.request_handlers[types.CallToolRequest]

        with patch.dict(os.environ, _env(), clear=True):
            with patch("src.jira_mcp.server.JiraClient") as MockClient:
                instance = MockClient.return_value
                instance.request = AsyncMock(return_value={})
                instance.close = AsyncMock()

                result = await handler(
                    _make_call_tool_request("get_issue", {"issueIdOrKey": "ABC-1"})
                )

        assert result.root.content[0].type == "text"


# ---------------------------------------------------------------------------
# call_tool handler – client lifecycle
# ---------------------------------------------------------------------------


class TestCallToolClientLifecycle:
    @pytest.mark.asyncio
    async def test_client_closed_after_successful_call(self):
        spec_path = _simple_spec()
        server, _ = create_server(spec_path)
        handler = server.request_handlers[types.CallToolRequest]

        with patch.dict(os.environ, _env(), clear=True):
            with patch("src.jira_mcp.server.JiraClient") as MockClient:
                instance = MockClient.return_value
                instance.request = AsyncMock(return_value={"id": "10001"})
                instance.close = AsyncMock()

                await handler(_make_call_tool_request("get_issue", {"issueIdOrKey": "ABC-1"}))

                instance.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_client_closed_even_when_request_raises(self):
        spec_path = _simple_spec()
        server, _ = create_server(spec_path)
        handler = server.request_handlers[types.CallToolRequest]

        with patch.dict(os.environ, _env(), clear=True):
            with patch("src.jira_mcp.server.JiraClient") as MockClient:
                instance = MockClient.return_value
                instance.request = AsyncMock(side_effect=RuntimeError("Jira API error 500"))
                instance.close = AsyncMock()

                # MCP server catches errors and wraps them as isError=True
                result = await handler(
                    _make_call_tool_request("get_issue", {"issueIdOrKey": "ABC-1"})
                )
                assert result.root.isError is True
                instance.close.assert_called_once()


# ---------------------------------------------------------------------------
# Integration – create_server with real Jira spec
# ---------------------------------------------------------------------------


class TestCreateServerRealSpec:
    def test_real_spec_loads_all_tools(self):
        real_spec = (
            Path(__file__).parent.parent
            / "Building MCP with LLMs"
            / "jira-swagger-v3.v3.json"
        )
        if not real_spec.exists():
            pytest.skip("Real Jira spec not found")

        _, registry = create_server(real_spec)
        assert len(registry.tools) > 400

    def test_real_spec_all_tool_names_unique(self):
        real_spec = (
            Path(__file__).parent.parent
            / "Building MCP with LLMs"
            / "jira-swagger-v3.v3.json"
        )
        if not real_spec.exists():
            pytest.skip("Real Jira spec not found")

        _, registry = create_server(real_spec)
        names = [t.name for t in registry.tools]
        assert len(set(names)) == len(names)

    @pytest.mark.asyncio
    async def test_real_spec_list_tools_via_handler(self):
        real_spec = (
            Path(__file__).parent.parent
            / "Building MCP with LLMs"
            / "jira-swagger-v3.v3.json"
        )
        if not real_spec.exists():
            pytest.skip("Real Jira spec not found")

        server, registry = create_server(real_spec)
        handler = server.request_handlers[types.ListToolsRequest]
        result = await handler(_make_list_tools_request())
        tool_list = result.root.tools if hasattr(result, "root") else result.tools
        assert len(tool_list) == len(registry.tools)

    def test_real_spec_get_issue_dispatch(self):
        real_spec = (
            Path(__file__).parent.parent
            / "Building MCP with LLMs"
            / "jira-swagger-v3.v3.json"
        )
        if not real_spec.exists():
            pytest.skip("Real Jira spec not found")

        _, registry = create_server(real_spec)
        dispatch = registry.get_dispatch("get_issue")
        assert dispatch is not None
        method, path, _, _ = dispatch
        assert method == "GET"
        assert "issueIdOrKey" in path

    def test_real_spec_create_issue_has_body(self):
        real_spec = (
            Path(__file__).parent.parent
            / "Building MCP with LLMs"
            / "jira-swagger-v3.v3.json"
        )
        if not real_spec.exists():
            pytest.skip("Real Jira spec not found")

        _, registry = create_server(real_spec)
        dispatch = registry.get_dispatch("create_issue")
        assert dispatch is not None
        _, _, _, has_body = dispatch
        assert has_body is True
