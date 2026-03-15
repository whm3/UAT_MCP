"""MCP server for UAT runner — exposes test session management to AI agents.

This server enables AI agents to programmatically create UAT sessions,
monitor test progress, and read results. The actual testing is done by
a human via the console TUI or web UI (human-in-the-loop).

Typical agent workflow:
  1. Agent builds an application
  2. Agent calls create_session() to set up UAT
  3. Agent tells human to run tests via web UI or console
  4. Agent polls get_session() to monitor progress
  5. Agent calls read_report() to get results

Run: python -m uat_runner.mcp_server
Transport: stdio (for Claude Code / Claude Desktop integration)
"""

import os

from mcp.server.fastmcp import FastMCP

from .session import (
    create_session as _create_session,
    load_session,
    save_session,
    list_sessions as _list_sessions,
    DEFAULT_RESULTS_DIR,
)
from .report import (
    generate_markdown_report,
    generate_xlsx_report,
)

# Built-in plan shortcuts — add entries here to register plans that ship
# with your project. Users can always pass absolute file paths instead.
BUILTIN_PLANS = {}

mcp = FastMCP(
    "uat-runner",
    instructions=(
        "Human-in-the-loop UAT testing tool. Use this to create test "
        "sessions for code you have built, so a human can verify it works. "
        "Create a session, tell the user to run tests via the web UI "
        "(uat_runner web --port 8080), then check results when they finish."
    ),
)


@mcp.tool()
def list_plans() -> dict:
    """List available built-in test plans.

    Returns the plans that can be used with create_session().
    Each plan has a name (used as the plan argument) and a
    human-readable label.
    """
    plans = []
    for key, info in BUILTIN_PLANS.items():
        if os.path.exists(info["path"]):
            plans.append({
                "name": info["name"],
                "label": info["label"],
                "test_count": _count_tests(info["path"]),
            })
    return {"plans": plans}


@mcp.tool()
def create_session(plan: str, version: str, tester: str) -> dict:
    """Create a new UAT test session for human testing.

    After creating the session, tell the human tester to open the web UI
    and begin testing. Use get_session() to monitor their progress.

    Args:
        plan: Built-in plan name or absolute path to a custom markdown
              test plan file.
        version: Version string being tested (e.g. '4.1.0').
        tester: Name of the person who will run the tests.

    Returns:
        Full session state including id, plan_name, version, sections,
        and summary with test counts.
    """
    if plan in BUILTIN_PLANS:
        plan_name = BUILTIN_PLANS[plan]["name"]
        plan_path = BUILTIN_PLANS[plan]["path"]
    else:
        plan_path = os.path.abspath(plan)
        plan_name = os.path.splitext(os.path.basename(plan_path))[0]

    if not os.path.exists(plan_path):
        return {"error": f"Plan not found: {plan_path}"}

    session = _create_session(plan_path, plan_name, version, tester)
    return session.to_dict()


@mcp.tool()
def get_session(session_id: str) -> dict:
    """Get the full state of a UAT session including all test results.

    Use this to check progress on a session that a human is running.
    The summary field shows pass/fail/skip/remaining counts.

    Args:
        session_id: The session ID returned by create_session().

    Returns:
        Full session state with sections, tests, results, and summary.
    """
    try:
        session = load_session(session_id)
        return session.to_dict()
    except FileNotFoundError:
        return {"error": f"Session not found: {session_id}"}


@mcp.tool()
def list_sessions(plan: str = "", version: str = "") -> dict:
    """List all UAT sessions, optionally filtered by plan or version.

    Args:
        plan: Filter by plan name (e.g. 'static'). Empty for all.
        version: Filter by version string. Empty for all.

    Returns:
        List of session metadata with id, plan, version, tester,
        progress counts, and completion status.
    """
    sessions = _list_sessions(
        plan_name=plan if plan else None,
        version=version if version else None,
    )
    return {"sessions": sessions}


