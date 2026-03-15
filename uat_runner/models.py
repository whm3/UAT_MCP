"""Data models for UAT runner sessions and test cases."""

from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Optional


@dataclass
class TestCase:
    """A single test case parsed from a UAT markdown table."""
    num: str
    test: str
    expected: str
    result: Optional[str] = None       # "pass", "fail", "skip", or None
    comment: str = ""
    timestamp: Optional[str] = None    # ISO format when result was recorded

    def is_answered(self):
        return self.result is not None

    def to_dict(self):
        return asdict(self)

    @classmethod
    def from_dict(cls, d):
        return cls(**d)


@dataclass
class Section:
    """A section of related test cases (parsed from ## heading)."""
    key: str            # e.g. "1", "10a", "Pre-Test: Page Load"
    title: str          # e.g. "1. Single-Track Flight Planning"
    tests: list = field(default_factory=list)  # list of TestCase

    def to_dict(self):
        return {
            "key": self.key,
            "title": self.title,
            "tests": [t.to_dict() for t in self.tests],
        }

    @classmethod
    def from_dict(cls, d):
        return cls(
            key=d["key"],
            title=d["title"],
            tests=[TestCase.from_dict(t) for t in d["tests"]],
        )


@dataclass
class Session:
    """A UAT test session with all state needed for save/resume."""
    id: str
    plan_name: str          # "static", "flask", "firmware" or custom label
    plan_path: str          # absolute path to the markdown file
    version: str
    tester: str
    started: str            # ISO datetime
    updated: str            # ISO datetime
    completed: Optional[str] = None  # ISO datetime when all tests done
    sections: list = field(default_factory=list)  # list of Section

    @property
    def total(self):
        return sum(len(s.tests) for s in self.sections)

    @property
    def answered(self):
        return sum(1 for s in self.sections for t in s.tests if t.is_answered())

    @property
    def passed(self):
        return sum(1 for s in self.sections for t in s.tests if t.result == "pass")

    @property
    def failed(self):
        return sum(1 for s in self.sections for t in s.tests if t.result == "fail")

    @property
    def skipped(self):
        return sum(1 for s in self.sections for t in s.tests if t.result == "skip")

    @property
    def remaining(self):
        return self.total - self.answered

    @property
    def is_complete(self):
        return self.remaining == 0

    def summary_dict(self):
        return {
            "total": self.total,
            "pass": self.passed,
            "fail": self.failed,
            "skip": self.skipped,
            "remaining": self.remaining,
        }

    def to_dict(self):
        return {
            "id": self.id,
            "plan_name": self.plan_name,
            "plan_path": self.plan_path,
            "version": self.version,
            "tester": self.tester,
            "started": self.started,
            "updated": self.updated,
            "completed": self.completed,
            "sections": [s.to_dict() for s in self.sections],
            "summary": self.summary_dict(),
        }

    @classmethod
    def from_dict(cls, d):
        return cls(
            id=d["id"],
            plan_name=d["plan_name"],
            plan_path=d["plan_path"],
            version=d["version"],
            tester=d["tester"],
            started=d["started"],
            updated=d["updated"],
            completed=d.get("completed"),
            sections=[Section.from_dict(s) for s in d["sections"]],
        )

    def find_first_unanswered(self):
        """Return (section_idx, test_idx) of first unanswered test, or None."""
        for si, section in enumerate(self.sections):
            for ti, test in enumerate(section.tests):
                if not test.is_answered():
                    return (si, ti)
        return None
