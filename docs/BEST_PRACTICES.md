# UAT Runner Best Practices

This guide covers how to use the UAT runner tool effectively, with emphasis on
glass-to-glass testing methodology for reliable, repeatable user acceptance testing.

---

## Glass-to-Glass Testing

### Why Test from a Separate Device

The most reliable UAT testing uses a separate physical device (laptop, tablet, phone)
to access the system under test (SUT) running on a different machine. This is called
"glass-to-glass" testing because you are looking at two different screens -- one
running the SUT, one running the test harness.

Benefits:

- **No shared state**: browser cache, cookies, localStorage from development don't contaminate test results
- **Realistic performance**: CPU/memory contention from the SUT doesn't affect test runner responsiveness
- **Clean browser profile**: no extensions, ad blockers, or developer tools interfering
- **Independent failure domains**: if the SUT crashes, your test session is preserved on the other device
- **Realistic user perspective**: you see what an actual user would see -- network latency, rendering, etc.

### What to Avoid

- **Same browser, different tab**: shared cookies/localStorage/service workers can mask bugs
- **Same machine, different browser**: still shares CPU/memory, may hide performance issues
- **Same machine, incognito window**: better than same browser, but still shares system resources

These approaches are acceptable for quick smoke tests but should not be used for
formal UAT sign-off.

---

## Recommended Network Setup

### Option 1: Local Area Network (LAN)

Best for office/lab environments where test host and tester device are on the same subnet.

```
┌──────────────────┐        WiFi / Ethernet        ┌──────────────────┐
│   Test Host       │ <-----------------------------> │   Tester Device   │
│   (runs SUT +     │    Same subnet (192.168.x.x) │   (laptop/tablet) │
│    UAT web server)│                               │   Browser only    │
└──────────────────┘                               └──────────────────┘
```

Setup:

```bash
# On test host -- start UAT web server (binds all interfaces by default)
.venv/bin/python -m uat_runner web --port 8080

# Output shows:
# UAT Runner Web UI
# Listening on http://0.0.0.0:8080
# LAN access: http://192.168.1.42:8080

# On tester device -- open browser to the LAN URL
# http://192.168.1.42:8080
```

### Option 2: Tailscale (Remote / VPN)

Best for distributed teams or when test host and tester are on different networks.

```
┌──────────────────┐      Tailscale Mesh VPN       ┌──────────────────┐
│   Test Host       │ <-----------------------------> │   Tester Device   │
│   100.x.y.z       │     Encrypted WireGuard      │   100.a.b.c       │
│   (runs SUT +     │                               │   (any location)  │
│    UAT web server)│                               │                   │
└──────────────────┘                               └──────────────────┘
```

Setup:

```bash
# Both devices must have Tailscale installed and authenticated

# On test host -- start with Tailscale IP or 0.0.0.0
.venv/bin/python -m uat_runner web --port 8080

# On tester device -- use Tailscale IP
# http://100.x.y.z:8080
# Or use Tailscale hostname: http://testhost:8080
```

### Option 3: Loopback (Last Resort)

Only when no other option is available. Not recommended for formal UAT.

```bash
# Localhost only
.venv/bin/python -m uat_runner web --host 127.0.0.1 --port 8080
# Access: http://localhost:8080
```

Use `--host 127.0.0.1` to explicitly restrict to localhost if you don't want network
access.

---

## Firewall Considerations

If the tester device can't reach the web server:

- **Linux (ufw)**: `sudo ufw allow 8080/tcp`
- **Linux (firewalld)**: `sudo firewall-cmd --add-port=8080/tcp`
- **macOS**: usually allows incoming by default; check System Preferences > Security > Firewall
- **Windows**: add inbound rule for port 8080 in Windows Defender Firewall

Or use a non-standard port above 1024 to avoid conflicts:

```bash
.venv/bin/python -m uat_runner web --port 9999
```

---

## Mobile and Tablet Testing

