# MCP Integration Guide

## What is MCP?

Model Context Protocol (MCP) is Anthropic's open standard for AI agents to interact
with external tools and data sources over a structured interface. UAT Runner exposes
an MCP server so that agents can programmatically create test sessions, monitor
progress, and read results -- while humans do the actual testing.

The key design principle is **human-in-the-loop**: the agent builds code, creates a
UAT session, and then a human tester verifies the work through the web UI or console
TUI. The agent checks results afterward, fixes any failures, and repeats.

---

## Registration

### Claude Code

Add to your project-level `.claude/settings.json` (or `~/.claude/settings.json` for
global access):

```json
{
  "mcpServers": {
    "uat-runner": {
      "command": "python",
      "args": ["-m", "uat_runner.mcp_server"],
      "cwd": "/path/to/repo"
    }
  }
}
```

Replace `/path/to/repo` with the absolute path to the UAT Runner repository root (the
directory containing the `uat_runner/` package).

### Claude Desktop

Add to `claude_desktop_config.json` (typically at
`~/Library/Application Support/Claude/claude_desktop_config.json` on macOS or
`%APPDATA%\Claude\claude_desktop_config.json` on Windows):

```json
{
  "mcpServers": {
    "uat-runner": {
      "command": "python",
      "args": ["-m", "uat_runner.mcp_server"],
      "cwd": "/path/to/repo"
    }
  }
}
```

### Other MCP Clients

The server uses **stdio transport**. Any MCP-compatible client can connect by
spawning the process:

```
python -m uat_runner.mcp_server
```

The server reads JSON-RPC messages from stdin and writes responses to stdout. Set the
working directory to the UAT Runner repository root so that built-in plan paths
resolve correctly.

---

## Available Tools

### 1. `list_plans`

List the built-in test plans available for creating sessions.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| *(none)* | | | This tool takes no arguments. |

**Returns:** `{ plans: [{ name, label, test_count }] }`

Each entry contains:
- `name` -- short identifier used as the `plan` argument to `create_session`
- `label` -- human-readable label for the plan
- `test_count` -- number of test cases in the plan

**Example:**

```
list_plans()
```

```json
{
  "plans": [
    { "name": "myapp", "label": "My Application", "test_count": 42 },
    { "name": "regression", "label": "Regression Tests", "test_count": 18 }
  ]
}
```

---

### 2. `create_session`

Create a new UAT test session for human testing.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `plan` | string | yes | Built-in plan name (if configured) or absolute path to a markdown test plan file. |
| `version` | string | yes | Version string being tested (e.g. `"4.1.0"`). |
| `tester` | string | yes | Name of the person who will run the tests. |

**Returns:** Full session dict including `id`, `plan_name`, `version`, `tester`, `started`, `sections` (with all test cases), and `summary` with counts.

The session ID is auto-generated in the format `{plan}_{version}_{YYYYMMDD_HHMMSS}`.

**Example:**

```
create_session(plan="/path/to/my_test_plan.md", version="4.1.0", tester="Alice")
```

```json
{
  "id": "my_test_plan_4.1.0_20260315_140000",
  "plan_name": "my_test_plan",
  "plan_path": "/path/to/my_test_plan.md",
  "version": "4.1.0",
  "tester": "Alice",
  "started": "2026-03-15T14:00:00",
  "updated": "2026-03-15T14:00:00",
  "completed": null,
  "sections": [ ... ],
  "summary": { "total": 42, "pass": 0, "fail": 0, "skip": 0, "remaining": 42 }
}
```

---

### 3. `get_session`

Get the full state of a UAT session including all test results.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `session_id` | string | yes | The session ID returned by `create_session`. |

**Returns:** Full session state with `sections`, `tests`, individual `result`/`comment`/`timestamp` fields, and `summary` counts (`total`, `pass`, `fail`, `skip`, `remaining`).

Returns `{ error: "Session not found: ..." }` if the session does not exist.

**Example:**

```
get_session(session_id="my_test_plan_4.1.0_20260315_140000")
```

---

### 4. `list_sessions`

