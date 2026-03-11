"""Tests for src/jira_mcp/tools.py"""

import json
import tempfile
from pathlib import Path

import pytest

from src.jira_mcp.tools import (
    ToolRegistry,
    _build_input_schema,
    _camel_to_snake,
    _resolve_ref,
    _sanitize_tool_name,
    _schema_to_json_schema,
)


# ---------------------------------------------------------------------------
# _camel_to_snake
# ---------------------------------------------------------------------------


class TestCamelToSnake:
    def test_simple_camel(self):
        assert _camel_to_snake("getIssue") == "get_issue"

    def test_multi_word(self):
        assert _camel_to_snake("searchForIssuesUsingJql") == "search_for_issues_using_jql"

    def test_already_lower(self):
        assert _camel_to_snake("getissue") == "getissue"

    def test_all_caps_acronym(self):
        # e.g. "getJQL" → "get_j_q_l"  (per regex behaviour)
        result = _camel_to_snake("getJQL")
        assert result == result.lower()

    def test_leading_uppercase(self):
        assert _camel_to_snake("GetIssue") == "get_issue"

    def test_single_word(self):
        assert _camel_to_snake("issues") == "issues"

    def test_consecutive_capitals(self):
        # "getHTTPSResponse" → something all lowercase
        result = _camel_to_snake("getHTTPSResponse")
        assert result == result.lower()
        assert "_" in result

    def test_empty_string(self):
        assert _camel_to_snake("") == ""

    def test_numbers_preserved(self):
        result = _camel_to_snake("getIssueV2")
        assert "get" in result
        assert "2" in result


# ---------------------------------------------------------------------------
# _sanitize_tool_name
# ---------------------------------------------------------------------------


class TestSanitizeToolName:
    def test_basic_camel(self):
        assert _sanitize_tool_name("getIssue") == "get_issue"

    def test_hyphens_replaced(self):
        result = _sanitize_tool_name("get-issue")
        assert "-" not in result
        assert result.replace("_", "").isalnum()

    def test_spaces_replaced(self):
        result = _sanitize_tool_name("get issue")
        assert " " not in result

    def test_consecutive_underscores_collapsed(self):
        result = _sanitize_tool_name("get__issue")
        assert "__" not in result

    def test_leading_trailing_underscores_stripped(self):
        result = _sanitize_tool_name("_getIssue_")
        assert not result.startswith("_")
        assert not result.endswith("_")

    def test_max_64_chars(self):
        long_name = "getThisIsAVeryLongOperationIdThatExceedsSixtyFourCharactersInTotal"
        result = _sanitize_tool_name(long_name)
        assert len(result) <= 64

    def test_already_valid(self):
        assert _sanitize_tool_name("get_issue") == "get_issue"

    def test_only_valid_chars(self):
        result = _sanitize_tool_name("foo!bar@baz#123")
        assert all(c.isalnum() or c == "_" for c in result)


# ---------------------------------------------------------------------------
# _resolve_ref
# ---------------------------------------------------------------------------


class TestResolveRef:
    def _components(self):
        return {
            "schemas": {
                "IssueBean": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "string"},
                        "key": {"type": "string"},
                    },
                },
                "Nested": {
                    "type": "object",
                    "properties": {
                        "inner": {"$ref": "#/components/schemas/IssueBean"}
                    },
                },
            }
        }

    def test_resolves_schema_ref(self):
        components = self._components()
        result = _resolve_ref("#/components/schemas/IssueBean", components)
        assert result["type"] == "object"
        assert "id" in result["properties"]

    def test_unknown_ref_returns_empty(self):
        components = self._components()
        result = _resolve_ref("#/components/schemas/DoesNotExist", components)
        assert result == {}

    def test_partial_path_returns_empty(self):
        components = self._components()
        result = _resolve_ref("#/components/schemas/IssueBean/extraKey", components)
        assert result == {}

    def test_empty_components_returns_empty(self):
        result = _resolve_ref("#/components/schemas/IssueBean", {})
        assert result == {}

    def test_leading_hash_slash_stripped(self):
        components = self._components()
        result = _resolve_ref("#/components/schemas/IssueBean", components)
        assert result != {}


# ---------------------------------------------------------------------------
# _schema_to_json_schema
# ---------------------------------------------------------------------------


