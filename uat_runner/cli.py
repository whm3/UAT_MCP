"""CLI interface for UAT runner."""

import argparse
import os
import sys

from rich.console import Console
from rich.table import Table

from .session import (
    create_session, load_session, save_session, list_sessions,
    DEFAULT_RESULTS_DIR,
)
from .runner import run_session
from .report import generate_markdown_report, generate_xlsx_report


console = Console()

# Built-in plan shortcuts — add entries here to register plans that ship
# with your project. Users can always pass file paths via --plan instead.
BUILTIN_PLANS = {}


def _resolve_plan(plan_arg):
    """Resolve plan argument to (plan_name, plan_path).

    Accepts a built-in name or a direct file path.
    """
    if plan_arg in BUILTIN_PLANS:
        path = BUILTIN_PLANS[plan_arg]
        if not os.path.exists(path):
            console.print(
                f"[red]Built-in plan '{plan_arg}' not found at {path}[/]")
            sys.exit(1)
        return plan_arg, path

    # Treat as file path
    path = os.path.abspath(plan_arg)
    if not os.path.exists(path):
        console.print(f"[red]Plan file not found: {path}[/]")
        sys.exit(1)
    name = os.path.splitext(os.path.basename(path))[0]
    return name, path


def cmd_run(args):
    """Start a new UAT session."""
    plan_name, plan_path = _resolve_plan(args.plan)

    tester = args.tester
    if not tester:
        tester = console.input("[cyan]Tester name:[/] ")
        if not tester.strip():
            console.print("[red]Tester name required.[/]")
            sys.exit(1)

    version = args.version
    if not version:
        version = console.input("[cyan]Version being tested:[/] ")
        if not version.strip():
            console.print("[red]Version required.[/]")
            sys.exit(1)

    console.print(f"\nCreating session: [bold]{plan_name}[/] v{version}")
    session = create_session(plan_path, plan_name, version, tester.strip(),
                             args.results_dir)
    console.print(f"Session ID: [bold cyan]{session.id}[/]")
    console.print(f"Tests: {session.total}")
    console.print()

    run_session(session, args.results_dir)


def cmd_resume(args):
    """Resume an existing session."""
    try:
        session = load_session(args.session_id, args.results_dir)
    except FileNotFoundError:
        console.print(f"[red]Session not found: {args.session_id}[/]")
        sys.exit(1)

    if session.is_complete:
        console.print("[green]This session is already complete.[/]")
        console.print(
            f"Generate report: [bold]uat_runner report {session.id}[/]")
        return

    console.print(f"Resuming: [bold]{session.plan_name}[/] v{session.version}")
    console.print(
        f"Progress: {session.answered}/{session.total} "
        f"({session.remaining} remaining)")
    console.print()

    run_session(session, args.results_dir)


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


def cmd_status(args):
    """Show session status."""
    try:
        session = load_session(args.session_id, args.results_dir)
    except FileNotFoundError:
        console.print(f"[red]Session not found: {args.session_id}[/]")
        sys.exit(1)

    console.print(f"\n[bold]{session.plan_name}[/] v{session.version}")
    console.print(f"Tester: {session.tester}")
    console.print(f"Started: {session.started}")
    console.print(f"Updated: {session.updated}")
    if session.completed:
        console.print(f"Completed: {session.completed}")

    pct = (session.answered / session.total * 100) if session.total else 0
    console.print(
        f"\nProgress: {session.answered}/{session.total} ({pct:.1f}%)")
    console.print(
        f"  [green]Pass: {session.passed}[/]  "
        f"[red]Fail: {session.failed}[/]  "
        f"[yellow]Skip: {session.skipped}[/]  "
        f"Remaining: {session.remaining}")

    # Per-section breakdown
    console.print()
    table = Table(title="Sections", border_style="dim")
    table.add_column("Section", style="bold")
    table.add_column("Total", justify="right")
    table.add_column("Done", justify="right")
    table.add_column("Pass", justify="right", style="green")
    table.add_column("Fail", justify="right", style="red")
    table.add_column("Skip", justify="right", style="yellow")

    for section in session.sections:
        total = len(section.tests)
        done = sum(1 for t in section.tests if t.is_answered())
        passed = sum(1 for t in section.tests if t.result == "pass")
        failed = sum(1 for t in section.tests if t.result == "fail")
        skipped = sum(1 for t in section.tests if t.result == "skip")
        table.add_row(section.title, str(total), str(done),
                      str(passed), str(failed), str(skipped))

    console.print(table)