The web UI is responsive and works on mobile/tablet browsers. This is ideal for
glass-to-glass testing because:

- Tablets are portable -- carry them to wherever the SUT is running
- Touch-friendly buttons (Pass/Fail/Skip are large enough to tap)
- Works in landscape or portrait orientation
- No app installation required -- just open the browser

Tips:

- Use landscape orientation for better readability of long test descriptions
- Bookmark the UAT runner URL for quick access
- Add to home screen on iOS/Android for app-like experience
- Keyboard shortcuts (P/F/S/B/N) work with Bluetooth keyboards

---

## Console TUI vs Web UI: When to Use Each

### Use Console TUI when:

- You are the only tester and are working directly on the test host
- You prefer keyboard-driven workflows
- You need to run headless (SSH session, no display)
- Network access is not available

### Use Web UI when:

- Testing from a separate device (glass-to-glass)
- Multiple testers need to create/view sessions
- You want a visual dashboard of test progress
- You are on a tablet or mobile device
- Non-technical testers are involved (buttons are more intuitive than keypresses)

Both interfaces read and write the same session files, so you can switch between
them freely.

---

## Multi-Tester Workflow

When multiple people are testing simultaneously:

1. **Each tester creates their own session** -- sessions are identified by plan + version + timestamp, so no conflicts
2. **Use consistent version strings** -- agree on the exact version string (e.g. "4.1.0-rc1") so sessions are filterable
3. **Use the `--tester` flag** -- include your name for attribution
4. **Divide sections** -- assign specific sections to each tester to avoid duplicate effort
5. **One results directory** -- all testers share the same `--results-dir` so all sessions are visible in `list`

Example:

```bash
# Alice tests Core UI sections
uat_runner run --plan /path/to/plan.md --version 4.1.0-rc1 --tester "Alice"

# Bob tests Flash Panel sections
uat_runner run --plan /path/to/plan.md --version 4.1.0-rc1 --tester "Bob"

# Both visible in list
uat_runner list --version 4.1.0-rc1
```

---

## Session Naming Conventions

Session IDs are auto-generated as `{plan}_{version}_{timestamp}`. For team testing,
use consistent conventions:

- **Version format**: `MAJOR.MINOR.PATCH` (e.g. `4.1.0`)
- **Release candidates**: `4.1.0-rc1`, `4.1.0-rc2`
- **Hotfixes**: `4.1.1`
- **Feature branches**: `4.1.0-feature-auth`

This makes filtering easy:

```bash
uat_runner list --version 4.1.0       # All sessions for this version
uat_runner list --plan myapp          # All sessions for this plan
```

---

## Report Review Workflow

After UAT is complete:

1. **Generate reports** from each session (web UI or `uat_runner report <id>`)
2. **Review failures** -- the markdown report has a dedicated failures section
3. **File bugs** for each failure with the test number, section, and tester comment
4. **Re-test after fixes** -- create a new session for the patched version
5. **Compare across versions** -- session files are stored per version, so you can compare pass rates over time
6. **Archive** -- session JSON files and reports persist in the results directory

---

## Agent-to-Human Handoff

### Why Agents Need Human UAT

AI coding agents (Claude Code, Cursor, Copilot, etc.) can write code, run unit tests,
and verify lint rules -- but they cannot perform glass-to-glass user acceptance testing.
An agent cannot click buttons on a real browser, judge visual layout, or confirm that
a workflow "feels right" to an actual user. The UAT runner bridges this gap: an agent
prepares a test plan, creates a session, and then hands control to a human tester who
executes the plan on a separate device. When the human finishes, the agent reads the
results and acts on them.

This is the canonical pattern for verifying agent-built code before any claim of
production readiness.

### The Handoff Workflow

1. **Agent generates or selects a test plan** -- The agent writes a markdown test plan
   from requirements, or uses an existing plan file already in the repository.