List all UAT sessions, optionally filtered by plan or version.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `plan` | string | no | Filter by plan name. Empty string or omitted for all. |
| `version` | string | no | Filter by version string (e.g. `"4.1.0"`). Empty string or omitted for all. |

**Returns:** `{ sessions: [...] }` where each entry contains:
- `id` -- session identifier
- `plan_name` -- which plan was used
- `version` -- version under test
- `tester` -- who is testing
- `started` -- ISO timestamp when session was created
- `completed` -- ISO timestamp when all tests were answered (null if in progress)
- `total` -- total test count
- `answered` -- number of tests with results
- `pass`, `fail`, `skip` -- result counts

**Example:**

```
list_sessions(plan="my_test_plan", version="4.1.0")
```

```json
{
  "sessions": [
    {
      "id": "my_test_plan_4.1.0_20260315_140000",
      "plan_name": "my_test_plan",
      "version": "4.1.0",
      "tester": "Alice",
      "started": "2026-03-15T14:00:00",
      "completed": null,
      "total": 42,
      "answered": 18,
      "pass": 15,
      "fail": 2,
      "skip": 1
    }
  ]
}
```

---

### 5. `mark_test`

Mark a single test result in a UAT session.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `session_id` | string | yes | The session ID. |
| `section_idx` | integer | yes | Section index (0-based). |
| `test_idx` | integer | yes | Test index within the section (0-based). |
| `result` | string | yes | One of `"pass"`, `"fail"`, or `"skip"`. |
| `comment` | string | no | Optional comment explaining the result. Defaults to empty string. |

**Returns:** Updated full session state with new summary counts.

Returns an error dict if the result value is invalid, the session is not found, or
the indices are out of range.

**Example:**

```
mark_test(
    session_id="my_test_plan_4.1.0_20260315_140000",
    section_idx=0,
    test_idx=2,
    result="pass",
    comment="Verified page loads in under 2s"
)
```

---

### 6. `get_next_test`

Get the next unanswered test in a session.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `session_id` | string | yes | The session ID. |

**Returns:** Either test details or a completion indicator:

When tests remain:
```json
{
  "complete": false,
  "section_idx": 2,
  "test_idx": 0,
  "section_title": "3. Multi-Track Planning",
  "test_num": "3.1",
  "test": "Add three tracks and verify map rendering",
  "expected": "All three tracks visible on map with distinct colors",
  "summary": { "total": 42, "pass": 20, "fail": 1, "skip": 0, "remaining": 21 }
}
```

When all tests are answered:
```json
{
  "complete": true,
  "summary": { "total": 42, "pass": 39, "fail": 2, "skip": 1, "remaining": 0 }
}
```

---

### 7. `generate_report`

Generate markdown and XLSX reports for a session.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `session_id` | string | yes | The session ID. |

**Returns:** Paths to the generated files and the session summary.

Reports can be generated at any point -- they do not require all tests to be answered.
Partial reports serve as progress snapshots.

```json
{
  "markdown_path": "/path/to/results/my_test_plan_4.1.0_20260315_140000_report.md",
  "xlsx_path": "/path/to/results/my_test_plan_4.1.0_20260315_140000_report.xlsx",
  "summary": { "total": 42, "pass": 39, "fail": 2, "skip": 1, "remaining": 0 }
}
```

---

### 8. `read_report`

Read the generated markdown report content as a string.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `session_id` | string | yes | The session ID. |

**Returns:** `{ content: "# UAT Report: my_test_plan v4.1.0\n..." }`

Returns `{ error: "Report not found. Call generate_report() first." }` if the
markdown report has not been generated yet. Always call `generate_report` before
`read_report`.

**Example:**

```
read_report(session_id="my_test_plan_4.1.0_20260315_140000")
```

---

## Agent Workflow

### Standard Workflow

This is the typical sequence an agent follows to run human-in-the-loop UAT:

1. **Discover plans.** Call `list_plans()` to see which built-in test plans are
   available and how many tests each contains.

2. **Create a session.** Call `create_session("/path/to/plan.md", "4.1.0", "Alice")`
   to set up a new test session. Save the returned `id`.

