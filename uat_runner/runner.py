"""Interactive TUI test runner using Rich."""

import sys
import tty
import termios
from datetime import datetime

from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.table import Table
from rich.prompt import Prompt

from .session import save_session


console = Console()


def _getch():
    """Read a single character without requiring Enter."""
    fd = sys.stdin.fileno()
    old = termios.tcgetattr(fd)
    try:
        tty.setraw(fd)
        ch = sys.stdin.read(1)
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old)
    return ch


def _build_header(session, section_idx, test_idx):
    """Build the header text showing progress."""
    section = session.sections[section_idx]
    pct = (session.answered / session.total * 100) if session.total else 0

    lines = [
        f"[bold cyan]UAT Runner[/] — {session.plan_name} v{session.version}",
        f"[dim]Section:[/] {section.title}",
        f"[dim]Progress:[/] {session.answered}/{session.total} ({pct:.1f}%)  "
        f"[green]P:{session.passed}[/] [red]F:{session.failed}[/] "
        f"[yellow]S:{session.skipped}[/]",
    ]
    return "\n".join(lines)


def _build_test_panel(test):
    """Build the panel showing current test details."""
    content = Text()
    content.append(f"Test {test.num}:\n", style="bold white")
    content.append(f"{test.test}\n\n", style="white")
    content.append("Expected:\n", style="bold dim")
    content.append(f"{test.expected}", style="dim")

    if test.comment:
        content.append(f"\n\nComment: {test.comment}", style="italic yellow")

    return Panel(content, border_style="blue", padding=(1, 2))


def _build_keys_panel():
    """Build the key bindings panel."""
    return Panel(
        "[bold green][P][/] Pass  [bold red][F][/] Fail  "
        "[bold yellow][S][/] Skip  [bold cyan][C][/] Comment  "
        "[bold][B][/] Back  [bold][Q][/] Quit & Save",
        border_style="dim",
    )


def _get_comment():
    """Prompt for a comment (switches back to line-buffered input)."""
    console.print()
    return Prompt.ask("[yellow]Comment[/]", default="")


def run_session(session, results_dir=None):
    """Run the interactive test session.

    Args:
        session: Session object to run.
        results_dir: Directory for saving session state.

    Returns:
        The session object (updated with results).
    """
    # Find starting position
    pos = session.find_first_unanswered()
    if pos is None:
        console.print("[green]All tests in this session are already answered.[/]")
        return session

    section_idx, test_idx = pos

    # Build flat index for navigation
    flat = []
    for si, section in enumerate(session.sections):
        for ti, test in enumerate(section.tests):
            flat.append((si, ti))

    # Find current position in flat list
    flat_pos = flat.index((section_idx, test_idx))

    while True:
        si, ti = flat[flat_pos]
        section = session.sections[si]
        test = section.tests[ti]

        # Draw UI
        console.clear()
        console.print(_build_header(session, si, ti))
        console.print()
        console.print(_build_test_panel(test))
        console.print(_build_keys_panel())

        if test.is_answered():
            result_style = {"pass": "green", "fail": "red", "skip": "yellow"}
            style = result_style.get(test.result, "white")
            console.print(
                f"\n[{style}]Already marked: {test.result.upper()}[/]  "
                f"(press P/F/S to change, Enter to keep)"
            )

        # Get input
        ch = _getch()
        ch_lower = ch.lower()

        if ch_lower == "p":
            test.result = "pass"
            test.timestamp = datetime.now().isoformat(timespec="seconds")
            save_session(session, results_dir)
            # Advance to next
            if flat_pos < len(flat) - 1:
                flat_pos += 1
            else:
                # All done
                break

        elif ch_lower == "f":
            test.result = "fail"
            test.timestamp = datetime.now().isoformat(timespec="seconds")
            comment = _get_comment()
            if comment:
                test.comment = comment
            save_session(session, results_dir)
            if flat_pos < len(flat) - 1:
                flat_pos += 1
            else:
                break

        elif ch_lower == "s":
            test.result = "skip"
            test.timestamp = datetime.now().isoformat(timespec="seconds")
            save_session(session, results_dir)
            if flat_pos < len(flat) - 1:
                flat_pos += 1
            else:
                break

        elif ch_lower == "c":
            comment = _get_comment()
            if comment:
                test.comment = comment
                save_session(session, results_dir)

        elif ch_lower == "b":
            if flat_pos > 0:
                flat_pos -= 1

        elif ch_lower == "q":
            save_session(session, results_dir)
            console.print("\n[cyan]Session saved. Resume with:[/]")
            console.print(f"  [bold]uat_runner resume {session.id}[/]")
            return session

        elif ch == "\r" or ch == "\n":
            # Enter — keep current answer and advance
            if test.is_answered() and flat_pos < len(flat) - 1:
                flat_pos += 1

        elif ch == "\x03":
            # Ctrl+C
            save_session(session, results_dir)
            console.print("\n[cyan]Session saved (Ctrl+C).[/]")
            return session

    # Session complete
    save_session(session, results_dir)
    console.clear()
    _print_summary(session)
    return session


def _print_summary(session):
    """Print the end-of-session summary."""
    console.print()
    console.print(Panel(
        f"[bold green]Session Complete[/]\n\n"
        f"Plan: {session.plan_name} v{session.version}\n"
        f"Tester: {session.tester}\n"
        f"Total: {session.total}\n"
        f"[green]Pass: {session.passed}[/]  "
        f"[red]Fail: {session.failed}[/]  "
        f"[yellow]Skip: {session.skipped}[/]",
        title="UAT Summary",
        border_style="green" if session.failed == 0 else "red",
    ))

    if session.failed > 0:
        console.print()
        table = Table(title="Failures", border_style="red")
        table.add_column("#", style="bold")
        table.add_column("Section")
        table.add_column("Test")
        table.add_column("Comment", style="italic")

        for section in session.sections:
            for test in section.tests:
                if test.result == "fail":
                    table.add_row(test.num, section.title, test.test,
                                  test.comment or "")

        console.print(table)

    console.print(f"\nGenerate report: [bold]uat_runner report {session.id}[/]")
