# UAT Runner

Human-in-the-loop UAT testing tool for agent-developed code and applications.

AI agents build software. Humans verify it works. UAT Runner bridges the gap
with structured test sessions, progress tracking, and reports.

## Interfaces

- **Console TUI** — keyboard-driven terminal interface (rich)
- **Web UI** — browser-based interface for any device (Flask)
- **MCP Server** — Model Context Protocol for AI agent integration

## Quick Start

```bash
# Setup
bash setup_venv.sh

# Console TUI — start a new session
.venv/bin/python -m uat_runner run --plan /path/to/test_plan.md --version 1.0.0

# Web UI — start browser-based server
.venv/bin/python -m uat_runner web --port 8080

# MCP Server — for AI agent integration
.venv/bin/python -m uat_runner.mcp_server
```

## Agent Workflow

1. Agent builds code
2. Agent creates a UAT session (via MCP or CLI)
3. Human tests via web UI or console TUI
4. Agent monitors progress and reads results
5. Agent fixes failures, creates new session, iterates

## Documentation

- [Usage Guide](docs/USAGE.md) — full CLI and web UI reference
- [MCP Integration](docs/MCP_INTEGRATION.md) — AI agent setup and tool reference
- [Template Guide](docs/TEMPLATE_GUIDE.md) — writing custom test plans
- [Best Practices](docs/BEST_PRACTICES.md) — glass-to-glass testing methodology
- [Extending](docs/EXTENDING.md) — developer guide for adding features

## Test Plan Format

Test plans are markdown files with numbered section headings and tables:

```markdown
## 1. Login

| # | Test | Expected | Pass |
|---|------|----------|------|
| 1.1 | Enter valid credentials | Redirects to dashboard | |
| 1.2 | Enter invalid password | Shows error message | |

## 2. Dashboard

| # | Test | Expected | Pass |
|---|------|----------|------|
| 2.1 | Page loads | Shows user name and stats | |
```

See [examples/example_test_plan.md](examples/example_test_plan.md) for a
complete working example.

## Requirements

- Python 3.7+
- No other system dependencies

All Python packages are installed automatically by `setup_venv.sh` into an
isolated virtual environment.
