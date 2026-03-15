"""Session management: create, save, load, resume, list."""

import json
import os
from datetime import datetime
from .models import Session
from .parser import parse_plan


# Default results directory (relative to this package).
# Can be overridden via --results-dir CLI flag.
DEFAULT_RESULTS_DIR = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "..", "results",
)


def _results_dir(results_dir=None):
    d = results_dir or DEFAULT_RESULTS_DIR
    d = os.path.abspath(d)
    os.makedirs(d, exist_ok=True)
    return d


def _session_path(session_id, results_dir=None):
    return os.path.join(_results_dir(results_dir), f"{session_id}.json")


def create_session(plan_path, plan_name, version, tester, results_dir=None):
    """Create a new UAT session from a markdown plan file.

    Args:
        plan_path: Absolute path to the markdown test plan.
        plan_name: Short label (e.g. "static", "flask", "firmware").
        version: Version string being tested.
        tester: Name of the person running the tests.
        results_dir: Directory to store session JSON files.

    Returns:
        A new Session object (already saved to disk).
    """
    sections = parse_plan(plan_path)
    now = datetime.now().strftime("%Y%m%d_%H%M%S")
    session_id = f"{plan_name}_{version}_{now}"

    session = Session(
        id=session_id,
        plan_name=plan_name,
        plan_path=os.path.abspath(plan_path),
        version=version,
        tester=tester,
        started=datetime.now().isoformat(timespec="seconds"),
        updated=datetime.now().isoformat(timespec="seconds"),
        sections=sections,
    )

    save_session(session, results_dir)
    return session


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


def load_session(session_id, results_dir=None):
    """Load a session from its JSON file.

    Args:
        session_id: The session ID string.
        results_dir: Directory containing session files.

    Returns:
        Session object.

    Raises:
        FileNotFoundError: If session file doesn't exist.
    """
    path = _session_path(session_id, results_dir)
    with open(path, "r") as f:
        data = json.load(f)
    return Session.from_dict(data)


def list_sessions(results_dir=None, plan_name=None, version=None):
    """List all sessions, optionally filtered by plan name and/or version.

    Returns:
        List of dicts with session metadata (id, plan_name, version,
        tester, started, status, progress).
    """
    d = _results_dir(results_dir)
    sessions = []

    for fname in sorted(os.listdir(d)):
        if not fname.endswith(".json"):
            continue
        path = os.path.join(d, fname)
        try:
            with open(path, "r") as f:
                data = json.load(f)
        except (json.JSONDecodeError, KeyError):
            continue

        if plan_name and data.get("plan_name") != plan_name:
            continue
        if version and data.get("version") != version:
            continue

        summary = data.get("summary", {})
        total = summary.get("total", 0)
        remaining = summary.get("remaining", total)
        answered = total - remaining

        sessions.append({
            "id": data["id"],
            "plan_name": data["plan_name"],
            "version": data["version"],
            "tester": data.get("tester", ""),
            "started": data.get("started", ""),
            "completed": data.get("completed"),
            "total": total,
            "answered": answered,
            "pass": summary.get("pass", 0),
            "fail": summary.get("fail", 0),
            "skip": summary.get("skip", 0),
        })

    return sessions
