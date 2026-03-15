# Extending the UAT Runner

Developer guide for adding features to the UAT runner tool.

## Architecture Overview

```
Markdown Plan File
       |
    parser.py ──── parse_plan(path) -> list[Section]
       |
    session.py ─── create_session() -> Session (saved to JSON)
       |
   ┌───┴───┐
   |       |
runner.py  web.py ──── Interactive test execution
   |       |
   └───┬───┘
       |
    report.py ──── generate_markdown_report() / generate_xlsx_report()
```

All modules share the same data model (`models.py`) and session storage (`session.py`). The runner (TUI) and web (Flask) are independent frontends that can be used interchangeably. Neither frontend imports the other. Both read and write sessions through the same `load_session()` / `save_session()` functions, so a session started in the TUI can be resumed in the web UI and vice versa.

Entry point: `python -m uat_runner` calls `cli.main()`.

---

## Data Model Reference

All dataclasses live in `models.py`. Every model has `to_dict()` and `from_dict()` for JSON serialization.

### TestCase

A single test case parsed from a UAT markdown table row.

| Field | Type | Description |
|-------|------|-------------|
| `num` | `str` | Test number, e.g. `"1.1"`, `"3.4"` |
| `test` | `str` | Test description / action to perform |
| `expected` | `str` | Expected outcome |
| `result` | `Optional[str]` | `"pass"`, `"fail"`, `"skip"`, or `None` (unanswered) |
| `comment` | `str` | Tester's comment (default `""`) |
| `timestamp` | `Optional[str]` | ISO 8601 datetime when result was recorded |

Methods:
- `is_answered()` -- returns `True` if `result is not None`
- `to_dict()` -- calls `dataclasses.asdict(self)`
- `from_dict(d)` -- classmethod, constructs from dict

### Section

A group of related test cases, parsed from a `##` or `###` heading.

| Field | Type | Description |
|-------|------|-------------|
| `key` | `str` | Section identifier, e.g. `"1"`, `"10a"`, `"Pre-Test: Page Load"` |
| `title` | `str` | Full heading text, e.g. `"1. Single-Track Flight Planning"` |
| `tests` | `list[TestCase]` | Test cases in this section |

Methods:
- `to_dict()` -- returns `{"key": ..., "title": ..., "tests": [...]}`
- `from_dict(d)` -- classmethod

### Session

The top-level session object containing all state needed for save/resume.

| Field | Type | Description |
|-------|------|-------------|
| `id` | `str` | Format: `{plan_name}_{version}_{YYYYMMDD_HHMMSS}` |
| `plan_name` | `str` | Short label, e.g. `"static"`, `"flask"`, `"firmware"` |
| `plan_path` | `str` | Absolute path to the markdown plan file |
| `version` | `str` | Version string being tested |
| `tester` | `str` | Name of the person running tests |
| `started` | `str` | ISO 8601 datetime when session was created |
| `updated` | `str` | ISO 8601 datetime of last save |
| `completed` | `Optional[str]` | ISO 8601 datetime when all tests were answered, or `None` |
| `sections` | `list[Section]` | All test sections with their test cases |

Computed properties (not stored in JSON, recalculated on access):
- `total` -- sum of all test cases across all sections
- `answered` -- count of tests where `result is not None`
- `passed` -- count of tests with `result == "pass"`
- `failed` -- count of tests with `result == "fail"`
- `skipped` -- count of tests with `result == "skip"`
- `remaining` -- `total - answered`
- `is_complete` -- `remaining == 0`

Methods:
- `summary_dict()` -- returns `{"total": N, "pass": N, "fail": N, "skip": N, "remaining": N}`
- `to_dict()` -- full serialization including a `summary` key from `summary_dict()`
- `from_dict(d)` -- classmethod (note: ignores the `summary` key since those are computed)
- `find_first_unanswered()` -- returns `(section_idx, test_idx)` tuple, or `None` if all answered

---

## Session JSON Schema

Session files are stored as `{session_id}.json` in the results directory (default: `results/`).