class TestSchemaToJsonSchema:
    def _empty_components(self):
        return {}

    def test_empty_schema_returns_string_type(self):
        result = _schema_to_json_schema({}, {})
        assert result == {"type": "string"}

    def test_integer_type(self):
        result = _schema_to_json_schema({"type": "integer"}, {})
        assert result["type"] == "integer"

    def test_boolean_type(self):
        result = _schema_to_json_schema({"type": "boolean"}, {})
        assert result["type"] == "boolean"

    def test_string_with_format(self):
        result = _schema_to_json_schema({"type": "string", "format": "date-time"}, {})
        assert result["type"] == "string"
        assert result["format"] == "date-time"

    def test_string_with_enum(self):
        result = _schema_to_json_schema({"type": "string", "enum": ["a", "b"]}, {})
        assert result["enum"] == ["a", "b"]

    def test_string_with_default(self):
        result = _schema_to_json_schema({"type": "string", "default": "hello"}, {})
        assert result["default"] == "hello"

    def test_string_with_description(self):
        result = _schema_to_json_schema({"type": "string", "description": "An id"}, {})
        assert result["description"] == "An id"

    def test_array_with_items(self):
        schema = {"type": "array", "items": {"type": "string"}}
        result = _schema_to_json_schema(schema, {})
        assert result["type"] == "array"
        assert result["items"] == {"type": "string"}

    def test_array_items_nested(self):
        schema = {"type": "array", "items": {"type": "integer", "format": "int64"}}
        result = _schema_to_json_schema(schema, {})
        assert result["items"]["type"] == "integer"
        assert result["items"]["format"] == "int64"

    def test_object_with_properties(self):
        schema = {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "age": {"type": "integer"},
            },
        }
        result = _schema_to_json_schema(schema, {})
        assert result["type"] == "object"
        assert "name" in result["properties"]
        assert "age" in result["properties"]

    def test_object_with_required(self):
        schema = {
            "type": "object",
            "properties": {"id": {"type": "string"}},
            "required": ["id"],
        }
        result = _schema_to_json_schema(schema, {})
        assert result["required"] == ["id"]

    def test_object_additional_properties_bool(self):
        schema = {"type": "object", "additionalProperties": False}
        result = _schema_to_json_schema(schema, {})
        assert result["additionalProperties"] is False

    def test_object_additional_properties_schema(self):
        schema = {
            "type": "object",
            "additionalProperties": {"type": "string"},
        }
        result = _schema_to_json_schema(schema, {})
        assert result["additionalProperties"] == {"type": "string"}

    def test_ref_is_resolved(self):
        components = {
            "schemas": {
                "MyType": {"type": "integer"}
            }
        }
        schema = {"$ref": "#/components/schemas/MyType"}
        result = _schema_to_json_schema(schema, components)
        assert result["type"] == "integer"

    def test_ref_depth_limit(self):
        # At depth >= 3, $ref should NOT be resolved; returns {"type": "string"}
        components = {
            "schemas": {
                "MyType": {"type": "integer"}
            }
        }
        schema = {"$ref": "#/components/schemas/MyType"}
        result = _schema_to_json_schema(schema, components, depth=3)
        # Should not recurse; fallback to {"type": "string"}
        assert result == {"type": "string"}

    def test_properties_depth_limit(self):
        # At depth >= 2, properties are NOT expanded (depth check in function)
        schema = {
            "type": "object",
            "properties": {"id": {"type": "string"}},
        }
        result = _schema_to_json_schema(schema, {}, depth=2)
        assert "properties" not in result

    def test_no_type_with_properties_infers_object(self):
        schema = {"properties": {"id": {"type": "string"}}}
        result = _schema_to_json_schema(schema, {})
        assert result.get("type") == "object"


# ---------------------------------------------------------------------------
# _build_input_schema
# ---------------------------------------------------------------------------


