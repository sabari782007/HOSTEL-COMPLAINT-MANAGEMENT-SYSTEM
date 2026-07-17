"""
Hostel Complaint Management System (HCMS)
Backend - Flask + SQLite REST API

Setup:
    pip install flask flask-cors werkzeug
    python app.py

The app auto-creates the database (hcms.db) from schema.sql on first run,
and seeds a default admin account:
    email: admin@hcms.com
    password: admin123
"""

import os
import sqlite3
from datetime import datetime

from flask import Flask, g, jsonify, request
from flask_cors import CORS
from werkzeug.security import check_password_hash, generate_password_hash

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "hcms.db")
SCHEMA_PATH = os.path.join(BASE_DIR, "..", "database", "schema.sql")

app = Flask(__name__)
CORS(app)


# ---------------------------------------------------------------
# Database helpers
# ---------------------------------------------------------------
def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


@app.teardown_appcontext
def close_db(exception=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    first_time = not os.path.exists(DB_PATH)
    conn = sqlite3.connect(DB_PATH)
    with open(SCHEMA_PATH, "r") as f:
        conn.executescript(f.read())
    if first_time:
        conn.execute(
            "INSERT INTO users (full_name, email, password_hash, role) VALUES (?, ?, ?, ?)",
            ("System Admin", "admin@hcms.com", generate_password_hash("admin123"), "admin"),
        )
        conn.commit()
    conn.close()


def row_to_dict(row):
    return dict(row) if row else None


def rows_to_list(rows):
    return [dict(r) for r in rows]


# ---------------------------------------------------------------
# Auth routes
# ---------------------------------------------------------------
@app.route("/api/register", methods=["POST"])
def register():
    data = request.get_json(force=True)
    required = ["full_name", "email", "password"]
    if not all(data.get(f) for f in required):
        return jsonify({"error": "full_name, email and password are required"}), 400

    db = get_db()
    existing = db.execute("SELECT user_id FROM users WHERE email = ?", (data["email"],)).fetchone()
    if existing:
        return jsonify({"error": "Email already registered"}), 409

    db.execute(
        """INSERT INTO users (full_name, email, password_hash, role, room_number, block, phone)
           VALUES (?, ?, ?, 'student', ?, ?, ?)""",
        (
            data["full_name"],
            data["email"],
            generate_password_hash(data["password"]),
            data.get("room_number"),
            data.get("block"),
            data.get("phone"),
        ),
    )
    db.commit()
    return jsonify({"message": "Registration successful"}), 201


@app.route("/api/login", methods=["POST"])
def login():
    data = request.get_json(force=True)
    email = data.get("email")
    password = data.get("password")

    db = get_db()
    user = db.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
    if not user or not check_password_hash(user["password_hash"], password):
        return jsonify({"error": "Invalid email or password"}), 401

    user_dict = row_to_dict(user)
    user_dict.pop("password_hash")
    return jsonify({"message": "Login successful", "user": user_dict}), 200


# ---------------------------------------------------------------
# Category routes
# ---------------------------------------------------------------
@app.route("/api/categories", methods=["GET"])
def get_categories():
    db = get_db()
    rows = db.execute("SELECT * FROM categories ORDER BY name").fetchall()
    return jsonify(rows_to_list(rows)), 200


# ---------------------------------------------------------------
# Complaint routes
# ---------------------------------------------------------------
@app.route("/api/complaints", methods=["POST"])
def create_complaint():
    data = request.get_json(force=True)
    required = ["student_id", "category_id", "title", "description"]
    if not all(data.get(f) for f in required):
        return jsonify({"error": "student_id, category_id, title, description are required"}), 400

    db = get_db()
    cur = db.execute(
        """INSERT INTO complaints
           (student_id, category_id, title, description, block, room_number, priority)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (
            data["student_id"],
            data["category_id"],
            data["title"],
            data["description"],
            data.get("block"),
            data.get("room_number"),
            data.get("priority", "Medium"),
        ),
    )
    complaint_id = cur.lastrowid
    db.execute(
        "INSERT INTO complaint_logs (complaint_id, changed_by, old_status, new_status, remarks) VALUES (?, ?, NULL, 'Pending', 'Complaint submitted')",
        (complaint_id, data["student_id"]),
    )
    db.commit()
    return jsonify({"message": "Complaint submitted", "complaint_id": complaint_id}), 201


@app.route("/api/complaints", methods=["GET"])
def list_complaints():
    """Supports optional filters: student_id, status, category_id, block"""
    db = get_db()
    query = """SELECT c.*, cat.name AS category_name, u.full_name AS student_name
               FROM complaints c
               JOIN categories cat ON cat.category_id = c.category_id
               JOIN users u ON u.user_id = c.student_id
               WHERE 1=1"""
    params = []

    for field in ["student_id", "status", "category_id", "block"]:
        value = request.args.get(field)
        if value:
            query += f" AND c.{field} = ?"
            params.append(value)

    query += " ORDER BY c.created_at DESC"
    rows = db.execute(query, params).fetchall()
    return jsonify(rows_to_list(rows)), 200


@app.route("/api/complaints/<int:complaint_id>", methods=["GET"])
def get_complaint(complaint_id):
    db = get_db()
    row = db.execute(
        """SELECT c.*, cat.name AS category_name, u.full_name AS student_name
           FROM complaints c
           JOIN categories cat ON cat.category_id = c.category_id
           JOIN users u ON u.user_id = c.student_id
           WHERE c.complaint_id = ?""",
        (complaint_id,),
    ).fetchone()
    if not row:
        return jsonify({"error": "Complaint not found"}), 404
    return jsonify(row_to_dict(row)), 200


@app.route("/api/complaints/<int:complaint_id>/status", methods=["PUT"])
def update_status(complaint_id):
    """Admin/staff updates complaint status."""
    data = request.get_json(force=True)
    new_status = data.get("status")
    changed_by = data.get("changed_by")
    remarks = data.get("remarks", "")
    assigned_staff = data.get("assigned_staff")

    valid_statuses = ["Pending", "Assigned", "In Progress", "Resolved", "Rejected"]
    if new_status not in valid_statuses:
        return jsonify({"error": f"status must be one of {valid_statuses}"}), 400

    db = get_db()
    current = db.execute("SELECT status FROM complaints WHERE complaint_id = ?", (complaint_id,)).fetchone()
    if not current:
        return jsonify({"error": "Complaint not found"}), 404

    resolved_at = datetime.utcnow().isoformat() if new_status == "Resolved" else None

    db.execute(
        """UPDATE complaints
           SET status = ?, admin_remarks = ?, assigned_staff = COALESCE(?, assigned_staff),
               updated_at = CURRENT_TIMESTAMP,
               resolved_at = COALESCE(?, resolved_at)
           WHERE complaint_id = ?""",
        (new_status, remarks, assigned_staff, resolved_at, complaint_id),
    )
    db.execute(
        "INSERT INTO complaint_logs (complaint_id, changed_by, old_status, new_status, remarks) VALUES (?, ?, ?, ?, ?)",
        (complaint_id, changed_by, current["status"], new_status, remarks),
    )
    db.execute(
        "INSERT INTO notifications (user_id, complaint_id, message) SELECT student_id, complaint_id, ? FROM complaints WHERE complaint_id = ?",
        (f"Your complaint status changed to '{new_status}'", complaint_id),
    )
    db.commit()
    return jsonify({"message": "Status updated"}), 200


@app.route("/api/complaints/<int:complaint_id>", methods=["DELETE"])
def withdraw_complaint(complaint_id):
    db = get_db()
    row = db.execute("SELECT status FROM complaints WHERE complaint_id = ?", (complaint_id,)).fetchone()
    if not row:
        return jsonify({"error": "Complaint not found"}), 404
    if row["status"] != "Pending":
        return jsonify({"error": "Only pending complaints can be withdrawn"}), 400
    db.execute("DELETE FROM complaints WHERE complaint_id = ?", (complaint_id,))
    db.commit()
    return jsonify({"message": "Complaint withdrawn"}), 200


# ---------------------------------------------------------------
# Feedback routes
# ---------------------------------------------------------------
@app.route("/api/feedback", methods=["POST"])
def add_feedback():
    data = request.get_json(force=True)
    complaint_id = data.get("complaint_id")
    rating = data.get("rating")
    comments = data.get("comments", "")

    if not complaint_id or not rating:
        return jsonify({"error": "complaint_id and rating are required"}), 400

    db = get_db()
    complaint = db.execute("SELECT status FROM complaints WHERE complaint_id = ?", (complaint_id,)).fetchone()
    if not complaint:
        return jsonify({"error": "Complaint not found"}), 404
    if complaint["status"] != "Resolved":
        return jsonify({"error": "Feedback allowed only after resolution"}), 400

    db.execute(
        "INSERT INTO feedback (complaint_id, rating, comments) VALUES (?, ?, ?)",
        (complaint_id, rating, comments),
    )
    db.commit()
    return jsonify({"message": "Feedback submitted"}), 201


# ---------------------------------------------------------------
# Notification routes
# ---------------------------------------------------------------
@app.route("/api/notifications/<int:user_id>", methods=["GET"])
def get_notifications(user_id):
    db = get_db()
    rows = db.execute(
        "SELECT * FROM notifications WHERE user_id = ? ORDER BY created_at DESC", (user_id,)
    ).fetchall()
    return jsonify(rows_to_list(rows)), 200


# ---------------------------------------------------------------
# Reports & analytics
# ---------------------------------------------------------------
@app.route("/api/reports/summary", methods=["GET"])
def report_summary():
    db = get_db()
    by_status = db.execute(
        "SELECT status, COUNT(*) AS count FROM complaints GROUP BY status"
    ).fetchall()
    by_category = db.execute(
        """SELECT cat.name AS category, COUNT(*) AS count
           FROM complaints c JOIN categories cat ON cat.category_id = c.category_id
           GROUP BY cat.name"""
    ).fetchall()
    avg_rating = db.execute("SELECT AVG(rating) AS avg_rating FROM feedback").fetchone()

    return jsonify({
        "by_status": rows_to_list(by_status),
        "by_category": rows_to_list(by_category),
        "average_rating": round(avg_rating["avg_rating"], 2) if avg_rating["avg_rating"] else None,
    }), 200


# ---------------------------------------------------------------
# Staff/Admin management
# ---------------------------------------------------------------
@app.route("/api/staff", methods=["GET"])
def list_staff():
    db = get_db()
    rows = db.execute("SELECT user_id, full_name, email, phone FROM users WHERE role = 'staff'").fetchall()
    return jsonify(rows_to_list(rows)), 200


@app.route("/api/staff", methods=["POST"])
def add_staff():
    data = request.get_json(force=True)
    required = ["full_name", "email", "password"]
    if not all(data.get(f) for f in required):
        return jsonify({"error": "full_name, email and password are required"}), 400

    db = get_db()
    db.execute(
        "INSERT INTO users (full_name, email, password_hash, role, phone) VALUES (?, ?, ?, 'staff', ?)",
        (data["full_name"], data["email"], generate_password_hash(data["password"]), data.get("phone")),
    )
    db.commit()
    return jsonify({"message": "Staff account created"}), 201


if __name__ == "__main__":
    init_db()
    app.run(debug=True, port=5000)
