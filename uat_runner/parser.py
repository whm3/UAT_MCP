"""Parse UAT markdown test plans into Section/TestCase models.

Supports any markdown file using the format:
  ## N. Section Title
  | # | Test | Expected | Pass |
  |---|------|----------|------|
  | 1.1 | Do something | Something happens | |

Also handles:
  ## Pre-Test: Title
  ### Na. Sub-Section Title
"""

import re
from .models import TestCase, Section


def parse_plan(path):
    """Parse a UAT markdown file and return a list of Section objects.

    Args:
        path: Path to the markdown file.

    Returns:
        List of Section objects, each containing TestCase objects.
    """
    with open(path, "r") as f:
        lines = f.readlines()

    sections = []
    current_key = None
    current_title = None
    current_rows = []
    in_table = False
    header_seen = False

    def flush_section():
        nonlocal current_key, current_title, current_rows
        if current_key is not None:
            tests = [TestCase(num=r[0], test=r[1], expected=r[2])
                     for r in current_rows]
            sections.append(Section(key=current_key, title=current_title,
                                    tests=tests))
        current_key = None
        current_title = None
        current_rows = []

    for line in lines:
        line = line.rstrip("\n")

        # Detect section heading: ## 1. Title or ## 10a. Title
        m = re.match(r"^## (\d+\w*)\.\s+(.+)$", line)
        if m:
            flush_section()
            current_key = m.group(1)
            current_title = f"{m.group(1)}. {m.group(2)}"
            in_table = False
            header_seen = False
            continue

        # ## Pre-Test: Page Load
        m2 = re.match(r"^## (Pre-Test:\s*.+)$", line)
        if m2:
            flush_section()
            current_key = m2.group(1).strip()
            current_title = current_key
            in_table = False
            header_seen = False
            continue

        # ### 10a. Sub-Section Title
        m3 = re.match(r"^### (\d+\w*)\.\s+(.+)$", line)
        if m3:
            flush_section()
            current_key = m3.group(1)
            current_title = f"{m3.group(1)}. {m3.group(2)}"
            in_table = False
            header_seen = False
            continue

        if current_key is None:
            continue

        # Detect table header
        if line.startswith("| # |"):
            in_table = True
            header_seen = False
            continue
        if line.startswith("|---|"):
            header_seen = True
            continue

        # Parse table rows
        if in_table and header_seen and line.startswith("|"):
            cols = [c.strip() for c in line.split("|")]
            cols = cols[1:-1]  # strip empty first/last from split
            if len(cols) >= 3:
                num = cols[0].strip()
                test = cols[1].strip()
                expected = cols[2].strip()
                # Strip markdown bold
                test = re.sub(r"\*\*(.+?)\*\*", r"\1", test)
                expected = re.sub(r"\*\*(.+?)\*\*", r"\1", expected)
                current_rows.append((num, test, expected))
        elif in_table and not line.startswith("|"):
            in_table = False
            header_seen = False

    # Save last section
    flush_section()

    return sections
