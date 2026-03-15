# UAT Runner Usage Guide

A guided test runner that parses markdown UAT test plans and walks testers
through each step, tracking results and generating reports. Available as a
console TUI (rich) and a web UI (Flask).

---

## Purpose

UAT Runner is built for **human-in-the-loop testing of agent-developed code and applications**. When AI agents (Claude, Cursor, Copilot, etc.) build or modify software, a human must verify it works correctly before sign-off. UAT Runner bridges this gap.

### The Problem

AI agents can write code, run automated tests, and even fix bugs — but they cannot perform visual verification, test user experience, or confirm that a feature works as intended from a real user's perspective. Automated tests verify code correctness; UAT verifies that the software actually works for humans.

### The Solution

UAT Runner provides three interfaces for the same testing workflow:

- **Console TUI** — keyboard-driven terminal interface for developers
- **Web UI** — browser-based interface for testers on any device
- **MCP Server** — Model Context Protocol interface for AI agent integration

### Agent-to-Human Workflow

1. **Agent builds** — the AI agent writes code, creates features, fixes bugs
2. **Agent creates test plan** — generates a markdown test plan from requirements (or uses an existing one)
3. **Agent creates session** — calls `create_session` via MCP or CLI to set up a UAT session
4. **Human tests** — opens the web UI or console TUI and walks through each test
5. **Agent monitors** — polls `get_session` via MCP to check progress
6. **Agent reads results** — calls `read_report` via MCP to analyze pass/fail outcomes
7. **Agent acts on feedback** — fixes failures and creates a new session for re-testing

This workflow ensures that agent-built code meets human quality standards before deployment.

---

## 1. Prerequisites

- Python 3.7 or later
- No other system-level dependencies required

All Python packages (rich, openpyxl, flask) are installed automatically
during setup into an isolated virtual environment.

---

## 2. Setup

Run the setup script from the repository root:

```bash
bash setup_venv.sh
```

This creates an isolated virtual environment at `.venv/`
and installs the required packages: `rich`, `openpyxl`, and `flask`.

To recreate the venv from scratch:

```bash
rm -rf .venv
bash setup_venv.sh
```

---

## 3. Quick Start

All commands must be run from the repository root directory.

**Console TUI** -- start a new interactive session in the terminal:

```bash
.venv/bin/python -m uat_runner run --plan ./tests/my_plan.md --version 1.0.0
```

**Web UI** -- start a browser-based server:

```bash
.venv/bin/python -m uat_runner web --port 8080
```

Then open `http://localhost:8080` in a browser.

---

## 4. Console TUI Reference

### `run` -- Start a new session

```bash
.venv/bin/python -m uat_runner run --plan <PLAN> [OPTIONS]
```

| Flag | Required | Description |
|------|----------|-------------|
| `--plan` | Yes | Built-in plan name or path to markdown file |
| `--version` | No | Version being tested. If omitted, prompted interactively |
| `--tester` | No | Tester name. If omitted, prompted interactively |
| `--results-dir` | No | Custom output directory (default: `results/`) |

Examples:

```bash
# Registered built-in plan with all flags
.venv/bin/python -m uat_runner run \
  --plan myapp --version 2.0.0 --tester "Alice"

# Custom markdown plan file by path
.venv/bin/python -m uat_runner run \
  --plan /path/to/my_test_plan.md --version 1.0.0
```

### `resume <session-id>` -- Resume an interrupted session

```bash
.venv/bin/python -m uat_runner resume <session-id> [--results-dir DIR]
```

Picks up where the previous session left off. The session ID is printed when
a session is created or when you quit with `Q`.

```bash
.venv/bin/python -m uat_runner resume myapp_2.0.0_20260315_143052
```

### `status <session-id>` -- Show session progress

```bash
.venv/bin/python -m uat_runner status <session-id> [--results-dir DIR]
```

Displays session metadata and a per-section breakdown table showing total,
done, pass, fail, and skip counts for each section.

### `list` -- List all sessions

```bash
.venv/bin/python -m uat_runner list [OPTIONS]
```

| Flag | Description |
|------|-------------|
| `--plan` | Filter by plan name (e.g. `myapp`, `api`) |
| `--version` | Filter by version string |
| `--results-dir` | Directory to scan for sessions |

Displays a table with session ID, plan, version, tester, progress
percentages, and completion status.

### `report <session-id>` -- Generate reports

```bash
.venv/bin/python -m uat_runner report <session-id> [--results-dir DIR]
```

Produces both a markdown report and an XLSX spreadsheet in the results
directory. Output paths are printed to the console.

### Keyboard Shortcuts (TUI)

These keys are active during the interactive test runner:

| Key | Action |
|-----|--------|
| P | Pass -- mark current test as passed and advance |
| F | Fail -- prompt for a comment, mark as failed, and advance |
| S | Skip -- mark current test as skipped and advance |
| C | Add or edit a comment on the current test |
| B | Go back to the previous test |
| Q | Save session state and quit |
| Enter | Keep existing answer on a previously-answered test and advance |
| Ctrl+C | Emergency save and exit |