```json
{
  "id": "static_4.1.0_20260315_143022",
  "plan_name": "static",
  "plan_path": "/path/to/your/test_plan.md",
  "version": "4.1.0",
  "tester": "Alice",
  "started": "2026-03-15T14:30:22",
  "updated": "2026-03-15T15:12:05",
  "completed": null,
  "sections": [
    {
      "key": "1",
      "title": "1. Single-Track Flight Planning",
      "tests": [
        {
          "num": "1.1",
          "test": "Click the map to place a single waypoint",
          "expected": "Marker appears on map at clicked location",
          "result": "pass",
          "comment": "",
          "timestamp": "2026-03-15T14:31:10"
        },
        {
          "num": "1.2",
          "test": "Click Generate with one waypoint",
          "expected": "Error message: need at least 2 waypoints",
          "result": null,
          "comment": "",
          "timestamp": null
        }
      ]
    }
  ],
  "summary": {
    "total": 85,
    "pass": 12,
    "fail": 0,
    "skip": 1,
    "remaining": 72
  }
}
```

Field notes:
- `id` is constructed from `{plan_name}_{version}_{YYYYMMDD_HHMMSS}` at creation time and never changes.
- `completed` is `null` until all tests are answered, then set to the ISO 8601 timestamp of the final save.
- `summary` is written by `to_dict()` for convenient reading by `list_sessions()`, but `from_dict()` ignores it -- the values are recomputed from the sections on load.
- `result` in each test is one of `"pass"`, `"fail"`, `"skip"`, or `null` (unanswered).
- `timestamp` in each test is `null` until a result is recorded.

---

## Adding a New CLI Subcommand

### Steps

1. Write a `cmd_mycommand(args)` function in `cli.py`.
2. Add a subparser in the `main()` function.
3. Add the command name to the `commands` dispatch dict.
4. If the command reads or writes session files, add `--results-dir` with `_add_results_dir()`.

### Example: `diff` command comparing two sessions

**Step 1.** Add the command function in `cli.py`:

```python
def cmd_diff(args):
    """Compare two UAT sessions side by side."""
    try:
        session_a = load_session(args.session_a, args.results_dir)
        session_b = load_session(args.session_b, args.results_dir)
    except FileNotFoundError as e:
        console.print(f"[red]Session not found: {e}[/]")
        sys.exit(1)

    table = Table(title=f"Diff: {session_a.id} vs {session_b.id}",
                  border_style="dim")
    table.add_column("#", style="bold")
    table.add_column("Test")
    table.add_column(session_a.id[:20], justify="center")
    table.add_column(session_b.id[:20], justify="center")

    for sa, sb in zip(session_a.sections, session_b.sections):
        for ta, tb in zip(sa.tests, sb.tests):
            if ta.result != tb.result:
                result_a = (ta.result or "-").upper()
                result_b = (tb.result or "-").upper()
                table.add_row(ta.num, ta.test, result_a, result_b)

    console.print(table)
```

**Step 2.** Add the subparser inside `main()`:

```python
    # diff
    p_diff = sub.add_parser("diff", help="Compare two sessions")
    p_diff.add_argument("session_a", help="First session ID")
    p_diff.add_argument("session_b", help="Second session ID")
    _add_results_dir(p_diff)
```

**Step 3.** Add to the commands dict:

```python
    commands = {
        "run": cmd_run,
        "resume": cmd_resume,
        "report": cmd_report,
        "status": cmd_status,
        "list": cmd_list,
        "web": cmd_web,
        "diff": cmd_diff,       # <-- new
    }
```

Usage:

```bash
python -m uat_runner diff static_4.0.0_20260314_100000 static_4.1.0_20260315_143022
```

---

## Adding a New API Endpoint

### Steps

1. Add a route inside the `create_web_app()` function in `web.py`.
2. Use `load_session()` / `save_session()` with `app.config["RESULTS_DIR"]` for data access.
3. Return `jsonify()` responses with appropriate HTTP status codes.
4. If the endpoint is consumed by the web UI, update the JavaScript in `templates/index.html`.

### Example: DELETE endpoint to remove a session

**Step 1.** Add the route inside `create_web_app()`, after the existing routes:

```python
    @app.route("/api/sessions/<session_id>", methods=["DELETE"])
    def api_delete_session(session_id):
        """Delete a session file."""
        from .session import _session_path
        path = _session_path(session_id, app.config["RESULTS_DIR"])
        if not os.path.exists(path):
            return jsonify({"error": "Session not found"}), 404
        os.remove(path)
        return jsonify({"deleted": session_id})
```

**Step 2.** Add a delete button in the web UI. In the session list row markup inside `loadSessions()`:

```javascript
    // Inside the session-row HTML template, add a delete button:
    `<button class="btn btn-nav btn-sm"
             onclick="event.stopPropagation(); deleteSession('${s.id}')">
         Delete
     </button>`
```

**Step 3.** Add the JavaScript function:

```javascript
async function deleteSession(sessionId) {
    if (!confirm('Delete this session? This cannot be undone.')) return;
    await api('DELETE', '/api/sessions/' + sessionId);
    loadSessions();
}
```

---

## Adding a New Report Format

### Steps

1. Add a `generate_FORMAT_report(session, output_path)` function in `report.py`.
2. Call it from `cmd_report()` in `cli.py`.
3. Add a download endpoint in `web.py` (extend the existing format dispatch).
4. Add a download link in `templates/index.html`.

### Example: CSV report output

**Step 1.** Add the generator in `report.py`:

```python
import csv

def generate_csv_report(session, output_path):
    """Generate a CSV report from a session.

    Args:
        session: Session object with results.
        output_path: Path to write the CSV file.
    """
    with open(output_path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["Section", "#", "Test", "Expected",
                         "Result", "Comment", "Timestamp"])
        for section in session.sections:
            for test in section.tests:
                writer.writerow([
                    section.title,
                    test.num,
                    test.test,
                    test.expected,
                    (test.result or "").upper(),
                    test.comment or "",
                    test.timestamp or "",
                ])
```

**Step 2.** Call it from `cmd_report()` in `cli.py`:

```python
def cmd_report(args):
    """Generate reports for a session."""
    try:
        session = load_session(args.session_id, args.results_dir)
    except FileNotFoundError:
        console.print(f"[red]Session not found: {args.session_id}[/]")
        sys.exit(1)

    results_dir = os.path.abspath(args.results_dir or DEFAULT_RESULTS_DIR)

    md_path = os.path.join(results_dir, f"{session.id}_report.md")
    generate_markdown_report(session, md_path)
    console.print(f"[green]Markdown report:[/] {md_path}")

    xlsx_path = os.path.join(results_dir, f"{session.id}_report.xlsx")
    generate_xlsx_report(session, xlsx_path)
    console.print(f"[green]XLSX report:[/] {xlsx_path}")

    csv_path = os.path.join(results_dir, f"{session.id}_report.csv")    # new
    generate_csv_report(session, csv_path)                                # new
    console.print(f"[green]CSV report:[/] {csv_path}")                   # new
```

Don't forget to update the import at the top of `cli.py`:

```python
from .report import generate_markdown_report, generate_xlsx_report, generate_csv_report
```

**Step 3.** Add the format to the download endpoint in `web.py`. In `api_download_report()`, extend the if/elif chain:

```python
        elif fmt == "csv":
            path = os.path.join(rd, f"{session_id}_report.csv")
            mimetype = "text/csv"
```

Also update `api_generate_report()` to generate the CSV:

```python
        csv_path = os.path.join(rd, f"{session.id}_report.csv")
        generate_csv_report(session, csv_path)

        return jsonify({
            "markdown": f"/api/sessions/{session_id}/report/md",
            "xlsx": f"/api/sessions/{session_id}/report/xlsx",
            "csv": f"/api/sessions/{session_id}/report/csv",
        })
```

**Step 4.** Add a download link in `templates/index.html`, next to the existing report links:

```html
<a id="link-csv" class="btn btn-nav"
   style="display:none; text-decoration:none;" download>Download CSV</a>
```

And in the `generateReport()` JavaScript function:

```javascript
    const linkCsv = document.getElementById('link-csv');
    linkCsv.href = data.csv;
    linkCsv.style.display = 'inline-block';
```

---

## Modifying the Web UI

The web UI is a single HTML file (`templates/index.html`) with no build step and no external framework dependencies.

