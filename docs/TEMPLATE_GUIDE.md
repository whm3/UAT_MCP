# Writing Custom UAT Test Plans

A guide for authoring markdown test plans that the UAT runner parser can consume.

---

## Overview

The UAT runner parses markdown files containing test sections with tables. Each
section has a heading and a table of test cases. The parser extracts these into
structured data for the interactive test runner.

The parser lives at `uat_runner/parser.py` and uses regex to match section
headings and pipe-delimited table rows. Everything else in the file -- top-level
headings, prose paragraphs, blank lines -- is ignored.

A parsed plan produces a flat list of `Section` objects. Each section has:

- `key` -- a short identifier (e.g. `"1"`, `"10a"`, `"Pre-Test: Page Load"`)
- `title` -- the full display title (e.g. `"1. Login"`)
- `tests` -- a list of `TestCase` objects with `num`, `test`, and `expected` fields

---

## Section Heading Formats

The parser recognizes three heading formats. Each one starts a new section; any
previously open section is closed and saved before the new one begins.

### Standard sections

```markdown
## 1. Section Title
## 10. Another Section
## 25b. Section With Letter Suffix
```

Regex: `^## (\d+\w*)\.\s+(.+)$`

- Must start with `## ` (h2 level).
- The number may include letter suffixes: `1`, `10a`, `25b`.
- A period and at least one space must follow the number.
- Everything after the space is the title.
- The `key` is set to the number portion (e.g. `"25b"`).
- The `title` is set to `"25b. Section With Letter Suffix"`.

### Pre-test sections

```markdown
## Pre-Test: Page Load
## Pre-Test: Environment Setup
```

Regex: `^## (Pre-Test:\s*.+)$`

- Must start with `## Pre-Test:`.
- The entire matched text becomes both the `key` and the `title`.
- Example key: `"Pre-Test: Page Load"`.

### Sub-sections

```markdown
### 10a. Layer Slicing Behavior
### 55b. GPS Test Firmware
```

Regex: `^### (\d+\w*)\.\s+(.+)$`

- Identical rules to standard sections, but uses `###` (h3 level).
- Useful for breaking a large topic into sub-groups without promoting them to
  top-level sections.
- The `key` and `title` are derived the same way as standard sections.

### What is NOT recognized

- `# Title` (h1) -- ignored; use it for the document title.
- `#### Title` (h4 and below) -- ignored.
- Headings without a number prefix (e.g. `## Overview`) -- ignored.
- Headings missing the period after the number (e.g. `## 1 Title`) -- ignored.

---

## Test Table Format

Each section must contain a markdown table with this exact header row:

```markdown
| # | Test | Expected | Pass |
|---|------|----------|------|
| 1.1 | Click the button | Button changes color | |
| 1.2 | Enter text in field | Text appears in preview | |
```

### Header detection

The parser looks for a line starting with `| # |` to enter table mode, then
a separator line starting with `|---|` to confirm the header. Data rows are
collected after both lines have been seen.

### Data row rules

- Each row must start with `|`.
- The row is split on `|` and the leading and trailing empty segments are
  discarded, leaving the cell values.
- At least three columns must be present.
- Column mapping:
  - **Column 1** (`#`): test number -- any string, typically in `N.M` format.
  - **Column 2** (`Test`): what to do -- the action the tester should perform.
  - **Column 3** (`Expected`): what should happen -- the expected outcome.
  - **Column 4** (`Pass`): ignored by the parser. Present as a visual checkbox
    placeholder when viewing the markdown directly.
- Markdown bold (`**text**`) is automatically stripped from the Test and
  Expected columns. For example, `**Click Save**` becomes `Click Save`.

### Table termination

The table ends when the parser encounters a line that does not start with `|`.
Blank lines, new headings, and prose all terminate the current table.

### One table per section

If a section contains more than one table, only the first table's rows are
captured. Subsequent tables after a non-`|` line are ignored (because table
mode is turned off and the header detection would need to repeat within the
same section).

---

## Complete Minimal Example

```markdown
# My Application UAT Plan

## Pre-Test: Setup
| # | Test | Expected | Pass |
|---|------|----------|------|
| 0.1 | Open the application URL | Page loads without errors | |
| 0.2 | Check browser console | No JavaScript errors | |

## 1. Login
| # | Test | Expected | Pass |
|---|------|----------|------|
| 1.1 | Enter valid credentials | Login succeeds, dashboard shown | |
| 1.2 | Enter invalid password | Error message "Invalid credentials" shown | |
| 1.3 | Click "Forgot Password" | Password reset form appears | |

## 2. Dashboard
| # | Test | Expected | Pass |
|---|------|----------|------|
| 2.1 | Verify widget count | Shows 5 widgets | |
| 2.2 | Click refresh button | Data reloads within 2 seconds | |
```

This plan produces three sections with keys `"Pre-Test: Setup"`, `"1"`, and
`"2"`, containing 2, 3, and 2 test cases respectively.

---

## Complex Example with Sub-Sections