Notes:
- Keys are case-insensitive (both `p` and `P` work).
- After pressing F (fail), you are prompted for a comment describing the
  failure. This switches to line-buffered input temporarily.
- Session state is saved to disk after every action (pass, fail, skip,
  comment, quit). Saves are atomic (write to `.tmp`, then `os.replace`),
  so the session file is never corrupted even on a crash.

---

## 5. Web UI Reference

### Starting the server

```bash
.venv/bin/python -m uat_runner web [OPTIONS]
```

| Flag | Default | Description |
|------|---------|-------------|
| `--host` | `0.0.0.0` | Bind address. Default binds to all interfaces (loopback, LAN, Tailscale) |
| `--port` | `8080` | Port number |
| `--debug` | off | Enable Flask debug mode with auto-reload |
| `--results-dir` | `results/` | Directory for session files |

On startup the server prints the LAN IP address for easy sharing with
teammates on the same network:

```
UAT Runner Web UI
Listening on http://0.0.0.0:8080
LAN access: http://192.168.1.42:8080
Press Ctrl+C to stop
```

### Web UI Features

- **Session list**: shows all sessions with progress information; click any
  session to resume it.
- **New session**: pick a plan from the dropdown (built-in plans), enter a
  version string and tester name.
- **Test runner**: Pass/Fail/Skip buttons alongside each test, inline comment
  field, back/next navigation between tests.
- **Keyboard shortcuts**: P, F, S, B, and N keys work in the browser. These
  shortcuts are disabled when the cursor is in a text area (e.g. typing a
  comment).
- **Completion view**: summary of results, failures table, and report download
  buttons.
- Responsive design -- works on mobile and tablet browsers.

### API Endpoints

The web UI exposes a REST API. These endpoints can be used for scripting or
integration with other tools.

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/api/plans` | List available built-in plans |
| GET | `/api/sessions` | List all sessions (query params: `plan`, `version`) |
| POST | `/api/sessions` | Create a new session (JSON body: `plan`, `version`, `tester`) |
| GET | `/api/sessions/<id>` | Get full session state |
| PUT | `/api/sessions/<id>/test` | Mark a test result (JSON body: `section_idx`, `test_idx`, `result`, `comment`) |
| POST | `/api/sessions/<id>/report` | Generate markdown and XLSX reports |
| GET | `/api/sessions/<id>/report/md` | Download the markdown report file |
| GET | `/api/sessions/<id>/report/xlsx` | Download the XLSX report file |

Example -- create a session via API:

```bash
curl -X POST http://localhost:8080/api/sessions \
  -H "Content-Type: application/json" \
  -d '{"plan": "myapp", "version": "2.0.0", "tester": "Alice"}'
```

Example -- mark a test result:

```bash
curl -X PUT http://localhost:8080/api/sessions/myapp_2.0.0_20260315_100000/test \
  -H "Content-Type: application/json" \
  -d '{"section_idx": 0, "test_idx": 0, "result": "pass", "comment": ""}'
```

---

## 6. Built-in Plans vs Custom Plans

### Built-in plans

The `BUILTIN_PLANS` dictionary in `uat_runner/cli.py` (and `web.py`,
`mcp_server.py`) is empty by default. To register your own built-in plans,
add entries mapping a short name to the plan file path:

```python
BUILTIN_PLANS = {
    "myapp": "tests/uat/UAT_TEST_PLAN_MYAPP.md",
    "api":   "tests/uat/UAT_TEST_PLAN_API.md",
}
```

Once registered, use the short name with `--plan`:

```bash
.venv/bin/python -m uat_runner run --plan myapp --version 1.0.0
```

In the web UI, registered built-in plans appear in the dropdown menu when
creating a new session.

### Custom plans (file path)

You can also pass any markdown file path directly to `--plan` without
registering it:

```bash
.venv/bin/python -m uat_runner run \
  --plan /home/user/my_custom_tests.md --version 1.0.0
```

Custom plans work with both the console TUI and the web UI (via the API).
The session ID uses the filename stem as the plan label.

### Plan format

The parser expects this markdown structure:

```markdown
## 1. Section Title

| # | Test | Expected | Pass |
|---|------|----------|------|
| 1.1 | Do something | Something happens | |
| 1.2 | Do another thing | Another result | |

## 2. Next Section

| # | Test | Expected | Pass |
|---|------|----------|------|
| 2.1 | Check feature | Feature works | |
```

Supported heading patterns:
- `## N. Title` (numbered sections)
- `## Pre-Test: Title` (pre-test sections)
- `### Na. Sub-Section Title` (sub-sections like `### 10a. Edge Cases`)

---

## 7. Session Lifecycle