### Structure

- **Embedded CSS** at the top, using CSS custom properties (variables) on `:root` for the dark theme. All colors, backgrounds, and borders reference these variables.
- **Vanilla JavaScript** at the bottom, inside a single `<script>` tag.
- **4 views** controlled by `showView(name)`:
  - `view-list` -- session list with clickable rows
  - `view-create` -- new session form (plan dropdown, version, tester)
  - `view-runner` -- test execution with progress bar and action buttons
  - `view-complete` -- completion summary with failures table and report downloads
- **API communication** via the `api(method, path, body)` async helper, which wraps `fetch()` and returns parsed JSON.
- **Global state**: `session` (current session object), `flatTests` (array of `{si, ti}` index pairs), `flatPos` (current position in `flatTests`), `busy` (flag to prevent double-submits).

### View switching

Views are `<div>` elements with `class="view"`. Only one has `class="view active"` at a time. The `showView()` function removes `active` from all views, then adds it to the target:

```javascript
function showView(name) {
    document.querySelectorAll('.view').forEach(v => v.classList.remove('active'));
    document.getElementById('view-' + name).classList.add('active');
}
```

### Adding a new view

1. Add an HTML div with `class="view"` and a unique `id`:

```html
    <!-- HISTORY VIEW -->
    <div id="view-history" class="view">
        <h2 style="margin-bottom:20px;">Session History</h2>
        <div id="history-content"></div>
        <button class="btn btn-nav" onclick="showView('list')">Back</button>
    </div>
```

2. Add a navigation trigger somewhere (e.g., a button in another view):

```html
<button class="btn btn-nav btn-sm" onclick="showView('history')">History</button>
```

3. Add JavaScript functions for the view's logic:

```javascript
async function loadHistory() {
    const data = await api('GET', '/api/sessions');
    const el = document.getElementById('history-content');
    // Render timeline...
}
```

4. Add any new API endpoints the view needs (see "Adding a New API Endpoint" above).

### Keyboard shortcuts

Keyboard handling is in a global `keydown` listener. It only fires when `view-runner` is active and the focused element is not a `TEXTAREA` or `INPUT`. To add a new shortcut:

```javascript
    else if (key === 'j') { e.preventDefault(); jumpToSection(); }
```

### Escaping

All user-supplied text must go through the `esc()` function before insertion via `innerHTML`. This prevents XSS:

```javascript
function esc(str) {
    if (!str) return '';
    const d = document.createElement('div');
    d.textContent = str;
    return d.innerHTML;
}
```

If you set content via `.textContent` instead of `.innerHTML`, escaping is not needed.

---

## Atomic Save Mechanism

Session saves in `session.py` use a write-to-temp-then-rename pattern:

```python
def save_session(session, results_dir=None):
    """Save session state to JSON (crash-safe atomic write)."""
    session.updated = datetime.now().isoformat(timespec="seconds")
    if session.is_complete and not session.completed:
        session.completed = session.updated

    path = _session_path(session.id, results_dir)
    tmp = path + ".tmp"
    with open(tmp, "w") as f:
        json.dump(session.to_dict(), f, indent=2)
    os.replace(tmp, path)  # atomic on POSIX
```

This prevents corrupted JSON if the process crashes mid-write. The temp file is written completely, then atomically renamed to replace the real file. On POSIX systems, `os.replace()` is guaranteed atomic (it maps to the `rename` syscall). On Windows, `os.replace()` is not guaranteed atomic but is the best available option.

If you add any new data persistence (e.g., a config file, an export cache), follow the same pattern:
1. Write to `path + ".tmp"`.
2. Call `os.replace(tmp, path)`.
3. Never write directly to the final path.

---

## Adding Built-in Plans

Built-in plans are shortcut names that map to markdown files. They are defined in three places that must be kept in sync: `cli.py`, `web.py`, and `mcp_server.py`. All three are empty by default in the standalone repo -- you populate them for your project.

### cli.py

`BUILTIN_PLANS` is a simple dict mapping name to path:

```python
BUILTIN_PLANS = {
    "myapp": os.path.join(REPO_ROOT, "tests",
                          "UAT_TEST_PLAN_MYAPP.md"),
    "api": os.path.join(REPO_ROOT, "tests",
                        "UAT_TEST_PLAN_API.md"),
}
```

### web.py

`BUILTIN_PLANS` is a dict of dicts, adding a human-readable `label` for the dropdown:

```python
BUILTIN_PLANS = {
    "myapp": {
        "name": "myapp",
        "label": "My Application",
        "path": os.path.join(REPO_ROOT, "tests",
                             "UAT_TEST_PLAN_MYAPP.md"),
    },
    "api": {
        "name": "api",
        "label": "API Tests",
        "path": os.path.join(REPO_ROOT, "tests",
                             "UAT_TEST_PLAN_API.md"),
    },
}
```

### mcp_server.py

`BUILTIN_PLANS` is a `{name: path}` dict, same format as `cli.py`:

```python
BUILTIN_PLANS = {
    "myapp": os.path.join(REPO_ROOT, "tests",
                          "UAT_TEST_PLAN_MYAPP.md"),
    "api": os.path.join(REPO_ROOT, "tests",
                        "UAT_TEST_PLAN_API.md"),
}
```

### To add a new built-in plan

1. Create the markdown test plan file following the format described below.
2. Add an entry to `BUILTIN_PLANS` in `cli.py`:

```python
    "integration": os.path.join(REPO_ROOT, "tests",
                                "UAT_TEST_PLAN_INTEGRATION.md"),
```

3. Add the corresponding entry to `BUILTIN_PLANS` in `web.py`:

```python
    "integration": {
        "name": "integration",
        "label": "Integration Tests",
        "path": os.path.join(REPO_ROOT, "tests",
                             "UAT_TEST_PLAN_INTEGRATION.md"),
    },
```

4. Add the corresponding entry to `BUILTIN_PLANS` in `mcp_server.py`:

```python
    "integration": os.path.join(REPO_ROOT, "tests",
                                "UAT_TEST_PLAN_INTEGRATION.md"),
```

The plan file must use the heading and table format that `parser.py` recognizes:

```markdown
## 1. Section Title

| # | Test | Expected | Pass |
|---|------|----------|------|
| 1.1 | Do something | Something happens | |
| 1.2 | Do another thing | Another result | |

## 2. Another Section

| # | Test | Expected | Pass |
|---|------|----------|------|
| 2.1 | Third test | Third expected result | |
```

The parser also supports `## Pre-Test: Title` headings and `### Na. Sub-Section` headings (e.g., `### 10a. Edge Cases`).

---

## MCP Server

The UAT runner exposes its functionality to AI agents via the Model Context Protocol (MCP). The server implementation lives in `mcp_server.py`.

### Architecture

`mcp_server.py` is a thin wrapper over the existing core modules. It imports functions from `session.py`, `parser.py`, and `report.py` and exposes them as MCP tools -- it contains no business logic of its own. The server uses `FastMCP` from the `mcp` Python SDK with `@mcp.tool()` decorators to define each tool. It runs via stdio transport (the agent launches the process and communicates over stdin/stdout).

```
Agent (Claude Code, etc.)
       |
   stdio transport
       |
  mcp_server.py ── FastMCP instance
       |
  ┌────┼────────────┐
  |    |             |
parser.py  session.py  report.py
```

### Existing tools

| Tool | Description |
|------|-------------|
| `list_plans` | Return the dict of built-in plan names and paths |
| `create_session` | Parse a plan and create a new session JSON file |
| `get_session` | Load a session by ID and return its full state |
| `list_sessions` | List all sessions in the results directory with summary info |
| `mark_test` | Record a pass/fail/skip result for a single test case |
| `get_next_test` | Find the first unanswered test in a session |
| `generate_report` | Generate markdown and XLSX reports for a session |
| `read_report` | Read the contents of a generated markdown report file |

### Adding a new MCP tool

1. **Import or write the backing function.** If the logic already exists in `session.py`, `parser.py`, or `report.py`, import it. If it requires new logic, add it to the appropriate core module first, then import it into `mcp_server.py`.

2. **Add an `@mcp.tool()` decorated function** in `mcp_server.py`:

