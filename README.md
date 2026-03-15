# UAT Runner

Human-in-the-loop UAT testing tool for agent-developed code and applications.

AI agents can write code, run automated tests, and fix bugs — but they cannot
click buttons, judge visual layouts, or confirm that a feature feels right to a
real user. UAT Runner closes that gap. Agents create structured test sessions,
humans walk through them step by step, and agents read the results to decide
what to fix next.

## Why This Exists

Every AI coding agent (Claude, Cursor, Copilot, etc.) eventually hits the same
wall: automated tests pass, but nobody has actually used the software. UAT
Runner gives agents a formal way to hand off to a human for verification, then
pick up the results programmatically and keep iterating.

```
Agent builds code
       |
       v
Agent creates UAT session (MCP / CLI)
       |
       v
Human tests via Web UI or Console TUI
       |
       v
Agent reads results, fixes failures
       |
       v
Agent creates new session, repeats
```

## Three Interfaces, One Workflow

| Interface | For | How |
|-----------|-----|-----|
| **Console TUI** | Developers on the test host | `python -m uat_runner run --plan plan.md` |
| **Web UI** | Testers on any device (phone, tablet, laptop) | `python -m uat_runner web --port 8080` |
| **MCP Server** | AI agents (Claude Code, Claude Desktop, etc.) | `python -m uat_runner.mcp_server` |

All three read and write the same session files. Start in the console, resume
in the browser, check progress from your agent — they're interchangeable.

## Quick Start

```bash
# 1. Clone and setup
git clone git@github.com:whm3/UAT_MCP.git
cd UAT_MCP
bash setup_venv.sh

# 2. Run the example test plan
.venv/bin/python -m uat_runner run \
  --plan examples/example_test_plan.md \
  --version 1.0.0 \
  --tester "Your Name"

# 3. Or start the web UI
.venv/bin/python -m uat_runner web --port 8080
# Open http://localhost:8080 in a browser
```

### Console TUI Keyboard Shortcuts

| Key | Action |
|-----|--------|
| P | Pass |
| F | Fail (prompts for comment) |
| S | Skip |
| B | Back to previous test |
| Q | Save and quit |

### Web UI

The web server binds to `0.0.0.0` by default so testers on the same network
can access it. On startup it prints the LAN IP:

```
UAT Runner Web UI
Listening on http://0.0.0.0:8080
LAN access: http://192.168.1.42:8080
```

Best practice: run the software under test on one machine, run UAT Runner on
(or access it from) a different device. This "glass-to-glass" approach catches
issues that same-machine testing misses.

## MCP Server

The MCP server lets AI agents create sessions, monitor progress, and read
results programmatically via the Model Context Protocol (stdio transport).

### Registration

**Claude Code** — add to `.claude/settings.json`:

```json
{
  "mcpServers": {
    "uat-runner": {
      "command": "python",
      "args": ["-m", "uat_runner.mcp_server"],
      "cwd": "/path/to/UAT_MCP"
    }
  }
}
```

**Claude Desktop** — add to `claude_desktop_config.json` with the same format.

### Available Tools

| Tool | Purpose |
|------|---------|
| `list_plans` | List registered built-in test plans |
| `create_session` | Create a new UAT session from a plan file |
| `get_session` | Get full session state with all results |
| `list_sessions` | List sessions, optionally filtered |
| `mark_test` | Mark a test pass/fail/skip |
| `get_next_test` | Get the next unanswered test |
| `generate_report` | Generate markdown + XLSX reports |
| `read_report` | Read the markdown report content |

See [docs/MCP_INTEGRATION.md](docs/MCP_INTEGRATION.md) for full parameter
documentation and agent workflow examples.

## Test Plan Format

Test plans are plain markdown. The parser looks for numbered section headings
and pipe-delimited tables:

```markdown
## 1. User Authentication

| # | Test | Expected | Pass |
|---|------|----------|------|
| 1.1 | Enter valid credentials and click Login | Redirects to dashboard | |
| 1.2 | Enter invalid password and click Login | Shows error message | |

## 2. Dashboard

| # | Test | Expected | Pass |
|---|------|----------|------|
| 2.1 | Load the dashboard page | Shows user name and statistics | |
| 2.2 | Resize browser to mobile width | Layout adapts to single column | |
```

Supported heading formats:
- `## N. Title` — numbered sections
- `## Pre-Test: Title` — pre-test setup sections
- `### Na. Title` — sub-sections (e.g. `### 3a. Edge Cases`)

See [examples/example_test_plan.md](examples/example_test_plan.md) for a
complete working example, or [docs/TEMPLATE_GUIDE.md](docs/TEMPLATE_GUIDE.md)
for the full format reference.

## Reports

After testing, generate markdown and XLSX reports:

```bash
# CLI
.venv/bin/python -m uat_runner report <session-id>

# Web UI — click "Generate Reports" on the completion screen

# MCP — agent calls generate_report() then read_report()
```

Reports include:
- Summary with pass/fail/skip counts and overall verdict
- Failures table with tester comments
- Full results organized by section
- XLSX with color-coded cells (green/red/yellow)

## Session Storage

Sessions are saved as JSON files in `results/` (override with `--results-dir`).
Saves are atomic — write to `.tmp` then `os.replace` — so sessions are never
corrupted, even on crashes or Ctrl+C.

```
results/
  myapp_2.0.0_20260315_140000.json        # Session state
  myapp_2.0.0_20260315_140000_report.md   # Markdown report
  myapp_2.0.0_20260315_140000_report.xlsx # XLSX report
```

## Project Structure

```
UAT_MCP/
├── uat_runner/           # Python package
│   ├── cli.py            # CLI with 6 subcommands
│   ├── web.py            # Flask web UI + REST API
│   ├── mcp_server.py     # MCP server (8 tools)
│   ├── models.py         # TestCase, Section, Session dataclasses
│   ├── parser.py         # Markdown test plan parser
│   ├── runner.py         # Console TUI (rich)
│   ├── session.py        # Session CRUD with atomic saves
│   ├── report.py         # Markdown + XLSX report generation
│   └── templates/
│       └── index.html    # Web UI (single-page, dark theme)
├── docs/                 # Full documentation
├── examples/             # Example test plan
├── results/              # Session files and reports
├── requirements.txt      # Python dependencies
└── setup_venv.sh         # Venv bootstrap script
```

## Requirements

- Python 3.7+
- No other system dependencies

All Python packages (`rich`, `openpyxl`, `flask`, `mcp`) are installed
automatically by `setup_venv.sh` into an isolated `.venv/`.

## Documentation

| Guide | Content |
|-------|---------|
| [Usage](docs/USAGE.md) | Full CLI and web UI reference |
| [MCP Integration](docs/MCP_INTEGRATION.md) | Agent setup, tool reference, workflow examples |
| [Template Guide](docs/TEMPLATE_GUIDE.md) | Writing custom test plans |
| [Best Practices](docs/BEST_PRACTICES.md) | Glass-to-glass testing, network setup |
| [Extending](docs/EXTENDING.md) | Adding commands, endpoints, report formats |
| [UAT Test Plan](docs/UAT_TEST_PLAN.md) | Self-dogfooding test plan (142 tests) |

## License

MIT
