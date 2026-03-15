# UAT Runner — Self-Test Plan

**Purpose**: User acceptance testing for the UAT runner tool itself. This plan exercises every feature of the console TUI, web UI, CLI subcommands, session management, report generation, and parser — allowing the tool to dogfood its own test format.

**Scope**:
- Console TUI (rich-based interactive runner)
- Web UI (Flask, dark theme, responsive)
- CLI subcommands: run, resume, report, status, list, web
- Session storage (JSON in results directory)
- Report generation (markdown + XLSX)
- Built-in plans and custom plan support
- Parser (markdown table extraction)
- Interoperability between console and web interfaces
- Edge cases and error handling

---

## Pre-Test: Environment Setup

| # | Test | Expected | Pass |
|---|------|----------|------|
| 0.1 | Run `bash setup_venv.sh` | Venv created at .venv/, dependencies installed, usage instructions printed to stdout | |
| 0.2 | Verify Python version: `python3 --version` | Python 3.7 or higher reported | |
| 0.3 | Verify dependencies: `.venv/bin/pip list` | rich, openpyxl, and flask all appear in installed packages list | |
| 0.4 | Verify module execution: run `.venv/bin/python -m uat_runner list --results-dir /tmp/uat_selftest` from repo root | Command executes without import errors; prints "No sessions found" | |
| 0.5 | Verify example plan exists: check that `examples/example_test_plan.md` exists on disk | File present and parseable | |

---

## 1. Console — Session Creation

| # | Test | Expected | Pass |
|---|------|----------|------|
| 1.1 | Run `uat_runner run --plan /path/to/plan.md --version 1.0.0 --tester "Alice" --results-dir /tmp/uat_selftest` | Session created, session ID printed, TUI starts showing first test from the plan | |
| 1.2 | Run `uat_runner run --plan /path/to/docs/UAT_TEST_PLAN.md --version 1.0.0 --tester "Alice" --results-dir /tmp/uat_selftest` (this file) | Session created using plan path, plan_name derived from filename, TUI starts | |
| 1.3 | Run `uat_runner run --plan /path/to/plan.md --tester "Alice" --results-dir /tmp/uat_selftest` (omit --version) | Interactive prompt asks "Version being tested:", entering a value proceeds to session creation | |
| 1.4 | Run `uat_runner run --plan /path/to/plan.md --version 1.0.0 --results-dir /tmp/uat_selftest` (omit --tester) | Interactive prompt asks "Tester name:", entering a value proceeds to session creation | |
| 1.5 | Run `uat_runner run --plan nonexistent_plan --version 1.0.0 --tester "Alice" --results-dir /tmp/uat_selftest` | Error message "Plan file not found" printed in red, process exits with non-zero code, no crash or traceback | |
| 1.6 | Run `uat_runner run --plan /path/to/plan.md --version 1.0.0 --tester "Alice" --results-dir /tmp/uat_custom_dir` | Session JSON file saved to /tmp/uat_custom_dir/, not the default results directory | |
| 1.7 | After creating a session, verify the JSON file exists in the results directory | File named {plan}_{version}_{timestamp}.json exists, is valid JSON, contains sections and tests arrays | |
| 1.8 | Run with --version omitted, then press Enter at the version prompt without typing anything | Error message "Version required" printed, process exits without creating a session | |
| 1.9 | Run with --tester omitted, then press Enter at the tester prompt without typing anything | Error message "Tester name required" printed, process exits without creating a session | |

---

## 2. Console — TUI Navigation

