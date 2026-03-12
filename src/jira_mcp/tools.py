"""Dynamic MCP tool generation from Jira OpenAPI spec."""

import json
import re
from pathlib import Path
from typing import Any

from mcp import types


def _camel_to_snake(name: str) -> str:
    """Convert camelCase operationId to snake_case tool name."""
    s1 = re.sub(r"(.)([A-Z][a-z]+)", r"\1_\2", name)
    return re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", s1).lower()


def _sanitize_tool_name(name: str) -> str:
    """Ensure tool name only contains alphanumeric chars and underscores."""
    name = _camel_to_snake(name)
    name = re.sub(r"[^a-z0-9_]", "_", name)
    name = re.sub(r"_+", "_", name).strip("_")
    # Tool names must not exceed 64 chars per MCP spec recommendation
    return name[:64]


def _resolve_ref(ref: str, components: dict[str, Any]) -> dict[str, Any]:
    """Resolve a $ref within OpenAPI components."""
    # e.g. "#/components/schemas/IssueBean"
    parts = ref.lstrip("#/").split("/")
    resolved: Any = {"components": components}
    for part in parts:
        resolved = resolved.get(part, {})
    return resolved if isinstance(resolved, dict) else {}


def _schema_to_json_schema(
    schema: dict[str, Any],
    components: dict[str, Any],
    depth: int = 0,
    for_output: bool = False,
) -> dict[str, Any]:
    """Convert an OpenAPI schema fragment to a JSON Schema object.

    Args:
        schema: The OpenAPI schema fragment to convert.
        components: The OpenAPI components dict for resolving ``$ref``\\ s.
        depth: Current recursion depth (used to limit property expansion).
        for_output: When *True* the schema is used as an MCP ``outputSchema``
            (i.e. for validating API *responses*).  In that case
            ``additionalProperties: false`` is **not** propagated because the
            Jira API regularly returns extra fields not listed in the spec, and
            a strict schema would cause false-negative validation failures.
    """
    if not schema:
        return {"type": "string"}

    if "$ref" in schema and depth < 3:
        resolved = _resolve_ref(schema["$ref"], components)
        return _schema_to_json_schema(resolved, components, depth + 1, for_output)

    result: dict[str, Any] = {}

    typ = schema.get("type")
    if typ:
        result["type"] = typ
    if "format" in schema:
        result["format"] = schema["format"]
    if "enum" in schema:
        result["enum"] = schema["enum"]
    # Only include description at depth 0 (top-level body schema); omit from
    # nested properties to keep the tools/list response size small.
    if "description" in schema and depth == 0:
        result["description"] = schema["description"][:120]
    # Omit default values from nested schemas — they bloat the response without
    # adding value for an AI client.
    if "default" in schema and depth == 0:
        result["default"] = schema["default"]
    if schema.get("nullable") and isinstance(result.get("type"), str):
        # OpenAPI 3.0 nullable:true → JSON Schema type array with "null"
        result["type"] = [result["type"], "null"]

    if typ == "array" and "items" in schema:
        result["items"] = _schema_to_json_schema(
            schema["items"], components, depth + 1, for_output
        )

    if (
        typ == "object"
        or "properties" in schema
        or "allOf" in schema
        or "oneOf" in schema
    ):
        if "properties" in schema and depth < 2:
            props = {}
            for prop_name, prop_schema in schema["properties"].items():
                props[prop_name] = _schema_to_json_schema(
                    prop_schema, components, depth + 1, for_output
                )
            result["properties"] = props
        if "required" in schema:
            result["required"] = schema["required"]
        if "additionalProperties" in schema:
            ap = schema["additionalProperties"]
            # Never propagate additionalProperties: false.
            # - For output schemas: the live Jira API returns fields beyond
            #   what the spec declares, so a strict schema causes false-negative
            #   validation errors.
            # - For input schemas: `additionalProperties: false` on a request
            #   body bean (e.g. SearchAndReconcileRequestBean) is meant for the
            #   Jira API itself, not for the MCP layer.  Propagating it causes
            #   the MCP framework to reject every field the caller passes,
            #   making the tool completely unusable.
            if ap is not False:
                result["additionalProperties"] = (
                    _schema_to_json_schema(ap, components, depth + 1)
                    if isinstance(ap, dict)
                    else ap
                )
        if not result.get("type") and (result.get("properties") or depth == 0):
            result["type"] = "object"

    if not result:
        result = {"type": "string"}

    return result