def cmd_web(args):
    """Start the web UI server."""
    from .web import create_web_app

    app = create_web_app(args.results_dir)
    host = args.host
    port = args.port

    console.print(f"\n[bold cyan]UAT Runner Web UI[/]")
    console.print(f"Listening on [bold]http://{host}:{port}[/]")
    if host == "0.0.0.0":
        import socket
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            local_ip = s.getsockname()[0]
            s.close()
            console.print(f"LAN access: [bold]http://{local_ip}:{port}[/]")
        except Exception:
            pass
    console.print("[dim]Press Ctrl+C to stop[/]\n")

    app.run(host=host, port=port, debug=args.debug)


def cmd_list(args):
    """List all sessions."""
    sessions = list_sessions(args.results_dir, args.plan, args.version)

    if not sessions:
        console.print("[dim]No sessions found.[/]")
        return

    table = Table(title="UAT Sessions", border_style="dim")
    table.add_column("ID", style="bold cyan")
    table.add_column("Plan")
    table.add_column("Version")
    table.add_column("Tester")
    table.add_column("Progress", justify="right")
    table.add_column("P", justify="right", style="green")
    table.add_column("F", justify="right", style="red")
    table.add_column("S", justify="right", style="yellow")
    table.add_column("Status")

    for s in sessions:
        pct = (s["answered"] / s["total"] * 100) if s["total"] else 0
        progress = f"{s['answered']}/{s['total']} ({pct:.0f}%)"
        status = "[green]Complete[/]" if s["completed"] else "[yellow]In progress[/]"
        table.add_row(
            s["id"], s["plan_name"], s["version"], s["tester"],
            progress, str(s["pass"]), str(s["fail"]), str(s["skip"]),
            status,
        )

    console.print(table)


def _add_results_dir(parser):
    """Add --results-dir flag to a subparser."""
    parser.add_argument(
        "--results-dir",
        default=None,
        help=f"Directory for session files (default: {DEFAULT_RESULTS_DIR})",
    )


def main():
    parser = argparse.ArgumentParser(
        prog="uat_runner",
        description="Guided UAT test runner with session tracking and reports",
    )

    sub = parser.add_subparsers(dest="command", required=True)

    # run
    p_run = sub.add_parser("run", help="Start a new UAT session")
    p_run.add_argument(
        "--plan", required=True,
        help="Built-in plan name or path to markdown file",
    )
    p_run.add_argument("--version", help="Version being tested")
    p_run.add_argument("--tester", help="Tester name")
    _add_results_dir(p_run)

    # resume
    p_resume = sub.add_parser("resume", help="Resume an interrupted session")
    p_resume.add_argument("session_id", help="Session ID to resume")
    _add_results_dir(p_resume)

    # report
    p_report = sub.add_parser("report", help="Generate reports for a session")
    p_report.add_argument("session_id", help="Session ID")
    _add_results_dir(p_report)

    # status
    p_status = sub.add_parser("status", help="Show session status")
    p_status.add_argument("session_id", help="Session ID")
    _add_results_dir(p_status)

    # list
    p_list = sub.add_parser("list", help="List all sessions")
    p_list.add_argument("--plan", help="Filter by plan name")
    p_list.add_argument("--version", help="Filter by version")
    _add_results_dir(p_list)

    # web
    p_web = sub.add_parser("web", help="Start web UI server")
    p_web.add_argument("--host", default="0.0.0.0",
                       help="Bind address (default: 0.0.0.0 for all interfaces)")
    p_web.add_argument("--port", type=int, default=8080,
                       help="Port (default: 8080)")
    p_web.add_argument("--debug", action="store_true",
                       help="Enable Flask debug mode")
    _add_results_dir(p_web)

    args = parser.parse_args()

    commands = {
        "run": cmd_run,
        "resume": cmd_resume,
        "report": cmd_report,
        "status": cmd_status,
        "list": cmd_list,
        "web": cmd_web,
    }
    commands[args.command](args)