| # | Test | Expected | Pass |
|---|------|----------|------|
| 2.1 | Start a session and press P on the first test | Test marked as "pass", display advances to the next test, progress counter increments by 1 | |
| 2.2 | Press F on a test | Comment prompt appears; after entering a comment, test marked as "fail" with comment saved, display advances to next test | |
| 2.3 | Press F on a test, then press Enter at the comment prompt without typing | Test marked as "fail" with empty comment, display advances to next test | |
| 2.4 | Press S on a test | Test marked as "skip", display advances to next test, skip counter increments | |
| 2.5 | Press C on a test | Comment prompt appears; after entering text, comment saved to current test, display stays on same test | |
| 2.6 | Press B on the second or later test | Display navigates back to the previous test, previous test's details shown | |
| 2.7 | Press B on the very first test | Nothing happens, display stays on the first test (no crash or index error) | |
| 2.8 | Press Q at any point during the session | Session saved to disk, "Session saved. Resume with:" message printed with session ID, TUI exits to terminal | |
| 2.9 | Press Ctrl+C at any point during the session | Session saved to disk, "Session saved (Ctrl+C)" message printed, TUI exits to terminal | |
| 2.10 | Navigate to an already-answered test (via B) and press Enter | Display advances to next test without changing the existing result | |
| 2.11 | Navigate to an already-answered test (via B) and press P/F/S | Result changes to the newly pressed value, overwriting the previous answer | |
| 2.12 | Reach the last test in the plan and press P (or F or S) | Session completes, summary panel displayed with pass/fail/skip counts, "Generate report" command printed | |
| 2.13 | Complete a session where all tests pass | Summary panel has green border, shows 0 failures, no failures table displayed | |
| 2.14 | Complete a session with at least one failure | Summary panel has red border, failures table displayed listing each failed test with section, test description, and comment | |
| 2.15 | Verify progress display during navigation | Header shows correct section title, progress fraction (answered/total), percentage, and P/F/S counters matching actual answers | |
| 2.16 | On an already-answered test, verify the result badge | Text "Already marked: PASS/FAIL/SKIP" appears in appropriate color (green/red/yellow) below the test panel | |

---

## 3. Console — Resume

| # | Test | Expected | Pass |
|---|------|----------|------|
| 3.1 | Create a session, answer 3 tests with P, then press Q to quit | Session saved with 3 answered tests | |
| 3.2 | Run `uat_runner resume {session_id} --results-dir /tmp/uat_selftest` using the session ID from 3.1 | TUI starts at the 4th test (first unanswered), progress shows 3/{total}, resume message shows remaining count | |
| 3.3 | Resume the same session again, answer remaining tests to completion | Session completes normally, summary shown, completed timestamp set in JSON | |
| 3.4 | Run `uat_runner resume {session_id}` on the completed session from 3.3 | Message "This session is already complete" printed in green, TUI does not start, report command hint shown | |
| 3.5 | Run `uat_runner resume nonexistent_session_id --results-dir /tmp/uat_selftest` | Error message "Session not found: nonexistent_session_id" printed in red, process exits with non-zero code | |
| 3.6 | Create a session, mark test 1 as fail, test 2 as skip, test 3 as pass, then quit and resume | Resume starts at test 4; tests 1-3 retain their original results and comments when navigated back to via B | |

---

## 4. Console — Status

| # | Test | Expected | Pass |
|---|------|----------|------|
| 4.1 | Run `uat_runner status {session_id} --results-dir /tmp/uat_selftest` on an in-progress session | Output shows: plan name, version, tester, started timestamp, updated timestamp, progress fraction and percentage, P/F/S/remaining counts | |
| 4.2 | Verify per-section table in status output | Sections table displayed with columns: Section, Total, Done, Pass, Fail, Skip; each section row has correct counts | |
| 4.3 | Run `uat_runner status {session_id}` on a completed session | Output includes "Completed:" timestamp in addition to started/updated timestamps | |
| 4.4 | Run `uat_runner status nonexistent_session_id --results-dir /tmp/uat_selftest` | Error message "Session not found" printed in red, process exits with non-zero code | |

---

## 5. Console — List

