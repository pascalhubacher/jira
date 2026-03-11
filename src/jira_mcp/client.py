"""Jira Cloud REST API HTTP client."""

import base64
import os
from typing import Any

import httpx


class JiraClient:
    """HTTP client for Jira Cloud REST API v3."""

    def __init__(self) -> None:
        base_url = os.environ.get("JIRA_BASE_URL", "").rstrip("/")
        email = os.environ.get("JIRA_EMAIL", "")
        api_token = os.environ.get("JIRA_API_TOKEN", "")

        if not base_url:
            raise ValueError("JIRA_BASE_URL environment variable is required")
        if not email:
            raise ValueError("JIRA_EMAIL environment variable is required")
        if not api_token:
            raise ValueError("JIRA_API_TOKEN environment variable is required")

        credentials = base64.b64encode(f"{email}:{api_token}".encode()).decode()
        self._client = httpx.AsyncClient(
            base_url=base_url,
            headers={
                "Authorization": f"Basic {credentials}",
                "Accept": "application/json",
                "Content-Type": "application/json",
            },
            timeout=30.0,
        )

    async def request(
        self,
        method: str,
        path: str,
        path_params: dict[str, Any] | None = None,
        query_params: dict[str, Any] | None = None,
        body: Any = None,
    ) -> Any:
        """Execute an HTTP request against the Jira API."""
        # Substitute path parameters
        if path_params:
            for key, value in path_params.items():
                path = path.replace(f"{{{key}}}", str(value))

        # Filter out None values from query params
        filtered_query: dict[str, Any] = {}
        if query_params:
            for key, value in query_params.items():
                if value is not None:
                    filtered_query[key] = value

        kwargs: dict[str, Any] = {}
        if filtered_query:
            kwargs["params"] = filtered_query
        if body is not None:
            kwargs["json"] = body

        response = await self._client.request(method, path, **kwargs)

        if response.status_code == 204:
            return {"status": "success", "code": 204}

        try:
            data = response.json()
        except Exception:
            data = {"raw": response.text, "code": response.status_code}

        if response.is_error:
            error_msg = data if isinstance(data, dict) else {"message": str(data)}
            raise RuntimeError(
                f"Jira API error {response.status_code}: {error_msg}"
            )

        return data

    async def close(self) -> None:
        await self._client.aclose()
