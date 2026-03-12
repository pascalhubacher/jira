# Jira Cloud MCP Server

A [Model Context Protocol (MCP)](https://modelcontextprotocol.io) server that exposes the **Jira Cloud REST API v3** to any MCP-compatible AI assistant. The server exposes a curated set of **62 tools** covering the full lifecycle of stories, epics, bugs, and sprints — including search, create/edit/delete, transitions, comments, worklogs, issue links, watchers, bulk operations, changelogs, and more.

> **Note:** The full Jira OpenAPI spec contains 619 operations. Most MCP clients (including Claude Code) enforce a tool limit that prevents registering that many tools. The server therefore uses an allowlist to expose only the most useful operations. You can extend the allowlist in [`src/jira_mcp/tools.py`](src/jira_mcp/tools.py) if needed.

---

## Table of Contents

- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Configuration](#configuration)
- [Running the Server](#running-the-server)
- [Adding to Your AI Tool](#adding-to-your-ai-tool)
  - [Claude Code](#claude-code)
  - [Claude Desktop](#claude-desktop)
  - [Gemini CLI](#gemini-cli)
  - [OpenCode](#opencode)
  - [GitHub Copilot (VS Code)](#github-copilot-vs-code)
- [Tool Allowlist](#tool-allowlist)
- [Functionality Reference](#functionality-reference)
  - [Issues](#issues)
  - [Issue Search](#issue-search)
  - [Issue Comments](#issue-comments)
  - [Issue Worklogs](#issue-worklogs)
  - [Issue Attachments](#issue-attachments)
  - [Issue Links](#issue-links)
  - [Issue Remote Links](#issue-remote-links)
  - [Issue Votes & Watchers](#issue-votes--watchers)
  - [Issue Bulk Operations](#issue-bulk-operations)
  - [Issue Transitions](#issue-transitions)
  - [Issue Properties](#issue-properties)
  - [Projects](#projects)
  - [Project Components](#project-components)
  - [Project Versions](#project-versions)
  - [Project Roles & Actors](#project-roles--actors)
  - [Project Properties](#project-properties)
  - [Project Avatars](#project-avatars)
  - [Project Categories](#project-categories)
  - [Project Types](#project-types)
  - [Project Templates](#project-templates)
  - [Project Email & Features](#project-email--features)
  - [Project Classification Levels](#project-classification-levels)
  - [Project Permission Schemes](#project-permission-schemes)
  - [Workflows](#workflows)
  - [Workflow Schemes](#workflow-schemes)
  - [Workflow Scheme Drafts](#workflow-scheme-drafts)
  - [Workflow Status Categories](#workflow-status-categories)
  - [Workflow Statuses](#workflow-statuses)
  - [Workflow Transition Rules & Properties](#workflow-transition-rules--properties)
  - [Filters](#filters)
  - [Filter Sharing](#filter-sharing)
  - [Dashboards](#dashboards)
  - [Users](#users)
  - [User Search](#user-search)
  - [User Properties](#user-properties)
  - [Groups](#groups)
  - [Permissions & Permission Schemes](#permissions--permission-schemes)
  - [Issue Types](#issue-types)
  - [Issue Type Schemes](#issue-type-schemes)
  - [Issue Type Screen Schemes](#issue-type-screen-schemes)
  - [Issue Priorities](#issue-priorities)
  - [Priority Schemes](#priority-schemes)
  - [Issue Resolutions](#issue-resolutions)
  - [Issue Fields](#issue-fields)
  - [Issue Field Configurations](#issue-field-configurations)
  - [Field Schemes](#field-schemes)
  - [Issue Custom Field Contexts](#issue-custom-field-contexts)
  - [Issue Custom Field Options](#issue-custom-field-options)
  - [Issue Custom Field Values](#issue-custom-field-values)
  - [Issue Custom Field Configurations (Apps)](#issue-custom-field-configurations-apps)
  - [Issue Custom Field Options (Apps)](#issue-custom-field-options-apps)
  - [Issue Custom Field Associations](#issue-custom-field-associations)
  - [Screens](#screens)
  - [Screen Tabs & Fields](#screen-tabs--fields)
  - [Screen Schemes](#screen-schemes)
  - [Status](#status)
  - [JQL](#jql)
  - [Jira Expressions](#jira-expressions)
  - [Avatars](#avatars)
  - [Audit Records](#audit-records)
  - [Webhooks](#webhooks)
  - [Myself](#myself)
  - [Server Info & Jira Settings](#server-info--jira-settings)
  - [Time Tracking](#time-tracking)
  - [Labels](#labels)
  - [Plans & Teams in Plan](#plans--teams-in-plan)
  - [License Metrics](#license-metrics)
  - [Issue Security Schemes & Levels](#issue-security-schemes--levels)
  - [Issue Notification Schemes](#issue-notification-schemes)
  - [Issue Link Types](#issue-link-types)
  - [Issue Navigator Settings](#issue-navigator-settings)
  - [Application Roles](#application-roles)
  - [Announcement Banner](#announcement-banner)
  - [Tasks](#tasks)
  - [App Properties & Dynamic Modules](#app-properties--dynamic-modules)
  - [Webhooks (Dynamic)](#webhooks-dynamic)
  - [Classification Levels](#classification-levels)
- [Authentication](#authentication)
- [Security](#security)
- [Troubleshooting](#troubleshooting)

---

## Prerequisites

- **Python 3.11+**
- **uv** package manager
- A **Jira Cloud** account with API access
- A Jira **API token** (see [Authentication](#authentication))

---

## Installation

### 1. Install uv (if not already installed)

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
source ~/.bashrc   # or restart your terminal
```

### 2. Clone the repository

```bash
git clone https://github.com/yourorg/jira-mcp.git
cd jira-mcp
```

### 3. Install dependencies

```bash
uv sync
```

This creates a virtual environment in `.venv/` and installs all required packages automatically.

---

## Configuration

Copy the example environment file and fill in your credentials:

```bash
cp .env.example .env
```

Edit `.env`:

```env
# Your Jira Cloud instance URL (no trailing slash)
JIRA_BASE_URL=https://yourcompany.atlassian.net

# Email address associated with your Jira account
JIRA_EMAIL=you@example.com

# Jira API token
# Generate one at: https://id.atlassian.com/manage-profile/security/api-tokens
JIRA_API_TOKEN=your_api_token_here

# Optional: max tool calls per second (default: 10)
# JIRA_MCP_RATE_LIMIT=10
```

### Generating a Jira API Token

1. Log in to [Atlassian Account Settings](https://id.atlassian.com/manage-profile/security/api-tokens)
2. Click **Create API token**
3. Give it a label (e.g. `jira-mcp`)
4. Copy the token and paste it into `.env`

> **Security note:** Never commit your `.env` file. It is already in `.gitignore`.

---

## Running the Server

The server uses **stdio transport** (standard input/output), which is the standard for MCP servers used by desktop and CLI tools.

```bash
uv run jira-mcp
```

The server will start and wait for MCP messages on stdin/stdout. You don't run it directly — your AI tool launches it automatically based on your configuration.

---

## Adding to Your AI Tool

### Claude Code

Add the server to Claude Code using the `claude mcp add` command:

```bash
claude mcp add jira \
  --env JIRA_BASE_URL=https://yourcompany.atlassian.net \
  --env JIRA_EMAIL=you@example.com \
  --env JIRA_API_TOKEN=your_api_token_here \
  -- uv --directory /absolute/path/to/jira-mcp run jira-mcp
```

Or add it manually to your Claude Code MCP config file (`~/.claude/claude_code_config.json` or via `claude mcp edit`):

```json
{
  "mcpServers": {
    "jira": {
      "command": "uv",
      "args": ["--directory", "/absolute/path/to/jira-mcp", "run", "jira-mcp"],
      "env": {
        "JIRA_BASE_URL": "https://yourcompany.atlassian.net",
        "JIRA_EMAIL": "you@example.com",
        "JIRA_API_TOKEN": "your_api_token_here"
      }
    }
  }
}
```

Verify it's loaded:

```bash
claude mcp list
```

---

### Claude Desktop

Edit your Claude Desktop config file:

- **macOS:** `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Windows:** `%APPDATA%\Claude\claude_desktop_config.json`
- **Linux:** `~/.config/Claude/claude_desktop_config.json`

```json
{
  "mcpServers": {
    "jira": {
      "command": "uv",
      "args": ["--directory", "/absolute/path/to/jira-mcp", "run", "jira-mcp"],
      "env": {
        "JIRA_BASE_URL": "https://yourcompany.atlassian.net",
        "JIRA_EMAIL": "you@example.com",
        "JIRA_API_TOKEN": "your_api_token_here"
      }
    }
  }
}
```

Restart Claude Desktop after editing the config. You should see a hammer icon in the chat indicating tools are available.

---

### Gemini CLI

Gemini CLI supports MCP servers via its configuration file. Edit `~/.gemini/settings.json`:

```json
{
  "mcpServers": {
    "jira": {
      "command": "uv",
      "args": ["--directory", "/absolute/path/to/jira-mcp", "run", "jira-mcp"],
      "env": {
        "JIRA_BASE_URL": "https://yourcompany.atlassian.net",
        "JIRA_EMAIL": "you@example.com",
        "JIRA_API_TOKEN": "your_api_token_here"
      }
    }
  }
}
```

Restart Gemini CLI after updating the config. You can verify the tools are available by asking:
> "What Jira tools do you have access to?"

---

### OpenCode

Edit your OpenCode configuration file (`~/.config/opencode/config.json` or the project-level `.opencode/config.json`):

```json
{
  "mcp": {
    "servers": {
      "jira": {
        "type": "local",
        "command": ["uv", "--directory", "/absolute/path/to/jira-mcp", "run", "jira-mcp"],
        "env": {
          "JIRA_BASE_URL": "https://yourcompany.atlassian.net",
          "JIRA_EMAIL": "you@example.com",
          "JIRA_API_TOKEN": "your_api_token_here"
        }
      }
    }
  }
}
```

---

### GitHub Copilot (VS Code)

VS Code with the GitHub Copilot extension supports MCP servers. Edit your VS Code `settings.json`:

```json
{
  "github.copilot.chat.mcp.servers": {
    "jira": {
      "command": "uv",
      "args": ["--directory", "/absolute/path/to/jira-mcp", "run", "jira-mcp"],
      "env": {
        "JIRA_BASE_URL": "https://yourcompany.atlassian.net",
        "JIRA_EMAIL": "you@example.com",
        "JIRA_API_TOKEN": "your_api_token_here"
      }
    }
  }
}
```

After saving, reload VS Code. In Copilot Chat, switch to **Agent mode** to access the Jira tools.

---

## Tool Allowlist

Most MCP clients enforce a hard limit on the number of tools a server may register. Claude Code, for example, will silently drop the server if it advertises too many tools. Because the Jira OpenAPI spec contains **619 operations**, the server filters them down to a practical allowlist defined in [`src/jira_mcp/tools.py`](src/jira_mcp/tools.py) (`_ALLOWED_OPERATION_IDS`).

### Currently enabled tools (62)

| Tool name (snake_case) | Purpose |
|---|---|
| `search_and_reconsile_issues_using_jql_post` | Search issues via JQL (POST, supports large queries) |
| `get_issue` | Retrieve a single issue by key or ID |
| `bulk_fetch_issues` | Fetch multiple issues by key or ID in one request |
| `create_issue` | Create a new issue (story, bug, epic, task, etc.) |
| `create_issues` | Bulk-create multiple issues in one request |
| `edit_issue` | Update fields on an existing issue |
| `delete_issue` | Delete an issue |
| `assign_issue` | Assign or unassign an issue to a user |
| `get_transitions` | List available workflow transitions for an issue |
| `do_transition` | Move an issue to a new status via a workflow transition |
| `submit_bulk_edit` | Edit multiple issues simultaneously |
| `submit_bulk_delete` | Delete multiple issues at once |
| `submit_bulk_move` | Move issues between projects |
| `submit_bulk_transition` | Transition multiple issues to a new status |
| `get_comments` | List comments on an issue |
| `get_comment` | Retrieve a single comment |
| `add_comment` | Add a comment to an issue |
| `update_comment` | Edit a comment |
| `delete_comment` | Delete a comment |
| `link_issues` | Link two issues (blocks, duplicates, relates to, etc.) |
| `get_issue_link` | Get an issue link by ID |
| `get_issue_link_types` | List all available link types |
| `delete_issue_link` | Remove a link between issues |
| `get_remote_issue_links` | List all remote links on an issue |
| `create_or_update_remote_issue_link` | Create or update a remote link (e.g. Confluence page) |
| `get_remote_issue_link_by_id` | Get a specific remote link |
| `delete_remote_issue_link_by_id` | Delete a remote link by ID |
| `get_issue_worklog` | List all worklogs on an issue |
| `add_worklog` | Log time spent on an issue |
| `get_worklog` | Get a specific worklog entry |
| `update_worklog` | Update a worklog entry |
| `delete_worklog` | Delete a worklog entry |
| `get_issue_watchers` | Get all users watching an issue |
| `add_watcher` | Add a user as a watcher |
| `remove_watcher` | Remove a watcher |
| `get_votes` | Get voters for an issue |
| `add_vote` | Vote for an issue |
| `remove_vote` | Remove your vote |
| `get_change_logs` | Get the full history of changes for an issue |
| `get_change_logs_by_ids` | Fetch changelogs for specific IDs |
| `get_issue_property` | Get a custom property value on an issue |
| `set_issue_property` | Set a custom property on an issue |
| `delete_issue_property` | Delete an issue property |
| `add_attachment` | Upload a file attachment to an issue |
| `get_attachment` | Retrieve attachment metadata |
| `get_all_projects` | List all visible projects |
| `search_projects` | Search/filter projects |
| `get_project` | Retrieve a single project |
| `get_project_versions` | List all versions (releases) in a project |
| `create_version` | Create a project version |
| `get_project_components` | List all components in a project |
| `create_component` | Create a project component |
| `get_user` | Retrieve a user by account ID |
| `find_users` | Find users by display name or email |
| `find_users_assignable_to_issues` | Find users assignable to a specific issue |
| `find_bulk_assignable_users` | Find assignable users across multiple projects |
| `get_create_issue_meta` | Get fields available when creating an issue |
| `get_edit_issue_meta` | Get fields available when editing an issue |
| `get_fields` | List all fields (system + custom) |
| `get_issue_types_for_project` | List issue types available in a project |
| `get_priorities` | List all issue priorities |
| `get_statuses` | List all issue statuses |
| `get_all_labels` | List all labels used across Jira |
| `get_issues_for_sprint` | List issues in a sprint |
| `get_all_sprints` | List all sprints for a board |
| `get_board` | Get a Jira Software board by ID |
| `get_all_boards` | List all Jira Software boards |

### Adding more tools

To expose additional Jira API operations, add their `operationId` (from the OpenAPI spec) to `_ALLOWED_OPERATION_IDS` in [`src/jira_mcp/tools.py`](src/jira_mcp/tools.py):

```python
_ALLOWED_OPERATION_IDS: frozenset[str] = frozenset({
    ...
    "getWorkflowTransitionProperties",   # example: expose workflow transition properties
})
```

Restart the MCP server after any change. Keep the total well below your client's tool limit (Claude Code: ~128 tools).

---

## Functionality Reference

This section documents the full Jira Cloud REST API v3. Operations not in the whitelist are still listed here for reference — add their `operationId` to `_ALLOWED_OPERATION_IDS` to enable them.

---

### Issues

The core of Jira — full CRUD and lifecycle management for issues.

| Tool | Description |
|------|-------------|
| `get_issue` | Get a single issue by ID or key, with optional field filtering |
| `create_issue` | Create a new issue in any project |
| `edit_issue` | Update issue fields (summary, description, assignee, status, etc.) |
| `delete_issue` | Permanently delete an issue |
| `assign_issue` | Assign or unassign an issue to a user |
| `bulk_create_issue` | Create multiple issues in a single request |
| `bulk_fetch_issues` | Fetch multiple issues by ID or key |
| `get_create_issue_metadata` | Get required fields and allowed values for issue creation |
| `get_create_metadata_issue_types_for_a_project` | Get issue type metadata for a project |
| `get_create_field_metadata_for_a_project_and_issue_type_id` | Get field metadata for a specific project/issue type |
| `get_edit_issue_metadata` | Get editable fields and their allowed values for an issue |
| `get_changelogs` | Get the full history of changes for an issue |
| `get_changelogs_by_i_ds` | Fetch changelogs for specific IDs |
| `bulk_fetch_changelogs` | Bulk-fetch changelogs across multiple issues |
| `get_transitions` | Get available workflow transitions for an issue |
| `transition_issue` | Move an issue to a new status via a workflow transition |
| `send_notification_for_issue` | Send an email notification about an issue |
| `get_events` | Get all Jira event types |
| `archive_issue_s_by_jql` | Archive issues matching a JQL query |
| `archive_issue_s_by_issue_id_key` | Archive issues by ID or key |
| `unarchive_issue_s_by_issue_keys_id` | Unarchive issues |
| `export_archived_issue_s` | Export archived issues |
| `get_issue_limit_report` | Get report on issues approaching field limits |

---

### Issue Search

Find issues using Jira Query Language (JQL).

| Tool | Description |
|------|-------------|
| `search_for_issues_using_jql_enhanced_search` | Search using JQL with enhanced pagination (GET) |
| `search_for_issues_using_jql_enhanced_search_post` | Search using JQL with enhanced pagination (POST, for long JQL) |
| `count_issues_using_jql` | Count total issues matching a JQL filter |
| `check_issues_against_jql` | Validate whether issues match a JQL query |
| `get_issue_picker_suggestions` | Autocomplete suggestions for the issue picker |

---

### Issue Comments

| Tool | Description |
|------|-------------|
| `get_comments` | List all comments on an issue |
| `add_comment` | Add a new comment to an issue |
| `get_comment` | Get a specific comment by ID |
| `update_comment` | Update the text of an existing comment |
| `delete_comment` | Delete a comment |
| `get_comments_by_i_ds` | Fetch multiple comments by their IDs |

---

### Issue Worklogs

| Tool | Description |
|------|-------------|
| `get_issue_worklogs` | List all worklogs on an issue |
| `add_worklog` | Log time spent on an issue |
| `get_worklog` | Get a specific worklog entry |
| `update_worklog` | Update a worklog entry |
| `delete_worklog` | Delete a worklog entry |
| `bulk_delete_worklogs` | Delete multiple worklogs at once |
| `bulk_move_worklogs` | Move worklogs to a different issue |
| `get_worklogs` | Fetch worklogs by their IDs |
| `get_i_ds_of_deleted_worklogs` | Get IDs of worklogs deleted since a timestamp |
| `get_i_ds_of_updated_worklogs` | Get IDs of worklogs updated since a timestamp |

---

### Issue Attachments

| Tool | Description |
|------|-------------|
| `add_attachment` | Upload a file attachment to an issue |
| `get_attachment_metadata` | Get metadata for an attachment |
| `delete_attachment` | Delete an attachment |
| `get_attachment_content` | Download attachment content |
| `get_attachment_thumbnail` | Get attachment thumbnail image |
| `get_all_metadata_for_an_expanded_attachment` | Get archive contents metadata |
| `get_contents_metadata_for_an_expanded_attachment` | Get individual archive entry metadata |
| `get_jira_attachment_settings` | Get global attachment settings (size limits, enabled state) |

---

### Issue Links

| Tool | Description |
|------|-------------|
| `create_issue_link` | Link two issues together (blocks, duplicates, relates to, etc.) |
| `get_issue_link` | Get an issue link by ID |
| `delete_issue_link` | Remove a link between issues |

---

### Issue Remote Links

Link issues to external resources (URLs, Confluence pages, etc.).

| Tool | Description |
|------|-------------|
| `get_remote_issue_links` | List all remote links on an issue |
| `create_or_update_remote_issue_link` | Create or update a remote link |
| `delete_remote_issue_link_by_global_id` | Delete a remote link by its global ID |
| `get_remote_issue_link_by_id` | Get a specific remote link |
| `update_remote_issue_link_by_id` | Update a remote link |
| `delete_remote_issue_link_by_id` | Delete a remote link by ID |

---

### Issue Votes & Watchers

| Tool | Description |
|------|-------------|
| `get_votes` | Get the number of votes and voters for an issue |
| `add_vote` | Vote for an issue |
| `delete_vote` | Remove your vote from an issue |
| `get_issue_watchers` | Get all users watching an issue |
| `add_watcher` | Add a user as a watcher |
| `delete_watcher` | Remove a watcher from an issue |
| `get_is_watching_issue_bulk` | Check if the current user watches multiple issues |

---

### Issue Bulk Operations

| Tool | Description |
|------|-------------|
| `bulk_edit_issues` | Edit multiple issues simultaneously |
| `bulk_delete_issues` | Delete multiple issues at once |
| `bulk_move_issues` | Move issues between projects |
| `bulk_transition_issue_statuses` | Transition multiple issues to a new status |
| `bulk_watch_issues` | Watch multiple issues at once |
| `bulk_unwatch_issues` | Stop watching multiple issues at once |
| `get_bulk_editable_fields` | Get fields editable in a bulk operation |
| `get_available_transitions` | Get available transitions for a bulk move |
| `get_bulk_issue_operation_progress` | Poll the progress of a running bulk operation |

---

### Issue Properties

Key-value metadata attached to issues (for use by apps and integrations).

| Tool | Description |
|------|-------------|
| `get_issue_property_keys` | List all property keys on an issue |
| `get_issue_property` | Get a single issue property value |
| `set_issue_property` | Set an issue property |
| `delete_issue_property` | Delete an issue property |
| `bulk_set_issues_properties_by_list` | Set a property on multiple issues |
| `bulk_set_issue_properties_by_issue` | Set multiple properties on a single issue |
| `bulk_set_issue_property` | Bulk-set a property across many issues |
| `bulk_delete_issue_property` | Bulk-delete a property from many issues |

---

### Projects

| Tool | Description |
|------|-------------|
| `get_all_projects` | List all projects (simple, for dropdowns) |
| `create_project` | Create a new Jira project |
| `get_projects_paginated` | Search and page through projects |
| `get_recent_projects` | Get recently viewed projects |
| `get_project` | Get a project by ID or key |
| `update_project` | Update project settings (name, lead, category, etc.) |
| `delete_project` | Delete a project |
| `archive_project` | Archive a project |
| `restore_deleted_or_archived_project` | Restore an archived or deleted project |
| `delete_project_asynchronously` | Delete a project in the background |
| `get_all_statuses_for_project` | Get all available statuses for a project |
| `get_project_issue_type_hierarchy` | Get the issue type hierarchy for a project |
| `get_project_notification_scheme` | Get the notification scheme assigned to a project |

---

### Project Components

| Tool | Description |
|------|-------------|
| `create_component` | Create a project component |
| `get_component` | Get a component by ID |
| `update_component` | Update a component |
| `delete_component` | Delete a component |
| `get_component_issues_count` | Get count of issues in a component |
| `get_project_components` | List all components in a project |
| `get_project_components_paginated` | Page through project components |
| `find_components_for_projects` | Find components across projects |

---

### Project Versions

Manage fix versions and release milestones.

| Tool | Description |
|------|-------------|
| `create_version` | Create a project version (release) |
| `get_version` | Get a version by ID |
| `update_version` | Update version details |
| `delete_version` | Delete a version |
| `get_project_versions` | List all versions in a project |
| `get_project_versions_paginated` | Page through project versions |
| `merge_versions` | Merge two versions |
| `move_version` | Reorder a version |
| `delete_and_replace_version` | Delete a version and remap issues to another |
| `get_version_s_related_issues_count` | Get issue counts by status for a version |
| `get_version_s_unresolved_issues_count` | Get count of unresolved issues in a version |
| `get_related_work` | Get related work items linked to a version |
| `create_related_work` | Add a related work link to a version |
| `update_related_work` | Update a related work link |
| `delete_related_work` | Remove a related work link |

---

### Project Roles & Actors

| Tool | Description |
|------|-------------|
| `get_project_roles_for_project` | List all roles in a project |
| `get_project_role_for_project` | Get a specific role in a project |
| `get_all_project_roles` | List all roles defined globally |
| `create_project_role` | Create a new project role |
| `get_project_role_by_id` | Get a project role by ID |
| `fully_update_project_role` | Fully replace a project role definition |
| `partial_update_project_role` | Partially update a project role |
| `delete_project_role` | Delete a project role |
| `get_project_role_details` | Get role details including actor information |
| `add_actors_to_project_role` | Add users or groups to a project role |
| `set_actors_for_project_role` | Replace all actors in a project role |
| `delete_actors_from_project_role` | Remove actors from a project role |
| `get_default_actors_for_project_role` | Get default actors for a global role |
| `add_default_actors_to_project_role` | Add default actors to a global role |
| `delete_default_actors_from_project_role` | Remove default actors from a global role |

---

### Project Properties

| Tool | Description |
|------|-------------|
| `get_project_property_keys` | List property keys for a project |
| `get_project_property` | Get a project property value |
| `set_project_property` | Set a project property |
| `delete_project_property` | Delete a project property |

---

### Project Avatars

| Tool | Description |
|------|-------------|
| `get_all_project_avatars` | Get all avatars for a project |
| `load_project_avatar` | Upload a custom project avatar |
| `set_project_avatar` | Set the active avatar for a project |
| `delete_project_avatar` | Delete a custom project avatar |

---

### Project Categories

| Tool | Description |
|------|-------------|
| `get_all_project_categories` | List all project categories |
| `create_project_category` | Create a new project category |
| `get_project_category_by_id` | Get a category by ID |
| `update_project_category` | Update a project category |
| `delete_project_category` | Delete a project category |

---

### Project Types

| Tool | Description |
|------|-------------|
| `get_all_project_types` | List all available project types |
| `get_licensed_project_types` | List project types available for your license |
| `get_project_type_by_key` | Get a project type by key |
| `get_accessible_project_type_by_key` | Get an accessible project type by key |

---

### Project Templates

| Tool | Description |
|------|-------------|
| `create_custom_project` | Create a project from a custom template |
| `save_a_custom_project_template` | Save a project configuration as a template |
| `gets_a_custom_project_template` | Retrieve a saved project template |
| `edit_a_custom_project_template` | Update a project template |
| `deletes_a_custom_project_template` | Delete a project template |

---

### Project Email & Features

| Tool | Description |
|------|-------------|
| `get_project_s_sender_email` | Get the sender email for a project |
| `set_project_s_sender_email` | Set the sender email for a project |
| `get_project_features` | List features enabled on a project |
| `set_project_feature_state` | Enable or disable a project feature |

---

### Project Classification Levels

| Tool | Description |
|------|-------------|
| `get_the_classification_configuration_for_a_project` | Get classification settings for a project |
| `get_the_default_data_classification_level_of_a_project` | Get the default classification level |
| `update_the_default_data_classification_level_of_a_project` | Set the default classification level |
| `remove_the_default_data_classification_level_from_a_project` | Remove the default classification level |

---

### Project Permission Schemes

| Tool | Description |
|------|-------------|
| `get_assigned_permission_scheme` | Get the permission scheme assigned to a project |
| `assign_permission_scheme` | Assign a permission scheme to a project |
| `get_project_issue_security_scheme` | Get the security scheme for a project |
| `get_project_issue_security_levels` | Get the security levels available in a project |

---

### Workflows

| Tool | Description |
|------|-------------|
| `get_all_workflows` | List all workflows |
| `create_workflow` | Create a new workflow |
| `get_workflows_paginated` | Search and page through workflows |
| `delete_inactive_workflow` | Delete a workflow that is not in use |
| `bulk_get_workflows` | Fetch multiple workflows by ID |
| `bulk_create_workflows` | Create multiple workflows in one request |
| `bulk_update_workflows` | Update multiple workflows at once |
| `validate_create_workflows` | Validate workflow definitions before creating |
| `validate_update_workflows` | Validate workflow changes before applying |
| `get_available_workflow_capabilities` | Get all available workflow rules and conditions |
| `preview_workflow` | Preview what a workflow will look like |
| `search_workflows` | Search workflows by name or other criteria |
| `get_projects_using_a_given_workflow` | List projects using a specific workflow |
| `get_workflow_schemes_which_are_using_a_given_workflow` | List schemes using a workflow |
| `get_issue_types_in_a_project_that_are_using_a_given_workflow` | Get issue types linked to a workflow |
| `read_workflow_version_from_history` | Retrieve a past version of a workflow |
| `list_workflow_history_entries` | Get the change history of a workflow |
| `get_the_user_s_default_workflow_editor` | Get the user's preferred workflow editor |

---

### Workflow Schemes

| Tool | Description |
|------|-------------|
| `get_all_workflow_schemes` | List all workflow schemes |
| `create_workflow_scheme` | Create a new workflow scheme |
| `bulk_get_workflow_schemes` | Fetch multiple workflow schemes by ID |
| `update_workflow_scheme` | Update a workflow scheme (modern API) |
| `classic_update_workflow_scheme` | Update a workflow scheme (classic API) |
| `delete_workflow_scheme` | Delete a workflow scheme |
| `switch_workflow_scheme_for_project` | Change the active workflow scheme for a project |
| `get_workflow_scheme` | Get a workflow scheme by ID |
| `get_default_workflow` | Get the default workflow for a scheme |
| `update_default_workflow` | Set the default workflow for a scheme |
| `delete_default_workflow` | Remove the default workflow from a scheme |
| `get_workflow_for_issue_type_in_workflow_scheme` | Get the workflow assigned to an issue type |
| `set_workflow_for_issue_type_in_workflow_scheme` | Assign a workflow to an issue type |
| `delete_workflow_for_issue_type_in_workflow_scheme` | Remove a workflow-to-issue-type mapping |
| `get_issue_types_for_workflows_in_workflow_scheme` | List issue type-to-workflow mappings |
| `set_issue_types_for_workflow_in_workflow_scheme` | Set issue type mappings for a workflow |
| `delete_issue_types_for_workflow_in_workflow_scheme` | Remove issue type mappings from a workflow |
| `get_projects_which_are_using_a_given_workflow_scheme` | List projects using a workflow scheme |
| `get_required_status_mappings_for_workflow_scheme_update` | Get required status mappings before updating |
| `get_workflow_scheme_project_associations` | Get project-to-scheme associations |
| `assign_workflow_scheme_to_project` | Assign a workflow scheme to a project |

---

### Workflow Scheme Drafts

Manage draft versions of workflow schemes before publishing.

| Tool | Description |
|------|-------------|
| `create_draft_workflow_scheme` | Create a draft of a workflow scheme |
| `get_draft_workflow_scheme` | Get the draft of a workflow scheme |
| `update_draft_workflow_scheme` | Update the draft |
| `delete_draft_workflow_scheme` | Discard the draft |
| `publish_draft_workflow_scheme` | Publish the draft (replaces the live scheme) |
| `get_draft_default_workflow` | Get the default workflow in the draft |
| `update_draft_default_workflow` | Change the default workflow in the draft |
| `delete_draft_default_workflow` | Remove the default workflow from the draft |
| `get_workflow_for_issue_type_in_draft_workflow_scheme` | Get workflow mapping in draft |
| `set_workflow_for_issue_type_in_draft_workflow_scheme` | Set workflow mapping in draft |
| `delete_workflow_for_issue_type_in_draft_workflow_scheme` | Remove mapping from draft |
| `get_issue_types_for_workflows_in_draft_workflow_scheme` | Get all draft mappings |
| `set_issue_types_for_workflow_in_workflow_scheme_1` | Set issue type mappings in draft |
| `delete_issue_types_for_workflow_in_draft_workflow_scheme` | Delete issue type mappings in draft |

---

### Workflow Status Categories

| Tool | Description |
|------|-------------|
| `get_all_status_categories` | List all status categories (To Do, In Progress, Done) |
| `get_status_category` | Get a status category by ID |

---

### Workflow Statuses

| Tool | Description |
|------|-------------|
| `get_all_statuses` | List all issue statuses |
| `get_status` | Get a specific status by ID |

---

### Workflow Transition Rules & Properties

| Tool | Description |
|------|-------------|
| `get_workflow_transition_rule_configurations` | Get validator/condition rules for transitions |
| `update_workflow_transition_rule_configurations` | Update transition rules |
| `delete_workflow_transition_rule_configurations` | Remove transition rules |
| `get_workflow_transition_properties` | Get properties on a workflow transition |
| `create_workflow_transition_property` | Add a property to a transition |
| `update_workflow_transition_property` | Update a transition property |
| `delete_workflow_transition_property` | Remove a transition property |

---

### Filters

Save and manage JQL-based issue filters.

| Tool | Description |
|------|-------------|
| `create_filter` | Create a saved filter |
| `get_filter` | Get a filter by ID |
| `update_filter` | Update a saved filter |
| `delete_filter` | Delete a saved filter |
| `search_for_filters` | Search for filters by name or owner |
| `get_my_filters` | Get the current user's filters |
| `get_favourite_filters` | Get the current user's favourite filters |
| `get_columns` | Get the columns configured for a filter |
| `set_columns` | Set columns for a filter |
| `reset_columns` | Reset filter columns to defaults |
| `add_filter_as_favourite` | Mark a filter as a favourite |
| `remove_filter_as_favourite` | Remove a filter from favourites |
| `change_filter_owner` | Transfer ownership of a filter |

---

### Filter Sharing

| Tool | Description |
|------|-------------|
| `get_share_permissions` | List who a filter is shared with |
| `add_share_permission` | Share a filter with a user, group, or project |
| `get_share_permission` | Get a specific share permission |
| `delete_share_permission` | Remove a share permission |
| `get_default_share_scope` | Get the default scope for new filter shares |
| `set_default_share_scope` | Set the default scope for new filter shares |

---

### Dashboards

| Tool | Description |
|------|-------------|
| `get_all_dashboards` | List all dashboards |
| `create_dashboard` | Create a new dashboard |
| `get_dashboard` | Get a dashboard by ID |
| `update_dashboard` | Update dashboard settings |
| `delete_dashboard` | Delete a dashboard |
| `copy_dashboard` | Duplicate a dashboard |
| `search_for_dashboards` | Search dashboards by name |
| `bulk_edit_dashboards` | Update settings on multiple dashboards |
| `get_gadgets` | List gadgets on a dashboard |
| `add_gadget_to_dashboard` | Add a gadget to a dashboard |
| `update_gadget_on_dashboard` | Update a dashboard gadget |
| `remove_gadget_from_dashboard` | Remove a gadget from a dashboard |
| `get_available_gadgets` | List all available gadget types |
| `get_dashboard_item_property_keys` | Get property keys for a dashboard item |
| `get_dashboard_item_property` | Get a dashboard item property |
| `set_dashboard_item_property` | Set a dashboard item property |
| `delete_dashboard_item_property` | Delete a dashboard item property |

---

### Users

| Tool | Description |
|------|-------------|
| `get_user` | Get a user by account ID |
| `create_user` | Create a new user account |
| `delete_user` | Delete a user account |
| `bulk_get_users` | Fetch multiple users by account ID |
| `get_account_i_ds_for_users` | Look up account IDs for usernames |
| `get_user_default_columns` | Get default columns for a user |
| `set_user_default_columns` | Set default issue navigator columns for a user |
| `reset_user_default_columns` | Reset user columns to defaults |
| `get_user_email` | Get a user's email address |
| `get_user_email_bulk` | Get email addresses for multiple users |
| `get_user_groups` | Get groups a user belongs to |
| `get_all_users` | List all users (paginated) |
| `get_all_users_default` | List all users (uses default pagination) |

---

### User Search

| Tool | Description |
|------|-------------|
| `find_users` | Find users by display name or email |
| `find_users_assignable_to_projects` | Find users who can be assigned in specific projects |
| `find_users_assignable_to_issues` | Find users assignable to a specific issue |
| `find_users_with_permissions` | Find users who have specific permissions |
| `find_users_with_browse_permission` | Find users with browse permission on an issue |
| `find_users_for_picker` | Search users for the user picker UI |
| `find_users_by_query` | Find users using a structured query |
| `find_user_keys_by_query` | Find user keys using a query |
| `find_users_and_groups` | Combined user and group search |

---

### User Properties

| Tool | Description |
|------|-------------|
| `get_user_property_keys` | List all property keys for a user |
| `get_user_property` | Get a user property value |
| `set_user_property` | Set a user property |
| `delete_user_property` | Delete a user property |

---

### Groups

| Tool | Description |
|------|-------------|
| `create_group` | Create a new group |
| `get_group` | Get a group by name |
| `delete_group` | Delete a group |
| `bulk_get_groups` | Fetch multiple groups by ID |
| `get_users_from_group` | List members of a group |
| `add_user_to_group` | Add a user to a group |
| `remove_user_from_group` | Remove a user from a group |
| `find_groups` | Search for groups by name |

---

### Permissions & Permission Schemes

| Tool | Description |
|------|-------------|
| `get_my_permissions` | Check what permissions the current user has |
| `get_all_permissions` | List all possible Jira permissions |
| `get_bulk_permissions` | Check permissions for specific users/projects |
| `get_permitted_projects` | Get projects where the user has a given permission |
| `get_all_permission_schemes` | List all permission schemes |
| `create_permission_scheme` | Create a permission scheme |
| `get_permission_scheme` | Get a permission scheme by ID |
| `update_permission_scheme` | Update a permission scheme |
| `delete_permission_scheme` | Delete a permission scheme |
| `get_permission_scheme_grants` | List all grants in a permission scheme |
| `create_permission_grant` | Add a grant to a permission scheme |
| `get_permission_scheme_grant` | Get a specific grant |
| `delete_permission_scheme_grant` | Remove a grant from a permission scheme |

---

### Issue Types

| Tool | Description |
|------|-------------|
| `get_all_issue_types_for_user` | List all issue types available to the current user |
| `create_issue_type` | Create a new issue type |
| `get_issue_type` | Get an issue type by ID |
| `update_issue_type` | Update an issue type |
| `delete_issue_type` | Delete an issue type |
| `get_issue_types_for_project` | List issue types available in a project |
| `get_alternative_issue_types` | Get issue types the current type can be converted to |
| `load_issue_type_avatar` | Upload an avatar for an issue type |

---

### Issue Type Schemes

Group issue types into schemes assigned to projects.

| Tool | Description |
|------|-------------|
| `get_all_issue_type_schemes` | List all issue type schemes |
| `create_issue_type_scheme` | Create a new issue type scheme |
| `update_issue_type_scheme` | Update a scheme |
| `delete_issue_type_scheme` | Delete a scheme |
| `get_issue_type_scheme_items` | Get issue types in a scheme |
| `get_issue_type_schemes_for_projects` | Get schemes for specific projects |
| `assign_issue_type_scheme_to_project` | Assign a scheme to a project |
| `add_issue_types_to_issue_type_scheme` | Add issue types to a scheme |
| `change_order_of_issue_types` | Reorder issue types in a scheme |
| `remove_issue_type_from_issue_type_scheme` | Remove an issue type from a scheme |

---

### Issue Type Screen Schemes

Map issue types to screen schemes.

| Tool | Description |
|------|-------------|
| `get_issue_type_screen_schemes` | List all issue type screen schemes |
| `create_issue_type_screen_scheme` | Create a new scheme |
| `update_issue_type_screen_scheme` | Update a scheme |
| `delete_issue_type_screen_scheme` | Delete a scheme |
| `get_issue_type_screen_scheme_items` | Get mappings in a scheme |
| `get_issue_type_screen_schemes_for_projects` | Get schemes for specific projects |
| `assign_issue_type_screen_scheme_to_project` | Assign a scheme to a project |
| `append_mappings_to_issue_type_screen_scheme` | Add issue type-to-screen mappings |
| `update_issue_type_screen_scheme_default_screen_scheme` | Set the default screen scheme |
| `remove_mappings_from_issue_type_screen_scheme` | Remove issue type mappings |
| `get_issue_type_screen_scheme_projects` | List projects using a scheme |

---

### Issue Priorities

| Tool | Description |
|------|-------------|
| `get_priorities` | List all priorities |
| `create_priority` | Create a new priority |
| `get_priority` | Get a priority by ID |
| `update_priority` | Update a priority |
| `delete_priority` | Delete a priority |
| `set_default_priority` | Set the default priority |
| `move_priorities` | Reorder priorities |
| `search_priorities` | Search priorities by name |

---

### Priority Schemes

| Tool | Description |
|------|-------------|
| `get_priority_schemes` | List all priority schemes |
| `create_priority_scheme` | Create a priority scheme |
| `update_priority_scheme` | Update a priority scheme |
| `delete_priority_scheme` | Delete a priority scheme |
| `get_priorities_by_priority_scheme` | Get priorities in a scheme |
| `get_available_priorities_by_priority_scheme` | Get priorities available to add to a scheme |
| `get_projects_by_priority_scheme` | Get projects using a scheme |
| `suggested_priorities_for_mappings` | Get suggested priority mappings |

---

### Issue Resolutions

| Tool | Description |
|------|-------------|
| `get_resolutions` | List all resolutions |
| `create_resolution` | Create a new resolution |
| `get_resolution` | Get a resolution by ID |
| `update_resolution` | Update a resolution |
| `delete_resolution` | Delete a resolution |
| `set_default_resolution` | Set the default resolution |
| `move_resolutions` | Reorder resolutions |
| `search_resolutions` | Search resolutions by name |

---

### Issue Fields

| Tool | Description |
|------|-------------|
| `get_fields` | List all fields (system + custom) |
| `create_custom_field` | Create a new custom field |
| `get_fields_paginated` | Page through fields |
| `get_fields_in_trash_paginated` | List custom fields in the trash |
| `update_custom_field` | Update a custom field definition |
| `delete_custom_field` | Permanently delete a custom field |
| `restore_custom_field_from_trash` | Restore a trashed custom field |
| `move_custom_field_to_trash` | Move a custom field to the trash |
| `get_contexts_for_a_field` | List all contexts for a custom field |
| `get_fields_for_projects` | Get fields available in specific projects |

---

### Issue Field Configurations

| Tool | Description |
|------|-------------|
| `get_all_field_configurations` | List all field configurations |
| `create_field_configuration` | Create a field configuration |
| `update_field_configuration` | Update a field configuration |
| `delete_field_configuration` | Delete a field configuration |
| `get_field_configuration_items` | Get fields in a configuration |
| `update_field_configuration_items` | Update field settings within a configuration |
| `get_all_field_configuration_schemes` | List all field configuration schemes |
| `create_field_configuration_scheme` | Create a field configuration scheme |
| `update_field_configuration_scheme` | Update a scheme |
| `delete_field_configuration_scheme` | Delete a scheme |
| `get_field_configuration_issue_type_items` | Get issue type-to-field config mappings |
| `get_field_configuration_schemes_for_projects` | Get schemes for specific projects |
| `assign_field_configuration_scheme_to_project` | Assign a scheme to a project |
| `assign_issue_types_to_field_configurations` | Map issue types to field configurations |
| `remove_issue_types_from_field_configuration_scheme` | Remove issue type mappings |

---

### Field Schemes

| Tool | Description |
|------|-------------|
| `get_field_schemes` | List all field schemes |
| `create_field_scheme` | Create a field scheme |
| `get_field_scheme` | Get a field scheme by ID |
| `update_field_scheme` | Update a field scheme |
| `delete_a_field_scheme` | Delete a field scheme |
| `clone_field_scheme` | Clone an existing field scheme |
| `get_projects_with_field_schemes` | Get projects using a field scheme |
| `associate_projects_to_field_schemes` | Associate projects with a field scheme |
| `search_field_scheme_fields` | Search for fields in a scheme |
| `get_field_parameters` | Get parameters for a field in a scheme |
| `update_field_parameters` | Update field parameters |
| `remove_field_parameters` | Remove field parameters |
| `search_field_scheme_projects` | Search projects in a field scheme |
| `get_fields_associated_with_field_schemes` | Get fields associated with a scheme |
| `remove_fields_associated_with_field_schemes` | Remove field associations |

---

### Issue Custom Field Contexts

| Tool | Description |
|------|-------------|
| `get_custom_field_contexts` | List all contexts for a custom field |
| `create_custom_field_context` | Create a context for a custom field |
| `update_custom_field_context` | Update a context |
| `delete_custom_field_context` | Delete a context |
| `get_custom_field_contexts_default_values` | Get default values for contexts |
| `set_custom_field_contexts_default_values` | Set default values for contexts |
| `get_issue_types_for_custom_field_context` | Get issue type-context mappings |
| `get_custom_field_contexts_for_projects_and_issue_types` | Get contexts by project/issue type |
| `get_project_mappings_for_custom_field_context` | Get project mappings for a context |
| `add_issue_types_to_context` | Add issue types to a context |
| `remove_issue_types_from_context` | Remove issue types from a context |
| `assign_custom_field_context_to_projects` | Assign a context to projects |
| `remove_custom_field_context_from_projects` | Remove a context from projects |

---

### Issue Custom Field Options

| Tool | Description |
|------|-------------|
| `get_custom_field_option` | Get a specific custom field option |
| `get_custom_field_options_context` | List options for a custom field context |
| `create_custom_field_options_context` | Create new options |
| `update_custom_field_options_context` | Update existing options |
| `reorder_custom_field_options_context` | Reorder options |
| `delete_custom_field_options_context` | Delete options |
| `replace_custom_field_options` | Replace one option with another across issues |

---

### Issue Custom Field Values

| Tool | Description |
|------|-------------|
| `update_custom_fields` | Update custom field values on issues (POST) |
| `update_custom_field_value` | Update a custom field value (PUT) |
| `update_multiple_custom_field_values` | Bulk update multiple custom field values |

---

### Issue Custom Field Configurations (Apps)

For Forge/Connect apps that manage custom field configurations.

| Tool | Description |
|------|-------------|
| `get_custom_fields_configurations` | Bulk get custom field configurations |
| `get_custom_field_configuration` | Get configurations for a specific field |
| `update_custom_field_configuration` | Update custom field configurations |

---

### Issue Custom Field Options (Apps)

For Forge/Connect apps managing select field options.

| Tool | Description |
|------|-------------|
| `get_all_issue_field_options` | List all options for an app-managed field |
| `create_issue_field_option` | Create a new field option |
| `get_issue_field_option` | Get a specific field option |
| `update_issue_field_option` | Update a field option |
| `delete_issue_field_option` | Delete a field option |
| `replace_issue_field_option` | Replace one option with another |
| `get_selectable_issue_field_options` | Get options visible in the issue create screen |
| `get_visible_issue_field_options` | Get options visible to the current user |

---

### Issue Custom Field Associations

| Tool | Description |
|------|-------------|
| `create_associations` | Associate custom fields with contexts |
| `remove_associations` | Remove custom field associations |

---

### Screens

| Tool | Description |
|------|-------------|
| `get_screens` | List all screens |
| `create_screen` | Create a new screen |
| `update_screen` | Update a screen |
| `delete_screen` | Delete a screen |
| `get_screens_for_a_field` | Get screens where a field appears |
| `add_field_to_default_screen` | Add a field to the default screen |
| `get_available_screen_fields` | Get fields available to add to a screen |

---

### Screen Tabs & Fields

| Tool | Description |
|------|-------------|
| `get_all_screen_tabs` | List all tabs on a screen |
| `create_screen_tab` | Create a screen tab |
| `update_screen_tab` | Update a screen tab |
| `delete_screen_tab` | Delete a screen tab |
| `move_screen_tab` | Reorder screen tabs |
| `get_bulk_screen_tabs` | Get tabs across multiple screens |
| `get_all_screen_tab_fields` | List fields on a screen tab |
| `add_screen_tab_field` | Add a field to a screen tab |
| `remove_screen_tab_field` | Remove a field from a screen tab |
| `move_screen_tab_field` | Reorder fields within a screen tab |

---

### Screen Schemes

| Tool | Description |
|------|-------------|
| `get_screen_schemes` | List all screen schemes |
| `create_screen_scheme` | Create a screen scheme |
| `update_screen_scheme` | Update a screen scheme |
| `delete_screen_scheme` | Delete a screen scheme |

---

### Status

| Tool | Description |
|------|-------------|
| `bulk_get_statuses` | Fetch multiple statuses by ID |
| `bulk_create_statuses` | Create multiple statuses at once |
| `bulk_update_statuses` | Update multiple statuses |
| `bulk_delete_statuses` | Delete multiple statuses |
| `bulk_get_statuses_by_name` | Fetch statuses by name |
| `search_statuses_paginated` | Search and page through statuses |
| `get_issue_type_usages_by_status_and_project` | Find issue types using a status |
| `get_project_usages_by_status` | Find projects using a status |
| `get_workflow_usages_by_status` | Find workflows using a status |

---

### JQL

| Tool | Description |
|------|-------------|
| `get_field_reference_data` | Get field metadata for JQL autocompletion (GET) |
| `get_field_reference_data_post` | Get field metadata for JQL autocompletion (POST) |
| `get_field_auto_complete_suggestions` | Get autocomplete suggestions for JQL fields |
| `parse_jql_query` | Parse and validate a JQL query |
| `convert_user_identifiers_to_account_i_ds_in_jql_queries` | Convert legacy usernames to account IDs |
| `sanitize_jql_queries` | Sanitize JQL queries for safe execution |

---

### Jira Expressions

| Tool | Description |
|------|-------------|
| `analyse_jira_expression` | Analyse and validate a Jira expression |
| `evaluate_jira_expression_using_enhanced_search_api` | Evaluate a Jira expression |

---

### Avatars

| Tool | Description |
|------|-------------|
| `get_system_avatars_by_type` | Get system-provided avatars (user, project, etc.) |
| `get_avatars` | Get avatars for a specific entity |
| `load_avatar` | Upload a new avatar |
| `delete_avatar` | Delete an avatar |
| `get_avatar_image_by_type` | Get a system avatar image |
| `get_avatar_image_by_id` | Get an avatar image by ID |
| `get_avatar_image_by_owner` | Get the avatar image for an entity |

---

### Audit Records

| Tool | Description |
|------|-------------|
| `get_audit_records` | Get the Jira audit log with filtering by date and keyword |

---

### Webhooks

| Tool | Description |
|------|-------------|
| `get_dynamic_webhooks_for_app` | List all dynamic webhooks for the app |
| `register_dynamic_webhooks` | Register new webhooks |
| `delete_webhooks_by_id` | Delete webhooks by ID |
| `get_failed_webhooks` | Get webhooks that failed to deliver |
| `extend_webhook_life` | Extend the expiry of registered webhooks |

---

### Myself

Tools for the currently authenticated user.

| Tool | Description |
|------|-------------|
| `get_current_user` | Get the current user's profile |
| `get_preference` | Get a user preference setting |
| `set_preference` | Set a user preference |
| `delete_preference` | Delete a user preference |
| `get_locale` | Get the current user's locale |
| `set_locale` | Set the current user's locale |

---

### Server Info & Jira Settings

| Tool | Description |
|------|-------------|
| `get_jira_instance_info` | Get the Jira instance version and server time |
| `get_application_property` | Get an application property |
| `get_advanced_settings` | Get all advanced configuration properties |
| `set_application_property` | Update an application property |
| `get_global_settings` | Get global Jira settings |

---

### Time Tracking

| Tool | Description |
|------|-------------|
| `get_all_time_tracking_providers` | List all available time tracking providers |
| `get_selected_time_tracking_provider` | Get the currently active provider |
| `select_time_tracking_provider` | Switch the active time tracking provider |
| `get_time_tracking_settings` | Get time tracking format settings |
| `set_time_tracking_settings` | Update time tracking format settings |

---

### Labels

| Tool | Description |
|------|-------------|
| `get_all_labels` | List all labels used across Jira |

---

### Plans & Teams in Plan

For Jira Advanced Planning (formerly Portfolio).

| Tool | Description |
|------|-------------|
| `get_plans_paginated` | List all plans |
| `create_plan` | Create a new plan |
| `get_plan` | Get a plan by ID |
| `update_plan` | Update a plan |
| `archive_plan` | Archive a plan |
| `duplicate_plan` | Duplicate a plan |
| `trash_plan` | Move a plan to the trash |
| `get_teams_in_plan_paginated` | List all teams in a plan |
| `add_atlassian_team_to_plan` | Add an Atlassian team to a plan |
| `get_atlassian_team_in_plan` | Get a team in a plan |
| `update_atlassian_team_in_plan` | Update a team in a plan |
| `remove_atlassian_team_from_plan` | Remove a team from a plan |
| `create_plan_only_team` | Create a team that only exists in a plan |
| `get_plan_only_team` | Get a plan-only team |
| `update_plan_only_team` | Update a plan-only team |
| `delete_plan_only_team` | Delete a plan-only team |

---

### License Metrics

| Tool | Description |
|------|-------------|
| `get_license` | Get license information |
| `get_approximate_license_count` | Get approximate total user count |
| `get_approximate_application_license_count` | Get user count per application |

---

### Issue Security Schemes & Levels

| Tool | Description |
|------|-------------|
| `get_issue_security_schemes` | List all issue security schemes |
| `create_issue_security_scheme` | Create a security scheme |
| `get_issue_security_scheme` | Get a scheme by ID |
| `update_issue_security_scheme` | Update a security scheme |
| `delete_issue_security_scheme` | Delete a security scheme |
| `get_issue_security_levels` | List all security levels in a scheme |
| `set_default_issue_security_levels` | Set default security levels |
| `add_issue_security_levels` | Add security levels to a scheme |
| `update_issue_security_level` | Update a security level |
| `remove_issue_security_level` | Remove a security level |
| `get_issue_security_level_members` | Get members of a security level |
| `add_issue_security_level_members` | Add members to a security level |
| `remove_member_from_issue_security_level` | Remove a member from a security level |
| `search_issue_security_schemes` | Search security schemes |
| `get_projects_using_issue_security_schemes` | Get projects using a security scheme |
| `associate_security_scheme_to_project` | Assign a security scheme to a project |
| `get_issue_security_level_members_by_issue_security_scheme` | Get members by scheme |
| `get_issue_security_level` | Get a specific security level |

---

### Issue Notification Schemes

| Tool | Description |
|------|-------------|
| `get_notification_schemes_paginated` | List all notification schemes |
| `create_notification_scheme` | Create a notification scheme |
| `get_notification_scheme` | Get a scheme by ID |
| `update_notification_scheme` | Update a notification scheme |
| `delete_notification_scheme` | Delete a notification scheme |
| `add_notifications_to_notification_scheme` | Add notification rules to a scheme |
| `remove_notification_from_notification_scheme` | Remove a notification rule |
| `get_projects_using_notification_schemes_paginated` | Get projects using a scheme |

---

### Issue Link Types

| Tool | Description |
|------|-------------|
| `get_issue_link_types` | List all issue link types (blocks, clones, etc.) |
| `create_issue_link_type` | Create a new link type |
| `get_issue_link_type` | Get a link type by ID |
| `update_issue_link_type` | Update a link type |
| `delete_issue_link_type` | Delete a link type |

---

### Issue Navigator Settings

| Tool | Description |
|------|-------------|
| `get_issue_navigator_default_columns` | Get the default columns for the issue navigator |
| `set_issue_navigator_default_columns` | Set the default columns |

---

### Application Roles

| Tool | Description |
|------|-------------|
| `get_all_application_roles` | List all application roles |
| `get_application_role` | Get a specific application role by key |

---

### Announcement Banner

| Tool | Description |
|------|-------------|
| `get_banner` | Get the current announcement banner configuration |
| `set_banner` | Update the announcement banner |

---

### Tasks

Long-running background tasks in Jira.

| Tool | Description |
|------|-------------|
| `get_task` | Get the status and result of a background task |
| `cancel_task` | Cancel a running background task |

---

### App Properties & Dynamic Modules

| Tool | Description |
|------|-------------|
| `get_app_properties` | List all properties for an app |
| `get_app_property` | Get a specific app property |
| `set_app_property` | Set an app property |
| `delete_app_property` | Delete an app property |
| `get_modules` | List dynamically registered modules |
| `register_modules` | Register new dynamic modules |
| `remove_modules` | Remove dynamic modules |

---

### Classification Levels

| Tool | Description |
|------|-------------|
| `get_all_classification_levels` | Get all data classification levels defined for the workspace |

---

## Authentication

This server uses **HTTP Basic Authentication** with your Jira email address and a Jira API token. Credentials are transmitted securely over HTTPS.

| Env Variable | Required | Description |
|---|---|---|
| `JIRA_BASE_URL` | Yes | Your Jira Cloud URL, e.g. `https://yourcompany.atlassian.net` |
| `JIRA_EMAIL` | Yes | The email address of your Jira account |
| `JIRA_API_TOKEN` | Yes | An API token generated in your Atlassian account settings |
| `JIRA_MCP_RATE_LIMIT` | No | Max tool calls per second (default: `10`) |

To generate an API token:
1. Go to [https://id.atlassian.com/manage-profile/security/api-tokens](https://id.atlassian.com/manage-profile/security/api-tokens)
2. Click **Create API token**
3. Copy the token value and add it to your `.env` file

> Your Jira permissions determine what each tool can access. The server will return Jira's native `403 Forbidden` or `404 Not Found` errors if you lack the necessary permissions for a given operation.

---

## Security

This server is fully compliant with the [MCP specification](https://modelcontextprotocol.io/specification/latest) security requirements:

- **Input validation** — all tool arguments are validated against their JSON Schema before execution (via `jsonschema.validate` before dispatching to the Jira API).
- **Rate limiting** — a token-bucket rate limiter (default: 10 calls/sec) protects against runaway tool invocations. Tune with `JIRA_MCP_RATE_LIMIT`.
- **Output sanitization** — every Jira API response is recursively scanned before being returned. Values for sensitive keys (`password`, `token`, `secret`, `apikey`, `authorization`, `credential`, etc.) are replaced with `[REDACTED]`. Strings longer than 10,000 characters are truncated.
- **Structured output validation** — tools that have a defined response schema (`outputSchema`) have their structured results validated by the SDK before they reach the client.
- **Credentials never logged** — authentication details are read from environment variables at startup and never written to logs or stdout.
- **Error isolation** — tool execution errors (HTTP failures, invalid inputs) are returned as `isError: true` results, not as protocol-level JSON-RPC errors, so the client always receives a clean, usable response.

---

## Troubleshooting

**Server does not start**
- Ensure `uv` is installed: `~/.local/bin/uv --version`
- Ensure dependencies are installed: `~/.local/bin/uv sync`
- Check that your `.env` file exists and has all three required variables

**Authentication errors (`401 Unauthorized`)**
- Verify `JIRA_EMAIL` matches the email on your Atlassian account exactly
- Ensure the API token is valid and hasn't been revoked
- Confirm `JIRA_BASE_URL` has no trailing slash

**`403 Forbidden` on operations**
- Your Jira account may lack the required permissions
- Contact your Jira administrator to grant the necessary access

**`404 Not Found`**
- Check that the issue key, project key, or ID you are using is correct
- Ensure you are pointing at the right Jira instance (`JIRA_BASE_URL`)

**Tool not found / server not listed in AI tool**
- Confirm the `--directory` path in your MCP config points to the correct location
- Restart your AI tool after updating the MCP configuration
- On Claude Code, run `claude mcp list` to verify the server is registered