| # | Test | Expected | Pass |
|---|------|----------|------|
| 5.1 | Run `uat_runner list --results-dir /tmp/uat_empty` (empty directory) | "No sessions found" message printed | |
| 5.2 | Run `uat_runner list --results-dir /tmp/uat_selftest` after creating multiple sessions | Table displayed with columns: ID, Plan, Version, Tester, Progress, P, F, S, Status; all sessions listed | |
| 5.3 | Run `uat_runner list --plan myplan --results-dir /tmp/uat_selftest` | Only sessions with plan_name "myplan" shown; sessions from other plans excluded | |
| 5.4 | Run `uat_runner list --version 1.0.0 --results-dir /tmp/uat_selftest` | Only sessions with version "1.0.0" shown | |
| 5.5 | Run `uat_runner list --plan myplan --version 1.0.0 --results-dir /tmp/uat_selftest` | Only sessions matching both plan and version filters shown | |
| 5.6 | Verify status column: in-progress session shows "In progress", completed session shows "Complete" | Status badges displayed with correct colors (yellow/green) | |
| 5.7 | Verify progress column format | Shows answered/total with percentage, e.g. "5/20 (25%)" | |

---

## 6. Console — Report Generation

| # | Test | Expected | Pass |
|---|------|----------|------|
| 6.1 | Run `uat_runner report {session_id} --results-dir /tmp/uat_selftest` on a completed session with mixed results (some pass, some fail, some skip) | Two files created: {session_id}_report.md and {session_id}_report.xlsx in the results directory | |
| 6.2 | Open the generated markdown report | Contains: header table (Plan, Version, Tester, Date, Duration, Result), Summary section with P/F/S percentages, Failures section, Full Results by section | |
| 6.3 | Verify markdown header table | Fields include Plan, Version, Tester, Date, Duration, and Result showing PASS or FAIL with failure count | |
| 6.4 | Verify markdown failures section | Table with columns #, Section, Test, Comment; lists only failed tests with their comments | |
| 6.5 | Verify markdown full results section | Each section has its own heading and table with columns #, Test, Expected, Result, Comment; result values are PASS/FAIL/SKIP | |
| 6.6 | Open the generated XLSX report | Workbook contains three sheets: Summary, Results, and Failures | |
| 6.7 | Verify XLSX Summary sheet | Rows for Plan, Version, Tester, Started, Completed, Total Tests, Pass, Fail, Skip, Remaining with correct values | |
| 6.8 | Verify XLSX Results sheet | Header row with blue fill; section headers with light blue fill; test rows with result column color-coded: green for pass, red for fail, yellow for skip | |
| 6.9 | Verify XLSX Failures sheet | Only present when failures exist; header row with dark red fill; each failed test listed with section, test description, expected result, and comment | |
| 6.10 | Generate report for a session with zero failures | Markdown report shows "PASS" as result; markdown has no Failures section; XLSX has no Failures sheet | |
| 6.11 | Run `uat_runner report nonexistent_session_id --results-dir /tmp/uat_selftest` | Error message "Session not found" printed in red, process exits with non-zero code | |
| 6.12 | Verify markdown report includes skipped section when skips exist | Skipped section present with table listing skipped tests and their comments | |

---

## 7. Web — Server Startup

| # | Test | Expected | Pass |
|---|------|----------|------|
| 7.1 | Run `uat_runner web --results-dir /tmp/uat_selftest` with default flags | Server starts, output shows "Listening on http://0.0.0.0:8080" and LAN IP address | |
| 7.2 | Run `uat_runner web --host 127.0.0.1 --results-dir /tmp/uat_selftest` | Server binds to localhost only; no LAN IP line printed | |
| 7.3 | Run `uat_runner web --port 9999 --results-dir /tmp/uat_selftest` | Server binds to port 9999; output shows "http://0.0.0.0:9999" | |
| 7.4 | Run `uat_runner web --debug --results-dir /tmp/uat_selftest` | Flask debug mode enabled; Flask reloader and debugger messages visible in terminal output | |
| 7.5 | Run `uat_runner web --results-dir /tmp/uat_custom_web` | Server uses /tmp/uat_custom_web as the results directory for all session operations | |
| 7.6 | Open http://host:port from a different device on the same LAN (when bound to 0.0.0.0) | Page loads successfully in remote browser | |
| 7.7 | Press Ctrl+C in the terminal running the web server | Server shuts down cleanly, terminal returns to prompt | |