```markdown
# E-Commerce Platform UAT

## 1. Product Catalog
| # | Test | Expected | Pass |
|---|------|----------|------|
| 1.1 | Browse category page | Products listed with images and prices | |
| 1.2 | Use search bar | Relevant results appear within 1 second | |

### 1a. Product Filtering
| # | Test | Expected | Pass |
|---|------|----------|------|
| 1a.1 | Filter by price range | Only products within range shown | |
| 1a.2 | Filter by brand | Only selected brand products shown | |
| 1a.3 | Combine multiple filters | Intersection of all filters applied | |

### 1b. Product Detail Page
| # | Test | Expected | Pass |
|---|------|----------|------|
| 1b.1 | Click product thumbnail | Full-size image displayed | |
| 1b.2 | Select size/color variant | Price and availability update | |

## 2. Shopping Cart
| # | Test | Expected | Pass |
|---|------|----------|------|
| 2.1 | Add item to cart | Cart count increments, item appears in cart | |
| 2.2 | Remove item from cart | Item removed, totals recalculate | |
```

This produces four sections: `"1"`, `"1a"`, `"1b"`, and `"2"`. The sub-sections
(`1a`, `1b`) are independent sections in the parsed output -- they are not nested
inside section `1`.

---

## Content Between Tables

You can include descriptive text, notes, or prerequisites between the heading
and the table. The parser ignores all lines that are not headings or table
rows:

```markdown
## 5. Payment Processing

**Prerequisites:** Test credit card number: 4111-1111-1111-1111

Test payment flow with the staging payment gateway. Ensure you are using
the test environment credentials.

| # | Test | Expected | Pass |
|---|------|----------|------|
| 5.1 | Enter test card number | Card accepted, no validation errors | |
| 5.2 | Submit payment | "Processing" spinner shown, then success page | |
```

The prose lines before the table are silently skipped. The section key is `"5"`
and contains two tests.

---

## Tips for Good Test Plans

1. **Number tests within sections** -- use `N.M` format (section.test) for easy
   cross-referencing in bug reports and session logs.

2. **One action per test** -- each row should test one specific behavior. If a
   test requires multiple sequential actions, split them into separate rows.

3. **Be specific in the Expected column** -- "Page loads" is vague;
   "Page loads in under 3 seconds with header, sidebar, and main content
   visible" is testable and leaves no room for ambiguity.

4. **Use markdown bold for emphasis** -- the parser strips `**bold**`
   automatically, so feel free to highlight key terms in the Test and Expected
   columns when viewing the raw markdown.

5. **Keep sections focused** -- 5 to 15 tests per section is a practical range.
   Use sub-sections (`###`) to break up larger groups without inflating the
   top-level section count.

6. **Include a Pre-Test section** -- verify the test environment, credentials,
   and prerequisites are in order before the tester begins the main plan.

7. **Leave the Pass column empty** -- the parser ignores it. It exists so the
   markdown file itself can be used as a manual checklist outside the runner.

---

## Registering Custom Plans as Built-ins

To add a permanent plan shortcut so it appears in the CLI and web UI, edit the
`BUILTIN_PLANS` dict in both `cli.py` and `web.py`.

### cli.py

```python
BUILTIN_PLANS = {
    # Add your plans here -- keys are shortcut names, values are file paths:
    "myapp": os.path.join(BASE_DIR, "plans", "MY_APP_UAT.md"),
    "regression": os.path.join(BASE_DIR, "plans", "REGRESSION_TESTS.md"),
}
```

### web.py

```python
BUILTIN_PLANS = {
    "myapp": {
        "name": "myapp",
        "label": "My Application",
        "path": os.path.join(BASE_DIR, "plans", "MY_APP_UAT.md"),
    },
    "regression": {
        "name": "regression",
        "label": "Regression Tests",
        "path": os.path.join(BASE_DIR, "plans", "REGRESSION_TESTS.md"),
    },
}
```

After adding to both files, the plan is available as:

```bash
uat_runner run --plan myapp --version 1.0.0
```

It also appears in the web UI plan dropdown automatically.

---

## Using Custom Plans Without Registration

You can pass any markdown file path directly without modifying source code:

```bash
uat_runner run --plan /path/to/my_tests.md --version 1.0.0
```

The plan name is derived from the filename (without extension). Custom file
paths are only available through the CLI; the web UI dropdown shows registered
built-in plans only.

---

## Validating Your Plan

Test that your plan parses correctly before distributing it:

```bash
.venv/bin/python -c "
from uat_runner.parser import parse_plan
sections = parse_plan('path/to/your_plan.md')
total = sum(len(s.tests) for s in sections)
print(f'Parsed {len(sections)} sections, {total} tests')
for s in sections:
    print(f'  {s.key}: {s.title} ({len(s.tests)} tests)')
"
```

Expected output for the minimal example above:

```
Parsed 3 sections, 7 tests
  Pre-Test: Setup: Pre-Test: Setup (2 tests)
  1: 1. Login (3 tests)
  2: 2. Dashboard (2 tests)
```

If a section shows 0 tests, verify that:

- The table header line starts with `| # |` (exactly, with spaces around `#`).
- The separator line starts with `|---`.
- Data rows start with `|` and have at least three pipe-separated columns.
- There is no stray non-`|` line between the separator and the first data row.
