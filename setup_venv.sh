#!/usr/bin/env bash
# Setup isolated venv for UAT runner
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
VENV_DIR="$SCRIPT_DIR/.venv"

if [ -d "$VENV_DIR" ]; then
    echo "Venv already exists at $VENV_DIR"
    echo "To recreate: rm -rf $VENV_DIR && bash $0"
else
    echo "Creating venv at $VENV_DIR..."
    python3 -m venv "$VENV_DIR"
fi

echo "Installing dependencies..."
"$VENV_DIR/bin/pip" install -q -r "$SCRIPT_DIR/requirements.txt"

echo ""
echo "Setup complete. Usage:"
echo ""
echo "  # Start a new UAT session"
echo "  $VENV_DIR/bin/python -m uat_runner run --plan /path/to/test_plan.md --version 1.0.0"
echo ""
echo "  # Start web UI"
echo "  $VENV_DIR/bin/python -m uat_runner web --port 8080"
echo ""
echo "  # Resume an interrupted session"
echo "  $VENV_DIR/bin/python -m uat_runner resume <session-id>"
echo ""
echo "  # Generate report"
echo "  $VENV_DIR/bin/python -m uat_runner report <session-id>"
echo ""
echo "  # List all sessions"
echo "  $VENV_DIR/bin/python -m uat_runner list"