class TestBuildInputSchema:
    def test_no_params_no_body(self):
        schema = _build_input_schema([], None, {})
        assert schema["type"] == "object"
        assert schema["properties"] == {}
        assert "required" not in schema

    def test_single_query_param(self):
        params = [
            {
                "name": "projectKey",
                "in": "query",
                "required": True,
                "description": "The project key",
                "schema": {"type": "string"},
            }
        ]
        schema = _build_input_schema(params, None, {})
        assert "projectKey" in schema["properties"]
        assert schema["properties"]["projectKey"]["type"] == "string"
        assert schema["properties"]["projectKey"]["description"] == "The project key"
        assert "projectKey" in schema["required"]

    def test_optional_param_not_in_required(self):
        params = [
            {
                "name": "maxResults",
                "in": "query",
                "required": False,
                "schema": {"type": "integer"},
            }
        ]
        schema = _build_input_schema(params, None, {})
        assert "maxResults" in schema["properties"]
        assert "required" not in schema

    def test_path_param(self):
        params = [
            {
                "name": "issueIdOrKey",
                "in": "path",
                "required": True,
                "schema": {"type": "string"},
            }
        ]
        schema = _build_input_schema(params, None, {})
        assert "issueIdOrKey" in schema["properties"]
        assert "issueIdOrKey" in schema["required"]

    def test_multiple_params(self):
        params = [
            {"name": "a", "in": "query", "required": True, "schema": {"type": "string"}},
            {"name": "b", "in": "query", "required": False, "schema": {"type": "integer"}},
            {"name": "c", "in": "path", "required": True, "schema": {"type": "string"}},
        ]
        schema = _build_input_schema(params, None, {})
        assert set(schema["properties"].keys()) == {"a", "b", "c"}
        assert set(schema["required"]) == {"a", "c"}

    def test_request_body_added_as_body_property(self):
        request_body = {
            "required": True,
            "content": {
                "application/json": {
                    "schema": {"type": "object", "properties": {"name": {"type": "string"}}}
                }
            },
        }
        schema = _build_input_schema([], request_body, {})
        assert "body" in schema["properties"]
        assert "body" in schema["required"]

    def test_request_body_optional(self):
        request_body = {
            "required": False,
            "content": {
                "application/json": {
                    "schema": {"type": "object"}
                }
            },
        }
        schema = _build_input_schema([], request_body, {})
        assert "body" in schema["properties"]
        assert "required" not in schema

    def test_request_body_description_used(self):
        request_body = {
            "description": "Custom body description",
            "required": False,
            "content": {"application/json": {"schema": {"type": "object"}}},
        }
        schema = _build_input_schema([], request_body, {})
        assert schema["properties"]["body"]["description"] == "Custom body description"

    def test_request_body_fallback_description(self):
        request_body = {
            "required": False,
            "content": {"application/json": {"schema": {"type": "object"}}},
        }
        schema = _build_input_schema([], request_body, {})
        assert schema["properties"]["body"]["description"] == "Request body (JSON object)"

    def test_request_body_empty_schema_defaults_to_object(self):
        request_body = {
            "required": False,
            "content": {"application/json": {}},
        }
        schema = _build_input_schema([], request_body, {})
        assert schema["properties"]["body"]["type"] == "object"

    def test_param_with_ref_schema(self):
        components = {
            "schemas": {
                "IssueType": {"type": "string", "enum": ["bug", "task"]}
            }
        }
        params = [
            {
                "name": "issueType",
                "in": "query",
                "required": False,
                "schema": {"$ref": "#/components/schemas/IssueType"},
            }
        ]
        schema = _build_input_schema(params, None, components)
        prop = schema["properties"]["issueType"]
        assert prop["type"] == "string"
        assert prop["enum"] == ["bug", "task"]

    def test_param_without_description_uses_fallback(self):
        params = [{"name": "x", "in": "query", "schema": {"type": "string"}}]
        schema = _build_input_schema(params, None, {})
        assert "query" in schema["properties"]["x"]["description"]

    def test_octet_stream_body_accepted(self):
        request_body = {
            "required": True,
            "content": {
                "application/octet-stream": {"schema": {"type": "string", "format": "binary"}}
            },
        }
        schema = _build_input_schema([], request_body, {})
        assert "body" in schema["properties"]


# ---------------------------------------------------------------------------
# ToolRegistry
# ---------------------------------------------------------------------------


def _make_minimal_spec(paths: dict) -> dict:
    """Helper to create a minimal OpenAPI spec dict."""
    return {
        "openapi": "3.0.0",
        "info": {"title": "Test API", "version": "1.0.0"},
        "paths": paths,
        "components": {},
    }


def _write_spec(spec: dict) -> Path:
    """Write a spec dict to a temp file and return its Path."""
    tmp = tempfile.NamedTemporaryFile(
        mode="w", suffix=".json", delete=False, encoding="utf-8"
    )
    json.dump(spec, tmp)
    tmp.flush()
    return Path(tmp.name)


