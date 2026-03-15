"""Flask web UI for UAT runner."""

import os
from datetime import datetime

from flask import Flask, render_template, jsonify, request, send_file

from .session import (
    create_session, load_session, save_session, list_sessions,
    DEFAULT_RESULTS_DIR,
)
from .report import generate_markdown_report, generate_xlsx_report


# Built-in plan shortcuts — add entries here to register plans.
# Format: {"name": {"name": "...", "label": "...", "path": "/abs/path"}}
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BUILTIN_PLANS = {}


def create_web_app(results_dir=None):
    """Create and configure the Flask web app.

    Args:
        results_dir: Directory for session files. Defaults to
                     results/ relative to the repo root.
    """
    template_dir = os.path.join(SCRIPT_DIR, "templates")
    app = Flask(__name__, template_folder=template_dir)
    app.config["RESULTS_DIR"] = results_dir

    @app.route("/")
    def index():
        return render_template("index.html")

    @app.route("/api/plans")
    def api_plans():
        """List available built-in plans."""
        plans = []
        for key, info in BUILTIN_PLANS.items():
            if os.path.exists(info["path"]):
                plans.append({
                    "name": info["name"],
                    "label": info["label"],
                })
        return jsonify({"plans": plans})

    @app.route("/api/sessions")
    def api_list_sessions():
        """List all sessions, optionally filtered."""
        plan_name = request.args.get("plan")
        version = request.args.get("version")
        sessions = list_sessions(app.config["RESULTS_DIR"],
                                 plan_name, version)
        return jsonify({"sessions": sessions})

    @app.route("/api/sessions", methods=["POST"])
    def api_create_session():
        """Create a new session."""
        data = request.get_json()
        plan_key = data.get("plan", "")
        version = data.get("version", "").strip()
        tester = data.get("tester", "").strip()

        if not version:
            return jsonify({"error": "Version required"}), 400
        if not tester:
            return jsonify({"error": "Tester name required"}), 400

        # Resolve plan
        if plan_key in BUILTIN_PLANS:
            plan_name = BUILTIN_PLANS[plan_key]["name"]
            plan_path = BUILTIN_PLANS[plan_key]["path"]
        else:
            plan_path = os.path.abspath(plan_key)
            plan_name = os.path.splitext(os.path.basename(plan_path))[0]

        if not os.path.exists(plan_path):
            return jsonify({"error": f"Plan not found: {plan_path}"}), 404

        session = create_session(plan_path, plan_name, version, tester,
                                 app.config["RESULTS_DIR"])
        return jsonify(session.to_dict()), 201

    @app.route("/api/sessions/<session_id>")
    def api_get_session(session_id):
        """Get full session state."""
        try:
            session = load_session(session_id, app.config["RESULTS_DIR"])
            return jsonify(session.to_dict())
        except FileNotFoundError:
            return jsonify({"error": "Session not found"}), 404

    @app.route("/api/sessions/<session_id>/test", methods=["PUT"])
    def api_update_test(session_id):
        """Mark a test result."""
        data = request.get_json()
        try:
            session = load_session(session_id, app.config["RESULTS_DIR"])
        except FileNotFoundError:
            return jsonify({"error": "Session not found"}), 404

        section_idx = data.get("section_idx")
        test_idx = data.get("test_idx")
        result = data.get("result")
        comment = data.get("comment", "")

        if result not in ("pass", "fail", "skip", None):
            return jsonify({"error": "Invalid result"}), 400

        try:
            test = session.sections[section_idx].tests[test_idx]
        except (IndexError, TypeError):
            return jsonify({"error": "Invalid test index"}), 400

        test.result = result
        test.comment = comment
        test.timestamp = datetime.now().isoformat(timespec="seconds")

        save_session(session, app.config["RESULTS_DIR"])
        return jsonify(session.to_dict())

    @app.route("/api/sessions/<session_id>/report", methods=["POST"])
    def api_generate_report(session_id):
        """Generate reports and return paths."""
        try:
            session = load_session(session_id, app.config["RESULTS_DIR"])
        except FileNotFoundError:
            return jsonify({"error": "Session not found"}), 404

        rd = os.path.abspath(app.config["RESULTS_DIR"]
                             or DEFAULT_RESULTS_DIR)

        md_path = os.path.join(rd, f"{session.id}_report.md")
        generate_markdown_report(session, md_path)

        xlsx_path = os.path.join(rd, f"{session.id}_report.xlsx")
        generate_xlsx_report(session, xlsx_path)

        return jsonify({
            "markdown": f"/api/sessions/{session_id}/report/md",
            "xlsx": f"/api/sessions/{session_id}/report/xlsx",
        })

    @app.route("/api/sessions/<session_id>/report/<fmt>")
    def api_download_report(session_id, fmt):
        """Download a generated report."""
        rd = os.path.abspath(app.config["RESULTS_DIR"]
                             or DEFAULT_RESULTS_DIR)

        if fmt == "md":
            path = os.path.join(rd, f"{session_id}_report.md")
            mimetype = "text/markdown"
        elif fmt == "xlsx":
            path = os.path.join(rd, f"{session_id}_report.xlsx")
            mimetype = ("application/vnd.openxmlformats-officedocument"
                        ".spreadsheetml.sheet")
        else:
            return jsonify({"error": "Invalid format"}), 400

        if not os.path.exists(path):
            return jsonify({"error": "Report not found. Generate first."}), 404

        return send_file(path, mimetype=mimetype, as_attachment=True)

    return app