def _build_input_schema(
    parameters: list[dict[str, Any]],
    request_body: dict[str, Any] | None,
    components: dict[str, Any],
) -> dict[str, Any]:
    """Build a JSON Schema dict for MCP tool input from OpenAPI parameters."""
    properties: dict[str, Any] = {}
    required: list[str] = []

    for param in parameters:
        name = param["name"]
        raw_schema = param.get("schema", {})

        # Resolve $ref in parameter schema
        if "$ref" in raw_schema:
            raw_schema = _resolve_ref(raw_schema["$ref"], components)

        prop = _schema_to_json_schema(raw_schema, components)
        raw_desc = param.get("description", f"({param.get('in', 'query')} parameter)")
        # Truncate parameter descriptions to keep the tools/list response small
        prop["description"] = raw_desc[:120]

        properties[name] = prop
        if param.get("required", False):
            required.append(name)

    if request_body:
        content = request_body.get("content", {})
        json_content = (
            content.get("application/json")
            or content.get("application/octet-stream")
            or next(iter(content.values()), {})
        )
        body_schema = json_content.get("schema", {})
        if body_schema:
            # Use depth=0 so that a top-level $ref is resolved and its properties
            # are fully expanded (depth < 2 guard allows one more level of nesting).
            # Previously depth=1 caused the $ref resolution to consume depth 0→1,
            # leaving properties at depth 2 which were then silently dropped,
            # resulting in an opaque "body: {}" schema that gave Claude no guidance
            # on what fields to pass (e.g. jql, maxResults, fields).
            resolved_body = _schema_to_json_schema(body_schema, components, depth=0)
        else:
            resolved_body = {"type": "object"}

        resolved_body["description"] = (
            request_body.get("description") or "Request body (JSON object)"
        )
        properties["body"] = resolved_body
        if request_body.get("required", False):
            required.append("body")

    schema: dict[str, Any] = {
        "type": "object",
        "properties": properties,
    }
    if required:
        schema["required"] = required
    return schema


# Allowlist of Jira operationIds to expose as MCP tools.
# Covers all common actions around stories, epics, bugs, and sprints.
_ALLOWED_OPERATION_IDS: frozenset[str] = frozenset(
    {
        # ── Issue search & retrieval ──────────────────────────────────────
        "searchAndReconsileIssuesUsingJqlPost",
        "getIssue",
        "bulkFetchIssues",
        # ── Issue create / edit / delete ──────────────────────────────────
        "createIssue",
        "createIssues",  # bulk create
        "editIssue",
        "deleteIssue",
        "assignIssue",
        # ── Issue transitions ─────────────────────────────────────────────
        "getTransitions",
        "doTransition",
        # ── Bulk operations ───────────────────────────────────────────────
        "submitBulkEdit",
        "submitBulkDelete",
        "submitBulkMove",
        "submitBulkTransition",
        # ── Comments ──────────────────────────────────────────────────────
        "getComments",
        "addComment",
        "getComment",
        "updateComment",
        "deleteComment",
        # ── Issue links ───────────────────────────────────────────────────
        "linkIssues",
        "getIssueLink",
        "getIssueLinkTypes",
        "deleteIssueLink",
        # ── Remote issue links ────────────────────────────────────────────
        "getRemoteIssueLinks",
        "createOrUpdateRemoteIssueLink",
        "getRemoteIssueLinkById",
        "deleteRemoteIssueLinkById",
        # ── Worklogs ──────────────────────────────────────────────────────
        "getIssueWorklog",
        "addWorklog",
        "getWorklog",
        "updateWorklog",
        "deleteWorklog",
        # ── Watchers & votes ──────────────────────────────────────────────
        "getIssueWatchers",
        "addWatcher",
        "removeWatcher",
        "getVotes",
        "addVote",
        "removeVote",
        # ── Changelogs ────────────────────────────────────────────────────
        "getChangeLogs",
        "getChangeLogsByIds",
        # ── Issue properties ──────────────────────────────────────────────
        "getIssueProperty",
        "setIssueProperty",
        "deleteIssueProperty",
        # ── Attachments ───────────────────────────────────────────────────
        "addAttachment",
        "getAttachment",
        # ── Projects ──────────────────────────────────────────────────────
        "searchProjects",
        "getProject",
        "getAllProjects",
        # ── Project versions & components ─────────────────────────────────
        "getProjectVersions",
        "createVersion",
        "getProjectComponents",
        "createComponent",
        # ── Users & assignees ─────────────────────────────────────────────
        "getUser",
        "findUsers",
        "findUsersAssignableToIssues",
        "findBulkAssignableUsers",
        # ── Issue fields & metadata ───────────────────────────────────────
        "getCreateIssueMeta",
        "getEditIssueMeta",
        "getFields",
        "getIssueTypesForProject",
        # ── Priorities, statuses & labels ─────────────────────────────────
        "getPriorities",
        "getStatuses",
        "getAllLabels",
        # ── Sprints & boards (Jira Software / Agile API) ──────────────────
        "getIssuesForSprint",
        "getAllSprints",
        "getBoard",
        "getAllBoards",
    }
)