class TestToolRegistry:
    def test_empty_spec_produces_no_tools(self):
        spec = _make_minimal_spec({})
        path = _write_spec(spec)
        registry = ToolRegistry()
        registry.load_from_spec(path)
        assert registry.tools == []

    def test_single_get_operation(self):
        spec = _make_minimal_spec(
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
                            }
                        ],
                    }
                }
            }
        )
        path = _write_spec(spec)
        registry = ToolRegistry()
        registry.load_from_spec(path)
        assert len(registry.tools) == 1
        tool = registry.tools[0]
        assert tool.name == "get_issue"

    def test_operation_id_converted_to_snake_case(self):
        spec = _make_minimal_spec(
            {
                "/rest/api/3/search": {
                    "get": {
                        "operationId": "searchForIssuesUsingJql",
                        "summary": "Search issues",
                        "parameters": [],
                    }
                }
            }
        )
        path = _write_spec(spec)
        registry = ToolRegistry()
        registry.load_from_spec(path)
        assert registry.tools[0].name == "search_for_issues_using_jql"

    def test_multiple_methods_on_same_path(self):
        spec = _make_minimal_spec(
            {
                "/rest/api/3/issue": {
                    "get": {
                        "operationId": "getIssues",
                        "summary": "Get issues",
                        "parameters": [],
                    },
                    "post": {
                        "operationId": "createIssue",
                        "summary": "Create issue",
                        "parameters": [],
                        "requestBody": {
                            "required": True,
                            "content": {"application/json": {"schema": {"type": "object"}}},
                        },
                    },
                }
            }
        )
        path = _write_spec(spec)
        registry = ToolRegistry()
        registry.load_from_spec(path)
        names = {t.name for t in registry.tools}
        assert "get_issues" in names
        assert "create_issue" in names

    def test_duplicate_operation_ids_deduplicated(self):
        # Two operations resolving to same snake_case name
        spec = _make_minimal_spec(
            {
                "/a": {
                    "get": {
                        "operationId": "doThing",
                        "summary": "Do thing A",
                        "parameters": [],
                    }
                },
                "/b": {
                    "get": {
                        "operationId": "doThing",
                        "summary": "Do thing B",
                        "parameters": [],
                    }
                },
            }
        )
        path = _write_spec(spec)
        registry = ToolRegistry()
        registry.load_from_spec(path)
        assert len(registry.tools) == 2
        names = [t.name for t in registry.tools]
        assert len(set(names)) == 2  # both unique

    def test_missing_operation_id_generates_name(self):
        spec = _make_minimal_spec(
            {
                "/rest/api/3/banner": {
                    "get": {
                        "summary": "Get banner",
                        "parameters": [],
                    }
                }
            }
        )
        path = _write_spec(spec)
        registry = ToolRegistry()
        registry.load_from_spec(path)
        assert len(registry.tools) == 1
        assert registry.tools[0].name  # has some non-empty name

    def test_tool_description_uses_summary(self):
        spec = _make_minimal_spec(
            {
                "/x": {
                    "get": {
                        "operationId": "getX",
                        "summary": "Get the X resource",
                        "parameters": [],
                    }
                }
            }
        )
        path = _write_spec(spec)
        registry = ToolRegistry()
        registry.load_from_spec(path)
        assert registry.tools[0].description == "Get the X resource"

    def test_tool_description_combines_summary_and_description(self):
        spec = _make_minimal_spec(
            {
                "/x": {
                    "get": {
                        "operationId": "getX",
                        "summary": "Short title",
                        "description": "Longer explanation of the endpoint.",
                        "parameters": [],
                    }
                }
            }
        )
        path = _write_spec(spec)
        registry = ToolRegistry()
        registry.load_from_spec(path)
        desc = registry.tools[0].description
        assert "Short title" in desc
        assert "Longer explanation" in desc

    def test_tool_description_truncated_at_1024(self):
        long_desc = "x" * 2000
        spec = _make_minimal_spec(
            {
                "/x": {
                    "get": {
                        "operationId": "getX",
                        "summary": long_desc,
                        "parameters": [],
                    }
                }
            }
        )
        path = _write_spec(spec)
        registry = ToolRegistry()
        registry.load_from_spec(path)
        assert len(registry.tools[0].description) <= 1024

    def test_input_schema_has_path_params(self):
        spec = _make_minimal_spec(
            {
                "/rest/api/3/issue/{id}": {
                    "get": {
                        "operationId": "getIssueById",
                        "summary": "Get issue",
                        "parameters": [
                            {
                                "name": "id",
                                "in": "path",
                                "required": True,
                                "schema": {"type": "string"},
                            }
                        ],
                    }
                }
            }
        )
        path = _write_spec(spec)
        registry = ToolRegistry()
        registry.load_from_spec(path)
        schema = registry.tools[0].inputSchema
        assert "id" in schema["properties"]
        assert "id" in schema["required"]

    def test_input_schema_has_body_for_post(self):
        spec = _make_minimal_spec(
            {
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
                }
            }
        )
        path = _write_spec(spec)
        registry = ToolRegistry()
        registry.load_from_spec(path)
        schema = registry.tools[0].inputSchema
        assert "body" in schema["properties"]
        assert "body" in schema["required"]

    def test_path_level_params_merged(self):
        spec = _make_minimal_spec(
            {
                "/rest/api/3/project/{projectKey}/issue": {
                    "parameters": [
                        {
                            "name": "projectKey",
                            "in": "path",
                            "required": True,
                            "schema": {"type": "string"},
                        }
                    ],
                    "get": {
                        "operationId": "getProjectIssues",
                        "summary": "Get project issues",
                        "parameters": [
                            {
                                "name": "maxResults",
                                "in": "query",
                                "required": False,
                                "schema": {"type": "integer"},
                            }
                        ],
                    },
                }
            }
        )
        path = _write_spec(spec)
        registry = ToolRegistry()
        registry.load_from_spec(path)
        schema = registry.tools[0].inputSchema
        assert "projectKey" in schema["properties"]
        assert "maxResults" in schema["properties"]

    def test_dispatch_returns_correct_method_and_path(self):
        spec = _make_minimal_spec(
            {
                "/rest/api/3/issue/{issueIdOrKey}": {
                    "get": {
                        "operationId": "getIssue",
                        "summary": "Get issue",
                        "parameters": [],
                    }
                }
            }
        )
        path = _write_spec(spec)
        registry = ToolRegistry()
        registry.load_from_spec(path)
        dispatch = registry.get_dispatch("get_issue")
        assert dispatch is not None
        method, api_path, params, has_body = dispatch
        assert method == "GET"
        assert api_path == "/rest/api/3/issue/{issueIdOrKey}"
        assert has_body is False

    def test_dispatch_has_body_true_for_post(self):
        spec = _make_minimal_spec(
            {
                "/rest/api/3/issue": {
                    "post": {
                        "operationId": "createIssue",
                        "summary": "Create issue",
                        "parameters": [],
                        "requestBody": {
                            "required": True,
                            "content": {"application/json": {"schema": {"type": "object"}}},
                        },
                    }
                }
            }
        )
        path = _write_spec(spec)
        registry = ToolRegistry()
        registry.load_from_spec(path)
        dispatch = registry.get_dispatch("create_issue")
        assert dispatch is not None
        _, _, _, has_body = dispatch
        assert has_body is True

    def test_get_dispatch_unknown_returns_none(self):
        registry = ToolRegistry()
        assert registry.get_dispatch("nonexistent_tool") is None

    def test_all_methods_registered(self):
        spec = _make_minimal_spec(
            {
                "/x": {
                    "get": {"operationId": "getX", "summary": "G", "parameters": []},
                    "post": {"operationId": "postX", "summary": "P", "parameters": []},
                    "put": {"operationId": "putX", "summary": "U", "parameters": []},
                    "delete": {"operationId": "deleteX", "summary": "D", "parameters": []},
                    "patch": {"operationId": "patchX", "summary": "PA", "parameters": []},
                }
            }
        )
        path = _write_spec(spec)
        registry = ToolRegistry()
        registry.load_from_spec(path)
        assert len(registry.tools) == 5
        methods = {registry.get_dispatch(t.name)[0] for t in registry.tools}
        assert methods == {"GET", "POST", "PUT", "DELETE", "PATCH"}

    def test_tool_name_max_64_chars(self):
        long_id = "a" * 100
        spec = _make_minimal_spec(
            {"/x": {"get": {"operationId": long_id, "summary": "X", "parameters": []}}}
        )
        path = _write_spec(spec)
        registry = ToolRegistry()
        registry.load_from_spec(path)
        assert len(registry.tools[0].name) <= 64

    def test_tools_property_returns_list(self):
        registry = ToolRegistry()
        assert isinstance(registry.tools, list)

    def test_load_real_jira_spec(self):
        """Smoke test: the actual Jira spec loads without errors."""
        real_spec = (
            Path(__file__).parent.parent
            / "Building MCP with LLMs"
            / "jira-swagger-v3.v3.json"
        )
        if not real_spec.exists():
            pytest.skip("Real Jira spec not found")
        registry = ToolRegistry()
        registry.load_from_spec(real_spec)
        assert len(registry.tools) > 400
        names = [t.name for t in registry.tools]
        assert len(set(names)) == len(names)  # all unique
        assert "get_issue" in names
        assert "create_issue" in names
        assert "search_for_issues_using_jql" in names