---

## 8. Web — Session List View

| # | Test | Expected | Pass |
|---|------|----------|------|
| 8.1 | Open http://localhost:8080 in a browser | Session list page loads with dark theme, nav bar shows "UAT Runner" title | |
| 8.2 | View list with no sessions in the results directory | Empty state message displayed (no cards, no errors) | |
| 8.3 | View list after creating sessions (via console or web) | Session cards displayed showing: plan name, version, tester name, progress bar, P/F/S counts, completion status badge | |
| 8.4 | Verify progress bar on a partially complete session | Progress bar width reflects answered/total percentage; numeric label matches | |
| 8.5 | Verify status badge: in-progress session | Badge shows "In progress" or equivalent indicator in yellow/amber | |
| 8.6 | Verify status badge: completed session | Badge shows "Complete" or equivalent indicator in green | |
| 8.7 | Click on a session card | Navigates to the test runner view for that session | |
| 8.8 | Click "New Session" button | Navigates to the session creation form | |

---

## 9. Web — Create Session

| # | Test | Expected | Pass |
|---|------|----------|------|
| 9.1 | Open the create session form | Plan dropdown shows configured built-in plans (if any); version and tester text fields present | |
| 9.2 | Select a plan, enter version "2.0.0" and tester "Bob", click "Start Session" | Session created via API (HTTP 201), browser redirects to the runner view for the new session | |
| 9.3 | Submit the form with the version field empty | Error message displayed, session not created | |
| 9.4 | Submit the form with the tester field empty | Error message displayed, session not created | |
| 9.5 | Verify the new session appears in the session list | Navigate back to list view; new session card visible with correct plan, version, tester, and 0% progress | |

---

## 10. Web — Test Runner

| # | Test | Expected | Pass |
|---|------|----------|------|
| 10.1 | Open a session in the runner view | Current test displayed with: test number, test description, expected result text | |
| 10.2 | Verify progress stats bar | Shows pass/fail/skip/remaining counts and a progress bar reflecting completion percentage | |
| 10.3 | Click "Pass" button | Test marked as pass (green badge appears), display advances to next unanswered test, progress bar updates | |
| 10.4 | Click "Fail" button | Test marked as fail (red badge appears), display advances to next unanswered test | |
| 10.5 | Click "Skip" button | Test marked as skip (yellow badge appears), display advances to next unanswered test | |
| 10.6 | Type text in the comment field, then click "Pass" | Comment saved alongside the pass result; comment visible when navigating back to this test | |
| 10.7 | Click "Back" button | Display navigates to the previous test; previous test's number, description, expected, and result badge shown | |
| 10.8 | Click "Next" button | Display navigates to the next test, even if that test is already answered | |
| 10.9 | Navigate back to an already-answered test | Current result badge displayed (green/red/yellow) matching the previously recorded answer | |
| 10.10 | On an already-answered test, click a different result button (e.g. change Pass to Fail) | Result changes to the new value; progress counts update accordingly (pass count decrements, fail count increments) | |
| 10.11 | Click "Save and Exit" or equivalent exit button | Browser returns to the session list view; session progress preserved | |
| 10.12 | Verify section title updates as tests advance across section boundaries | When advancing from the last test of one section to the first test of the next, section heading updates | |

---

## 11. Web — Keyboard Shortcuts