class ToolRegistry:
    """
    Holds all dynamically generated tools from the Jira OpenAPI spec.
    Each entry maps tool_name -> (http_method, api_path, param_list, has_body).
    """

    def __init__(self) -> None:
        self._tools: list[types.Tool] = []
        self._dispatch: dict[str, tuple[str, str, list[dict[str, Any]], bool]] = {}

    def load_from_spec(self, spec_path: Path, use_allowlist: bool = True) -> None:
        """Parse the OpenAPI spec and populate tools.

        Args:
            spec_path: Path to the OpenAPI JSON spec file.
            use_allowlist: When True (default), only operations in
                ``_ALLOWED_OPERATION_IDS`` are exposed as tools.  Set to
                False to load every operation (useful for testing).
        """
        with open(spec_path) as f:
            spec = json.load(f)

        components = spec.get("components", {})
        paths = spec.get("paths", {})
        seen_names: set[str] = set()

        for path, path_item in paths.items():
            path_level_params: list[dict[str, Any]] = path_item.get("parameters", [])

            for method in ("get", "post", "put", "delete", "patch"):
                operation = path_item.get(method)
                if not operation:
                    continue

                operation_id = operation.get("operationId")
                if not operation_id:
                    slug = re.sub(r"[^a-zA-Z0-9]", "_", path)
                    operation_id = f"{method}_{slug}"

                # Skip operations not in the whitelist (unless disabled)
                if use_allowlist and operation_id not in _ALLOWED_OPERATION_IDS:
                    continue

                tool_name = _sanitize_tool_name(operation_id)

                # Deduplicate
                base_name = tool_name
                suffix = 1
                while tool_name in seen_names:
                    tool_name = f"{base_name}_{suffix}"[:64]
                    suffix += 1
                seen_names.add(tool_name)

                # Merge path-level + operation-level parameters
                op_params: list[dict[str, Any]] = operation.get("parameters", [])
                all_params = list(path_level_params) + list(op_params)

                request_body = operation.get("requestBody")
                input_schema = _build_input_schema(all_params, request_body, components)

                summary = operation.get("summary", "")
                description = operation.get("description", "")
                # Use only the summary as the tool description to keep the
                # tools/list response small. The full API description is
                # verbose and bloats the response beyond client limits.
                tool_description = summary or description.split("\n")[0] or tool_name
                # Hard cap as a safety net
                if len(tool_description) > 256:
                    tool_description = tool_description[:253] + "..."

                tool = types.Tool(
                    name=tool_name,
                    description=tool_description,
                    inputSchema=input_schema,
                )
                self._tools.append(tool)
                self._dispatch[tool_name] = (
                    method.upper(),
                    path,
                    all_params,
                    request_body is not None,
                )

    @property
    def tools(self) -> list[types.Tool]:
        return self._tools

    def get_tool(self, tool_name: str) -> types.Tool | None:
        """Return the Tool definition for *tool_name*, or None if not found."""
        return next((t for t in self._tools if t.name == tool_name), None)

    def get_dispatch(
        self, tool_name: str
    ) -> tuple[str, str, list[dict[str, Any]], bool] | None:
        return self._dispatch.get(tool_name)
