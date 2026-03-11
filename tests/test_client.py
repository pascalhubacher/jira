"""Tests for src/jira_mcp/client.py"""

import base64
import os
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from src.jira_mcp.client import JiraClient


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_response(
    status_code: int,
    json_data=None,
    text: str = "",
    is_error: bool = False,
) -> MagicMock:
    """Build a mock httpx.Response."""
    resp = MagicMock(spec=httpx.Response)
    resp.status_code = status_code
    resp.is_error = is_error
    resp.text = text
    if json_data is not None:
        resp.json = MagicMock(return_value=json_data)
    else:
        resp.json = MagicMock(side_effect=Exception("no JSON"))
    return resp


def _env(base_url="https://test.atlassian.net", email="u@e.com", token="tok"):
    return {"JIRA_BASE_URL": base_url, "JIRA_EMAIL": email, "JIRA_API_TOKEN": token}


# ---------------------------------------------------------------------------
# __init__ / construction
# ---------------------------------------------------------------------------


class TestJiraClientInit:
    def test_raises_without_base_url(self):
        env = _env()
        env.pop("JIRA_BASE_URL")
        with patch.dict(os.environ, env, clear=True):
            # remove if present
            os.environ.pop("JIRA_BASE_URL", None)
            with pytest.raises(ValueError, match="JIRA_BASE_URL"):
                JiraClient()

    def test_raises_without_email(self):
        env = _env()
        with patch.dict(os.environ, {**env, "JIRA_EMAIL": ""}, clear=True):
            with pytest.raises(ValueError, match="JIRA_EMAIL"):
                JiraClient()

    def test_raises_without_token(self):
        env = _env()
        with patch.dict(os.environ, {**env, "JIRA_API_TOKEN": ""}, clear=True):
            with pytest.raises(ValueError, match="JIRA_API_TOKEN"):
                JiraClient()

    def test_trailing_slash_stripped_from_base_url(self):
        with patch.dict(os.environ, _env(base_url="https://test.atlassian.net/"), clear=True):
            client = JiraClient()
            assert str(client._client.base_url).rstrip("/") == "https://test.atlassian.net"

    def test_basic_auth_header_set(self):
        email = "user@example.com"
        token = "mytoken"
        expected = "Basic " + base64.b64encode(f"{email}:{token}".encode()).decode()
        with patch.dict(os.environ, _env(email=email, token=token), clear=True):
            client = JiraClient()
            auth_header = client._client.headers.get("authorization")
            assert auth_header == expected

    def test_accept_header_set(self):
        with patch.dict(os.environ, _env(), clear=True):
            client = JiraClient()
            assert client._client.headers.get("accept") == "application/json"

    def test_content_type_header_set(self):
        with patch.dict(os.environ, _env(), clear=True):
            client = JiraClient()
            assert client._client.headers.get("content-type") == "application/json"

    def test_timeout_is_30_seconds(self):
        with patch.dict(os.environ, _env(), clear=True):
            client = JiraClient()
            assert client._client.timeout.read == 30.0


# ---------------------------------------------------------------------------
# request – path parameter substitution
# ---------------------------------------------------------------------------


class TestJiraClientRequestPathParams:
    @pytest.fixture
    def client(self):
        with patch.dict(os.environ, _env(), clear=True):
            return JiraClient()

    @pytest.mark.asyncio
    async def test_path_param_substituted(self, client):
        mock_resp = _make_response(200, json_data={"id": "10001"})
        client._client.request = AsyncMock(return_value=mock_resp)

        await client.request("GET", "/rest/api/3/issue/{issueIdOrKey}", {"issueIdOrKey": "ABC-1"})

        called_path = client._client.request.call_args[0][1]
        assert called_path == "/rest/api/3/issue/ABC-1"

    @pytest.mark.asyncio
    async def test_multiple_path_params_substituted(self, client):
        mock_resp = _make_response(200, json_data={})
        client._client.request = AsyncMock(return_value=mock_resp)

        await client.request(
            "GET",
            "/rest/api/3/project/{projectKey}/role/{id}",
            {"projectKey": "PROJ", "id": "42"},
        )

        called_path = client._client.request.call_args[0][1]
        assert called_path == "/rest/api/3/project/PROJ/role/42"

    @pytest.mark.asyncio
    async def test_no_path_params_leaves_path_unchanged(self, client):
        mock_resp = _make_response(200, json_data={})
        client._client.request = AsyncMock(return_value=mock_resp)

        await client.request("GET", "/rest/api/3/serverInfo")

        called_path = client._client.request.call_args[0][1]
        assert called_path == "/rest/api/3/serverInfo"

    @pytest.mark.asyncio
    async def test_integer_path_param_converted_to_string(self, client):
        mock_resp = _make_response(200, json_data={})
        client._client.request = AsyncMock(return_value=mock_resp)

        await client.request("GET", "/rest/api/3/issue/{id}", {"id": 12345})

        called_path = client._client.request.call_args[0][1]
        assert "12345" in called_path