1. **Create** -- `run --plan ... --version ...` (console) or the new session
   form (web). A session JSON file is created on disk immediately.

2. **Test** -- walk through tests one at a time. Mark each as Pass, Fail, or
   Skip. Add optional comments. State is saved after every action.

3. **Interrupt** -- press Q to save and quit (console) or use "Save & Exit"
   (web). All progress is preserved.

4. **Resume** -- `resume <session-id>` (console) or click the session in the
   web UI list. Testing picks up at the first unanswered test.

5. **Complete** -- once all tests have been answered, a summary is displayed
   showing pass/fail/skip counts and listing any failures.

6. **Report** -- `report <session-id>` (console) or use the download buttons
   (web) to generate markdown and XLSX reports.

---

## 8. Session Storage

### Default location

All session files are stored in:

```
results/
```

### Overriding the location

Use `--results-dir` with any subcommand:

```bash
.venv/bin/python -m uat_runner run \
  --plan myapp --version 2.0.0 --results-dir /tmp/uat_results
```

### File naming

| File | Pattern |
|------|---------|
| Session state | `{plan}_{version}_{YYYYMMDD}_{HHMMSS}.json` |
| Markdown report | `{session_id}_report.md` |
| XLSX report | `{session_id}_report.xlsx` |

Example filenames:

```
myapp_2.0.0_20260315_143052.json
myapp_2.0.0_20260315_143052_report.md
myapp_2.0.0_20260315_143052_report.xlsx
```

### Crash safety

Session saves use atomic writes: data is written to a `.tmp` file first,
then moved into place with `os.replace`. This means the session file is
never in a half-written state, even if the process is killed mid-save.

---

## 9. Report Formats

### Markdown

The markdown report (`{session_id}_report.md`) contains:

- **Header table**: plan name, version, tester, date, duration, and overall
  verdict (PASS or FAIL).
- **Summary**: pass/fail/skip counts with percentages.
- **Failures table**: lists only the failed tests with section, test
  description, and failure comment. Present only if there are failures.
- **Skipped table**: lists skipped tests. Present only if there are skips.
- **Full results**: every test organized by section, showing the test
  description, expected result, actual result, and comment.

### XLSX

The XLSX spreadsheet (`{session_id}_report.xlsx`) contains three sheets:

- **Summary**: metadata (plan, version, tester, dates) and totals
  (pass/fail/skip/remaining counts).
- **Results**: all tests organized by section with color-coded result cells.
  Green for pass, red for fail, yellow for skip. Headers are frozen for
  scrolling. Text columns use word-wrap.
- **Failures**: failed tests only, with section name, test description,
  expected result, and comment. This sheet is only created if there are
  failures.

---

## 10. Examples

### Complete console workflow

```bash
# 1. Setup (one-time)
bash setup_venv.sh

# 2. Start a UAT session
.venv/bin/python -m uat_runner run \
  --plan ./tests/my_plan.md --version 2.0.0 --tester "Alice"

# 3. Walk through tests using P/F/S keys, quit with Q when needed

# 4. Check progress of the session
.venv/bin/python -m uat_runner status \
  my_plan_2.0.0_20260315_143052

# 5. Resume later to finish remaining tests
.venv/bin/python -m uat_runner resume \
  my_plan_2.0.0_20260315_143052

# 6. Generate reports when all tests are answered
.venv/bin/python -m uat_runner report \
  my_plan_2.0.0_20260315_143052

# 7. List all sessions across all plans
.venv/bin/python -m uat_runner list

# 8. List sessions for a specific plan and version
.venv/bin/python -m uat_runner list \
  --plan my_plan --version 2.0.0
```

### Web UI workflow

```bash
# 1. Setup (one-time)
bash setup_venv.sh

# 2. Start the web server
.venv/bin/python -m uat_runner web --port 8080

# 3. Open http://localhost:8080 in a browser
# 4. Click "New Session", pick a plan, enter version and tester name
# 5. Walk through tests using the Pass/Fail/Skip buttons or P/F/S keys
# 6. Close the tab or click "Save & Exit" to preserve progress
# 7. Return to the session list and click the session to resume
# 8. When complete, use the download buttons for markdown and XLSX reports
```

### Custom test plan

```bash
# Run a custom plan that lives outside the repository
.venv/bin/python -m uat_runner run \
  --plan ~/projects/other_app/test_plan.md \
  --version 2.0.0 \
  --tester "Bob" \
  --results-dir ~/projects/other_app/uat_results
```

### Sharing the web UI on a LAN

```bash
# The default host 0.0.0.0 already binds to all interfaces.
# The server prints the LAN IP on startup:
.venv/bin/python -m uat_runner web --port 8080

# Output:
#   UAT Runner Web UI
#   Listening on http://0.0.0.0:8080
#   LAN access: http://192.168.1.42:8080
#
# Share the LAN URL with teammates. Works over Tailscale too.
```