@mcp.tool()
def mark_test(
    session_id: str,
    section_idx: int,
    test_idx: int,
    result: str,
    comment: str = "",
) -> dict:
    """Mark a single test result in a UAT session.

    Normally humans mark tests via the web UI or console TUI, but
    agents can also mark tests programmatically if needed (e.g. for
    automated pre-checks before human testing begins).

    Args:
        session_id: The session ID.
        section_idx: Section index (0-based).
        test_idx: Test index within the section (0-based).
        result: One of 'pass', 'fail', or 'skip'.
        comment: Optional comment explaining the result.

    Returns:
        Updated session state with new summary counts.
    """
    if result not in ("pass", "fail", "skip"):
        return {"error": f"Invalid result '{result}'. Must be pass/fail/skip."}

    try:
        session = load_session(session_id)
    except FileNotFoundError:
        return {"error": f"Session not found: {session_id}"}

    try:
        test = session.sections[section_idx].tests[test_idx]
    except IndexError:
        return {"error": f"Invalid index: section {section_idx}, test {test_idx}"}

    from datetime import datetime
    test.result = result
    test.comment = comment
    test.timestamp = datetime.now().isoformat(timespec="seconds")

    save_session(session)
    return session.to_dict()


@mcp.tool()
def get_next_test(session_id: str) -> dict:
    """Get the next unanswered test in a session.

    Use this to find what test the human should work on next,
    or to check if all tests are complete.

    Args:
        session_id: The session ID.

    Returns:
        Test details (section_idx, test_idx, section_title, test number,
        test description, expected result) or {complete: true} if all
        tests are answered.
    """
    try:
        session = load_session(session_id)
    except FileNotFoundError:
        return {"error": f"Session not found: {session_id}"}

    pos = session.find_first_unanswered()
    if pos is None:
        return {
            "complete": True,
            "summary": session.summary_dict(),
        }

    si, ti = pos
    section = session.sections[si]
    test = section.tests[ti]
    return {
        "complete": False,
        "section_idx": si,
        "test_idx": ti,
        "section_title": section.title,
        "test_num": test.num,
        "test": test.test,
        "expected": test.expected,
        "summary": session.summary_dict(),
    }


@mcp.tool()
def generate_report(session_id: str) -> dict:
    """Generate markdown and XLSX reports for a completed session.

    Call this after all tests are answered (or at any point for a
    progress snapshot). Reports are saved to the results directory.

    Args:
        session_id: The session ID.

    Returns:
        Paths to the generated markdown and XLSX report files.
    """
    try:
        session = load_session(session_id)
    except FileNotFoundError:
        return {"error": f"Session not found: {session_id}"}

    results_dir = os.path.abspath(DEFAULT_RESULTS_DIR)

    md_path = os.path.join(results_dir, f"{session.id}_report.md")
    generate_markdown_report(session, md_path)

    xlsx_path = os.path.join(results_dir, f"{session.id}_report.xlsx")
    generate_xlsx_report(session, xlsx_path)

    return {
        "markdown_path": md_path,
        "xlsx_path": xlsx_path,
        "summary": session.summary_dict(),
    }


@mcp.tool()
def read_report(session_id: str) -> dict:
    """Read the generated markdown report for a session.

    Call generate_report() first to create the report. This returns
    the full markdown content so you can analyze the test results.

    Args:
        session_id: The session ID.

    Returns:
        The markdown report content as a string, or an error if
        the report hasn't been generated yet.
    """
    results_dir = os.path.abspath(DEFAULT_RESULTS_DIR)
    md_path = os.path.join(results_dir, f"{session_id}_report.md")

    if not os.path.exists(md_path):
        return {"error": "Report not found. Call generate_report() first."}

    with open(md_path, "r") as f:
        content = f.read()

    return {"content": content}


def _count_tests(plan_path):
    """Count tests in a plan file without full parsing."""
    try:
        from .parser import parse_plan
        sections = parse_plan(plan_path)
        return sum(len(s.tests) for s in sections)
    except Exception:
        return 0


if __name__ == "__main__":
    mcp.run(transport="stdio")