# ---------------------------------------------------------------------------
# request – query parameters
# ---------------------------------------------------------------------------


class TestJiraClientRequestQueryParams:
    @pytest.fixture
    def client(self):
        with patch.dict(os.environ, _env(), clear=True):
            return JiraClient()

    @pytest.mark.asyncio
    async def test_query_params_passed_to_httpx(self, client):
        mock_resp = _make_response(200, json_data=[])
        client._client.request = AsyncMock(return_value=mock_resp)

        await client.request("GET", "/search", query_params={"jql": "project=ABC", "maxResults": 50})

        kwargs = client._client.request.call_args[1]
        assert kwargs["params"] == {"jql": "project=ABC", "maxResults": 50}

    @pytest.mark.asyncio
    async def test_none_values_filtered_from_query_params(self, client):
        mock_resp = _make_response(200, json_data=[])
        client._client.request = AsyncMock(return_value=mock_resp)

        await client.request(
            "GET",
            "/search",
            query_params={"jql": "project=ABC", "fields": None, "maxResults": 10},
        )

        kwargs = client._client.request.call_args[1]
        assert "fields" not in kwargs["params"]
        assert kwargs["params"] == {"jql": "project=ABC", "maxResults": 10}

    @pytest.mark.asyncio
    async def test_all_none_query_params_omits_params_key(self, client):
        mock_resp = _make_response(200, json_data=[])
        client._client.request = AsyncMock(return_value=mock_resp)

        await client.request("GET", "/search", query_params={"a": None, "b": None})

        kwargs = client._client.request.call_args[1]
        assert "params" not in kwargs

    @pytest.mark.asyncio
    async def test_empty_query_params_omits_params_key(self, client):
        mock_resp = _make_response(200, json_data={})
        client._client.request = AsyncMock(return_value=mock_resp)

        await client.request("GET", "/rest/api/3/serverInfo", query_params={})

        kwargs = client._client.request.call_args[1]
        assert "params" not in kwargs


# ---------------------------------------------------------------------------
# request – request body
# ---------------------------------------------------------------------------


class TestJiraClientRequestBody:
    @pytest.fixture
    def client(self):
        with patch.dict(os.environ, _env(), clear=True):
            return JiraClient()

    @pytest.mark.asyncio
    async def test_body_passed_as_json(self, client):
        mock_resp = _make_response(201, json_data={"id": "10001"})
        client._client.request = AsyncMock(return_value=mock_resp)

        body = {"fields": {"summary": "New issue"}}
        await client.request("POST", "/rest/api/3/issue", body=body)

        kwargs = client._client.request.call_args[1]
        assert kwargs["json"] == body

    @pytest.mark.asyncio
    async def test_none_body_omits_json_key(self, client):
        mock_resp = _make_response(200, json_data={})
        client._client.request = AsyncMock(return_value=mock_resp)

        await client.request("GET", "/rest/api/3/serverInfo", body=None)

        kwargs = client._client.request.call_args[1]
        assert "json" not in kwargs


# ---------------------------------------------------------------------------
# request – response handling
# ---------------------------------------------------------------------------