| # | Test | Expected | Pass |
|---|------|----------|------|
| 11.1 | In the runner view with focus outside the comment textarea, press the P key | Test marked as pass, same behavior as clicking the Pass button | |
| 11.2 | Press the F key | Test marked as fail, same behavior as clicking the Fail button | |
| 11.3 | Press the S key | Test marked as skip, same behavior as clicking the Skip button | |
| 11.4 | Press the B key | Navigates to previous test, same behavior as clicking the Back button | |
| 11.5 | Press the N key | Navigates to next test, same behavior as clicking the Next button | |
| 11.6 | Click into the comment textarea, then press the P key | Character "p" typed into the textarea; test is NOT marked as pass (shortcut suppressed while typing) | |
| 11.7 | Click outside the comment textarea after typing, then press P | Keyboard shortcut re-enabled; test marked as pass | |

---

## 12. Web — Session Completion

| # | Test | Expected | Pass |
|---|------|----------|------|
| 12.1 | Answer all tests in a session via the web runner | Completion view displayed automatically after the last test is answered | |
| 12.2 | Verify overall verdict when all tests pass | Verdict shown as "PASS" with green styling | |
| 12.3 | Verify overall verdict when at least one test fails | Verdict shown as "FAIL" with red styling | |
| 12.4 | Verify summary grid on completion view | Shows total count and breakdown: pass count, fail count, skip count | |
| 12.5 | Verify failures table on completion view (when failures exist) | Table lists each failed test with test number, section, description, and comment | |
| 12.6 | Click "Generate Reports" button on the completion view | API call creates markdown and XLSX reports; download links appear after generation completes | |
| 12.7 | Verify "Generate Reports" button is absent or disabled when no tests are answered | Button not clickable on a session with zero answers (edge case if directly navigated to) | |
| 12.8 | Click "Back to Sessions" link on the completion view | Browser navigates back to the session list view | |

---

## 13. Web — Report Downloads

| # | Test | Expected | Pass |
|---|------|----------|------|
| 13.1 | Click the "Download Markdown" link after generating reports | Browser downloads a .md file; filename contains the session ID | |
| 13.2 | Click the "Download XLSX" link after generating reports | Browser downloads a .xlsx file; filename contains the session ID | |
| 13.3 | Open the downloaded markdown file | Content matches the format produced by console `uat_runner report`: header table, summary, failures section, full results by section | |
| 13.4 | Open the downloaded XLSX file | Workbook contains Summary, Results, and (if failures exist) Failures sheets, with same styling as console-generated XLSX | |
| 13.5 | Attempt to download a report that has not been generated yet (direct URL) | API returns 404 with error message "Report not found. Generate first." | |
| 13.6 | Request a report with an invalid format parameter (not "md" or "xlsx") | API returns 400 with error message "Invalid format" | |

---

## 14. Interoperability

| # | Test | Expected | Pass |
|---|------|----------|------|
| 14.1 | Create a session via the web UI, then resume it in the console TUI using `uat_runner resume {session_id}` | TUI picks up at the correct position (first unanswered test), all web-marked results visible when navigating with B | |
| 14.2 | Create a session via the console TUI, answer some tests, quit; then open the web UI and continue the session | Web runner shows previously answered tests with correct results and advances to the first unanswered test | |
| 14.3 | Mark 5 tests in the web UI, then run `uat_runner status {session_id}` in the console | Status output shows 5 answered tests with correct P/F/S counts matching what was entered in the web UI | |
| 14.4 | Mark 5 tests in the console TUI, then view the session in the web UI | Web runner displays all 5 results correctly with proper badges and counts | |
| 14.5 | Verify both interfaces read/write to the same results directory | Session JSON file on disk contains results from both console and web interactions; no duplicate or conflicting files | |
| 14.6 | Start the web server with --results-dir /tmp/uat_interop, create a session in the web UI, then resume it in the console with --results-dir /tmp/uat_interop | Custom results directory works consistently; console finds and loads the web-created session | |

---

## 15. Parser