3. **Hand off to the human.** Tell the tester to open the web UI and begin
   testing:
   ```
   Please open the UAT web UI and begin testing session plan_4.1.0_20260315_140000.
   Start the web UI with: python -m uat_runner web --port 8080
   ```

4. **Monitor progress.** Periodically call `get_session(id)` to check the
   `summary.remaining` count. You can also call `get_next_test(id)` to see
   which test the tester should work on next.

5. **Generate and read the report.** When `summary.remaining` reaches 0 (or the
   tester finishes), call `generate_report(id)` followed by `read_report(id)`
   to get the full markdown report content.

6. **Analyze failures.** Parse the report for any `FAIL` results. Fix the
   underlying code issues.

7. **Re-test.** Create a new session for the fixed version and repeat the cycle
   until all tests pass.

### Custom Test Plans

Agents can generate their own markdown test plans and pass them to
`create_session`. The parser accepts any markdown file that follows this format:

```markdown
## 1. Section Title

| # | Test | Expected | Pass |
|---|------|----------|------|
| 1.1 | Do something specific | Expected outcome | |
| 1.2 | Do another thing | Another outcome | |

## 2. Another Section

| # | Test | Expected | Pass |
|---|------|----------|------|
| 2.1 | Third test | Third outcome | |
```

Rules for custom plans:
- Section headings must use `## N. Title` format (where N is a number, optionally
  followed by a letter like `10a`)
- `## Pre-Test: Title` headings are also supported
- Sub-sections can use `### Na. Title` format
- Each section must contain a markdown table with columns: `#`, `Test`, `Expected`,
  `Pass`
- The `Pass` column is ignored by the parser (results come from the session)

Pass the absolute file path to `create_session`:

```
create_session(plan="/tmp/my_custom_plan.md", version="1.0.0", tester="Bob")
```

### Automated Pre-Checks

Agents can use `mark_test()` to programmatically mark tests they can verify
without human intervention. This is useful for automated pre-checks before
handing the session to a human tester.

For example, an agent might:

1. Create a session
2. Automatically mark infrastructure tests (e.g., "page loads without HTTP errors",
   "API returns 200", "all JS files load")
3. Hand the session to a human for visual and UX tests that require human judgment

```
# Agent marks automated checks
mark_test(session_id=id, section_idx=0, test_idx=0, result="pass",
          comment="Automated: HTTP 200 verified")
mark_test(session_id=id, section_idx=0, test_idx=1, result="pass",
          comment="Automated: No console errors detected")

# Human handles the rest via web UI
```

The human tester will see pre-checked tests as already answered and can override
them if needed.

---

## Troubleshooting

**Server won't start**

- Verify that the `mcp` package with CLI extras is installed:
  ```bash
  pip install "mcp[cli]"
  ```
- Check that the `uat_runner.mcp_server` module is importable by running:
  ```bash
  python -c "from uat_runner.mcp_server import mcp; print('OK')"
  ```
- Make sure you are running from the repository root (or that `cwd` in your MCP
  config points to it).

**Tool not found after registration**

- Verify the server is registered in your settings file (`.claude/settings.json` for
  Claude Code, `claude_desktop_config.json` for Claude Desktop).
- Restart the MCP client after editing configuration.
- Check that the `command` path points to the correct Python interpreter. If using a
  virtualenv, use the full path to the venv Python binary:
  ```json
  "command": "/path/to/uat_runner_repo/.venv/bin/python"
  ```

**Session not found**

- Sessions are stored as JSON files in `results/` (relative to the UAT Runner repo
  root). Verify that both the MCP server and the web UI are reading from the same
  results directory.
- Check that the session ID is correct -- IDs follow the format
  `{plan}_{version}_{YYYYMMDD_HHMMSS}`.

**Plans not listed**

- `list_plans()` only returns built-in plans whose markdown files exist on disk.
  Verify the plan files are present at the paths configured in `BUILTIN_PLANS`.
- For custom plans, pass the absolute file path directly to `create_session` instead
  of using `list_plans`.

**Report generation fails**

- The `openpyxl` package is required for XLSX reports:
  ```bash
  pip install openpyxl
  ```
- Markdown reports have no additional dependencies beyond the standard library.