class TestJiraClientResponseHandling:
    @pytest.fixture
    def client(self):
        with patch.dict(os.environ, _env(), clear=True):
            return JiraClient()

    @pytest.mark.asyncio
    async def test_200_returns_json(self, client):
        data = {"id": "10001", "key": "ABC-1"}
        mock_resp = _make_response(200, json_data=data)
        client._client.request = AsyncMock(return_value=mock_resp)

        result = await client.request("GET", "/rest/api/3/issue/ABC-1")
        assert result == data

    @pytest.mark.asyncio
    async def test_204_returns_success_dict(self, client):
        mock_resp = _make_response(204)
        client._client.request = AsyncMock(return_value=mock_resp)

        result = await client.request("DELETE", "/rest/api/3/issue/ABC-1")
        assert result == {"status": "success", "code": 204}

    @pytest.mark.asyncio
    async def test_non_json_response_returns_raw(self, client):
        mock_resp = _make_response(200, text="plain text response")
        mock_resp.is_error = False
        client._client.request = AsyncMock(return_value=mock_resp)

        result = await client.request("GET", "/rest/api/3/attachment/content/1")
        assert result["raw"] == "plain text response"

    @pytest.mark.asyncio
    async def test_400_raises_runtime_error(self, client):
        error_body = {"errorMessages": ["Invalid input"]}
        mock_resp = _make_response(400, json_data=error_body, is_error=True)
        client._client.request = AsyncMock(return_value=mock_resp)

        with pytest.raises(RuntimeError, match="Jira API error 400"):
            await client.request("POST", "/rest/api/3/issue", body={})

    @pytest.mark.asyncio
    async def test_401_raises_runtime_error(self, client):
        mock_resp = _make_response(401, json_data={"message": "Unauthorized"}, is_error=True)
        client._client.request = AsyncMock(return_value=mock_resp)

        with pytest.raises(RuntimeError, match="401"):
            await client.request("GET", "/rest/api/3/myself")

    @pytest.mark.asyncio
    async def test_403_raises_runtime_error(self, client):
        mock_resp = _make_response(403, json_data={"message": "Forbidden"}, is_error=True)
        client._client.request = AsyncMock(return_value=mock_resp)

        with pytest.raises(RuntimeError, match="403"):
            await client.request("GET", "/rest/api/3/issue/SECRET-1")

    @pytest.mark.asyncio
    async def test_404_raises_runtime_error(self, client):
        mock_resp = _make_response(404, json_data={"errorMessages": ["Not found"]}, is_error=True)
        client._client.request = AsyncMock(return_value=mock_resp)

        with pytest.raises(RuntimeError, match="404"):
            await client.request("GET", "/rest/api/3/issue/NOTEXIST-1")

    @pytest.mark.asyncio
    async def test_500_raises_runtime_error(self, client):
        mock_resp = _make_response(500, text="Internal Server Error", is_error=True)
        mock_resp.json = MagicMock(side_effect=Exception("no JSON"))
        client._client.request = AsyncMock(return_value=mock_resp)

        with pytest.raises(RuntimeError, match="500"):
            await client.request("GET", "/rest/api/3/issue/ABC-1")

    @pytest.mark.asyncio
    async def test_error_with_non_dict_json_body(self, client):
        mock_resp = _make_response(400, json_data=["error1", "error2"], is_error=True)
        client._client.request = AsyncMock(return_value=mock_resp)

        with pytest.raises(RuntimeError, match="400"):
            await client.request("POST", "/rest/api/3/issue", body={})

    @pytest.mark.asyncio
    async def test_http_method_passed_correctly(self, client):
        for method in ("GET", "POST", "PUT", "DELETE", "PATCH"):
            mock_resp = _make_response(200, json_data={})
            client._client.request = AsyncMock(return_value=mock_resp)
            await client.request(method, "/rest/api/3/serverInfo")
            assert client._client.request.call_args[0][0] == method


# ---------------------------------------------------------------------------
# close
# ---------------------------------------------------------------------------


class TestJiraClientClose:
    @pytest.mark.asyncio
    async def test_close_calls_aclose(self):
        with patch.dict(os.environ, _env(), clear=True):
            client = JiraClient()
            client._client.aclose = AsyncMock()
            await client.close()
            client._client.aclose.assert_called_once()