```python
@mcp.tool()
def my_new_tool(session_id: str, flag: bool = False) -> dict:
    """One-line description of what this tool does.

    Longer description if needed. This entire docstring becomes
    the tool description that agents see when they list tools.
    """
    session = load_session(session_id, RESULTS_DIR)
    # ... do work ...
    return {"status": "ok", "data": result}
```

3. **Use type hints for all parameters.** FastMCP inspects them to generate the JSON schema that agents use. Supported types include `str`, `int`, `bool`, `float`, `Optional[str]`, etc. Default values become optional parameters.

4. **Write a descriptive docstring.** This is the only documentation agents see when deciding whether to call the tool. Be specific about what the tool does, what it returns, and any constraints.

5. **Return a dict.** FastMCP serializes the return value to JSON automatically. Return dicts with clear keys. For errors, return `{"error": "description"}` rather than raising exceptions (agents handle dict responses better than tracebacks).

6. **Test the tool directly** (see below).

### Testing MCP tools

You can call MCP tool functions directly as regular Python functions without starting the stdio server:

```python
python3 -c "
from uat_runner.mcp_server import list_plans, create_session
print(list_plans())
"
```

To test a tool that modifies state, use a temporary results directory:

```python
python3 -c "
from uat_runner.mcp_server import create_session, get_session, mark_test
result = create_session(plan='static', version='test', tester='dev')
print(result)
"
```

To test the full MCP server startup (verifies FastMCP wiring):

```bash
.venv/bin/python -c "from uat_runner.mcp_server import mcp; print(mcp.name, 'OK')"
```

### Built-in plan sync

`BUILTIN_PLANS` is defined in three places that must be kept in sync (all empty by default in the standalone repo):

- **`cli.py`** -- simple `{name: path}` dict for CLI subcommands
- **`web.py`** -- `{name: {name, label, path}}` dict for the web UI dropdown
- **`mcp_server.py`** -- `{name: path}` dict for the `list_plans` tool

When adding a new built-in plan, update all three files. See the "Adding Built-in Plans" section above for the exact format each file expects.

---

## Testing Changes

### Verify the parser

```bash
python3 -c "
from uat_runner.parser import parse_plan
sections = parse_plan('examples/example_test_plan.md')
for s in sections:
    print(f'{s.key}: {s.title} ({len(s.tests)} tests)')
"
```

### Test session creation

```bash
python3 -c "
from uat_runner.session import create_session
s = create_session('examples/example_test_plan.md', 'example', 'test', 'dev', '/tmp/uat_test')
print(f'Created: {s.id} with {s.total} tests')
"
```

### Test the API

```bash
# Start the web server
.venv/bin/python -m uat_runner web --port 8080 &

# List sessions
curl -s http://localhost:8080/api/sessions | python3 -m json.tool

# List available plans
curl -s http://localhost:8080/api/plans | python3 -m json.tool

# Create a session
curl -s -X POST http://localhost:8080/api/sessions \
  -H 'Content-Type: application/json' \
  -d '{"plan": "static", "version": "4.1.0", "tester": "dev"}' \
  | python3 -m json.tool

# Mark a test
curl -s -X PUT http://localhost:8080/api/sessions/SESSION_ID/test \
  -H 'Content-Type: application/json' \
  -d '{"section_idx": 0, "test_idx": 0, "result": "pass", "comment": ""}' \
  | python3 -m json.tool
```

### Test CLI subcommands

```bash
# List sessions
python -m uat_runner list

# Show status of a session
python -m uat_runner status SESSION_ID

# Generate reports
python -m uat_runner report SESSION_ID

# Start interactive TUI
python -m uat_runner run --plan static --version 4.1.0 --tester dev
```

### Quick smoke test after changes

```bash
# Parse all built-in plans without errors
python3 -c "
from uat_runner.parser import parse_plan
from uat_runner.cli import BUILTIN_PLANS
for name, path in BUILTIN_PLANS.items():
    try:
        sections = parse_plan(path)
        total = sum(len(s.tests) for s in sections)
        print(f'  {name}: {len(sections)} sections, {total} tests')
    except FileNotFoundError:
        print(f'  {name}: plan file not found (skip)')
"
```