| # | Test | Expected | Pass |
|---|------|----------|------|
| 15.1 | Parse a plan file containing standard headings (`## 1. Title`, `## 2. Title`) | Sections extracted with correct keys ("1", "2") and titles ("1. Title", "2. Title") | |
| 15.2 | Parse a plan file containing a Pre-Test heading (`## Pre-Test: Environment Setup`) | Section extracted with key "Pre-Test: Environment Setup" and matching title | |
| 15.3 | Parse a plan file containing sub-section headings (`### 1a. Sub-Title`) | Sub-section extracted as its own section with key "1a" and title "1a. Sub-Title" | |
| 15.4 | Parse a plan file containing markdown bold in test/expected columns (`**bold text**`) | Bold markers stripped; TestCase.test and TestCase.expected contain plain text without asterisks | |
| 15.5 | Parse a plan file containing multiple tables under a single heading | All rows from all tables under that heading captured in the section's tests list | |
| 15.6 | Parse a plan file with non-table text between the heading and the table (e.g. description paragraphs) | Text lines ignored gracefully; table rows parsed correctly when the table header eventually appears | |
| 15.7 | Parse a plan file that has section headings but no tables under them | Sections created with zero tests; no crash or exception | |
| 15.8 | Parse a plan file that has only a top-level heading and no section headings | Returns empty list (no sections); no crash or exception | |
| 15.9 | Parse this self-test plan file (UAT_TEST_PLAN.md) | All 17 sections extracted (Pre-Test + sections 1-16), total test count matches the number of data rows in all tables combined | |
| 15.10 | Verify test numbering is preserved from the source table | TestCase.num values match the first column of each table row (e.g. "0.1", "1.1", "15.10") | |

---

## 16. Edge Cases

| # | Test | Expected | Pass |
|---|------|----------|------|
| 16.1 | Resume a session where all tests are already passed | Message "All tests in this session are already answered" printed; TUI does not enter interactive mode | |
| 16.2 | Test with a very long description (200+ characters) in TUI | Full description displayed without truncation in the test panel; text wraps within the Rich panel | |
| 16.3 | Test with a very long description (200+ characters) in web UI | Full description displayed without truncation; text wraps within the test card | |
| 16.4 | Enter special characters in a comment (double quotes, single quotes, angle brackets, pipe characters) | Comment saved correctly to session JSON; displayed correctly in both TUI and web UI without corruption | |
| 16.5 | Leave the comment field empty when marking a test (no comment entered) | Empty string saved as comment value; no error, no null/None in JSON | |
| 16.6 | Rapid-fire clicks on Pass/Fail/Skip buttons in the web UI | Only one API call processed at a time (busy flag or button disabling prevents duplicate results); final state consistent | |
| 16.7 | Refresh the browser page during a web session | Session list or runner view reloads from server; no data loss; previously saved results intact | |
| 16.8 | Open two browser tabs on the same session and mark different tests in each | Both tabs can submit results; last write wins for any given test; no server crash or JSON corruption | |
| 16.9 | Parse a large test plan with 400+ test rows | Parser completes without noticeable delay or memory issues; all rows extracted correctly | |
| 16.10 | Enter Unicode characters in the tester name (e.g. accented letters, CJK characters) | Tester name saved correctly in session JSON, displayed correctly in TUI status output and web UI session cards | |
| 16.11 | Verify atomic session save: kill the process mid-save (simulate crash) | Session JSON is either the old version or the new version, never a partial/corrupt file (atomic os.replace behavior) | |
| 16.12 | Run `uat_runner list` when the results directory contains non-JSON files or malformed JSON files | Non-JSON files and corrupt JSON files silently skipped; valid sessions still listed; no crash or traceback | |
| 16.13 | Verify session ID format | Session ID follows the pattern {plan_name}_{version}_{YYYYMMDD_HHMMSS}; no special characters that would cause filesystem issues | |
| 16.14 | Run `uat_runner report` on an in-progress (incomplete) session | Report generated with unanswered tests showing blank/dash results; no crash (report works for partial sessions) | |