2. **Agent creates a UAT session** -- via MCP tool or CLI. This produces a session ID
   and a JSON file tracking every test case.

3. **Agent starts (or instructs the human to start) the web server** -- so the human
   can access the UAT UI from a separate device (glass-to-glass, as described above).

4. **Human tests on a separate device** -- The human opens the web UI on a tablet,
   laptop, or phone and works through every test case, marking each Pass, Fail, or
   Skip with optional comments.

5. **Agent monitors progress** -- The agent polls session status periodically to check
   how many tests remain.

6. **Agent reads the final report** -- When all tests are answered, the agent reads the
   generated report to determine pass/fail counts and failure details.

7. **Agent acts on failures** -- The agent fixes code, creates a new session for the
   patched version, and iterates until the human signs off.

### MCP Workflow Example

Below is a concrete sequence showing the MCP tool calls an agent would make. The
`mcp__uat_runner__` prefix follows the standard MCP tool naming convention.

```
# Step 1: Create a session from an existing test plan
mcp__uat_runner__create_session(
    plan_path="/path/to/your_test_plan.md",
    version="4.2.0-rc1",
    tester="human-tester"
)
# Returns: { "session_id": "your_test_plan_4.2.0-rc1_20260315_143022", "total_tests": 34 }

# Step 2: Instruct the human to start the web server (or start it directly)
# Agent tells the human:
#   "Please run: .venv/bin/python -m uat_runner web --port 8080"
#   "Then open http://<host-ip>:8080 on your test device."

# Step 3: Poll for progress while the human works
mcp__uat_runner__get_session(
    session_id="your_test_plan_4.2.0-rc1_20260315_143022"
)
# Returns: { "passed": 12, "failed": 1, "skipped": 0, "remaining": 21, "total": 34 }

# Step 4: When remaining reaches 0, read the report
mcp__uat_runner__read_report(
    session_id="your_test_plan_4.2.0-rc1_20260315_143022"
)
# Returns: full markdown report with pass/fail summary and failure details

# Step 5: If there are failures, fix the code and create a new session
mcp__uat_runner__create_session(
    plan_path="/path/to/your_test_plan.md",
    version="4.2.0-rc2",
    tester="human-tester"
)
# Repeat until all tests pass.
```

### CLI Equivalent

Agents that do not have MCP access can use the CLI directly via shell commands:

```bash
# Create session
.venv/bin/python -m uat_runner run \
    --plan /path/to/your_test_plan.md --version 4.2.0-rc1 --tester "human-tester" --web

# Check status
.venv/bin/python -m uat_runner status your_test_plan_4.2.0-rc1_20260315_143022

# Read report
.venv/bin/python -m uat_runner report your_test_plan_4.2.0-rc1_20260315_143022
```

### Practical Advice

- **Do not skip the human step.** An agent marking its own tests as passed defeats
  the purpose. The whole point is independent human verification.
- **Keep sessions short.** A 20-30 test plan is easier for a human to complete in one
  sitting than a 200-test marathon. Split large plans into sections if needed.
- **Include visual checks.** Agents cannot judge visual correctness. Add test cases
  like "Splash screen displays without clipping" or "Map tiles load within 3 seconds"
  that only a human can verify.
- **Version every iteration.** Use `-rc1`, `-rc2`, etc. so the fix-retest cycle
  produces a clear history of sessions.
- **Poll, don't spam.** Check session status every 30-60 seconds, not every second.
  The human needs time to actually perform the tests.

---

## Checklist: Formal UAT Sign-Off

Before declaring UAT complete:

- [ ] All tests answered (no "remaining" count)
- [ ] Glass-to-glass testing used (separate device from SUT)
- [ ] All failures investigated and either fixed or documented as known issues
- [ ] Reports generated (markdown + XLSX)
- [ ] Reports reviewed by test lead
- [ ] Bug tickets filed for all failures
- [ ] Re-test sessions created for fixed bugs
