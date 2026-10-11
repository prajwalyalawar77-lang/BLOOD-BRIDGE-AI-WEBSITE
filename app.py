from flask import (
    Flask, render_template, request, jsonify,
    redirect, url_for, session
)
from functools import wraps
import sqlite3
from pathlib import Path
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
import os

app = Flask(__name__)

BASE_DIR = Path(__file__).resolve().parent
DATABASE = str(BASE_DIR / "bloodbridge.db")

# Keep the secret stable between restarts.
# For deployment, set BLOODBRIDGE_SECRET_KEY as an environment variable.
app.config["SECRET_KEY"] = os.environ.get(
    "BLOODBRIDGE_SECRET_KEY",
    "bloodbridge-development-key-change-before-deployment"
)
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"

BLOOD_GROUPS = ["O-", "O+", "A-", "A+", "B-", "B+", "AB-", "AB+"]

COMPATIBLE_DONORS = {
    "O-": ["O-"],
    "O+": ["O-", "O+"],
    "A-": ["O-", "A-"],
    "A+": ["O-", "O+", "A-", "A+"],
    "B-": ["O-", "B-"],
    "B+": ["O-", "O+", "B-", "B+"],
    "AB-": ["O-", "A-", "B-", "AB-"],
    "AB+": ["O-", "O+", "A-", "A+", "B-", "B+", "AB-", "AB+"]
}


# ---------------- LOGIN PROTECTION ----------------

def login_required(route_function):
    @wraps(route_function)
    def wrapper(*args, **kwargs):
        if not session.get("user_id"):
            # APIs should receive JSON errors instead of login-page HTML.
            api_paths = {
                "/add-blood",
                "/update-blood-units",
                "/find-blood",
                "/submit-emergency",
                "/emergency-requests",
                "/update-emergency-status",
                "/emergency-matches",
                "/request-blood",
                "/emergency-request"
            }

            wants_json = (
                request.path in api_paths
                or request.is_json
                or "application/json" in request.headers.get("Accept", "")
                or request.args.get("format") == "json"
            )

            if wants_json:
                return jsonify({
                    "success": False,
                    "message": "Please log in to continue.",
                    "login_url": url_for("login")
                }), 401

            return redirect(url_for("login"))

        return route_function(*args, **kwargs)

    return wrapper


# ---------------- DATABASE ----------------

def get_db():
    conn = sqlite3.connect(DATABASE, timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA busy_timeout = 10000")
    return conn


def create_database():
    conn = get_db()

    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS blood_availability (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                blood_group TEXT NOT NULL,
                units INTEGER NOT NULL DEFAULT 0,
                location TEXT NOT NULL,
                phone TEXT,
                provider_type TEXT DEFAULT 'Individual Donor',
                status TEXT DEFAULT 'Normal'
            )
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS emergency_requests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                patient_name TEXT NOT NULL,
                patient_phone TEXT NOT NULL,
                hospital_name TEXT NOT NULL,
                blood_group TEXT NOT NULL,
                units INTEGER NOT NULL,
                location TEXT NOT NULL,
                priority TEXT NOT NULL DEFAULT 'Normal',
                additional_info TEXT,
                status TEXT NOT NULL DEFAULT 'Pending',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Add missing columns to older emergency databases.
        columns = {
            row["name"]
            for row in conn.execute(
                "PRAGMA table_info(emergency_requests)"
            ).fetchall()
        }

        migrations = {
            "patient_name": "TEXT",
            "patient_phone": "TEXT",
            "hospital_name": "TEXT",
            "blood_group": "TEXT",
            "units": "INTEGER DEFAULT 1",
            "location": "TEXT",
            "priority": "TEXT DEFAULT 'Normal'",
            "additional_info": "TEXT",
            "status": "TEXT DEFAULT 'Pending'",
            "created_at": "TEXT"
        }

        for column, definition in migrations.items():
            if column not in columns:
                conn.execute(
                    f"ALTER TABLE emergency_requests "
                    f"ADD COLUMN {column} {definition}"
                )

        conn.commit()

    finally:
        conn.close()


def clean_text(value):
    return str(value).strip() if value is not None else ""


def read_data():
    return request.get_json(silent=True) or request.form.to_dict()


def as_dicts(rows):
    return [dict(row) for row in rows]


def get_blood_records():
    conn = get_db()

    try:
        rows = conn.execute("""
            SELECT *
            FROM blood_availability
            WHERE units > 0
            ORDER BY
                CASE
                    WHEN status = 'Emergency' THEN 0
                    WHEN status = 'Critical' THEN 1
                    ELSE 2
                END,
                id DESC
        """).fetchall()

        return as_dicts(rows)

    finally:
        conn.close()


# ---------------- REGISTRATION ----------------

@app.route("/register", methods=["GET", "POST"])
def register():
    if session.get("user_id"):
        return redirect(url_for("home"))

    if request.method == "GET":
        return render_template("register.html")

    name = clean_text(request.form.get("name"))
    email = clean_text(request.form.get("email")).lower()
    password = request.form.get("password", "")
    confirm_password = request.form.get("confirm_password", "")

    if not all([name, email, password, confirm_password]):
        return render_template(
            "register.html",
            error="Please complete all required fields.",
            name=name,
            email=email
        )

    if len(name) > 100 or len(email) > 254:
        return render_template(
            "register.html",
            error="Name or email is too long.",
            name=name,
            email=email
        )

    if "@" not in email or "." not in email.rsplit("@", 1)[-1]:
        return render_template(
            "register.html",
            error="Enter a valid email address.",
            name=name,
            email=email
        )

    if len(password) < 8:
        return render_template(
            "register.html",
            error="Password must contain at least 8 characters.",
            name=name,
            email=email
        )

    if password != confirm_password:
        return render_template(
            "register.html",
            error="Passwords do not match.",
            name=name,
            email=email
        )

    conn = get_db()

    try:
        conn.execute("""
            INSERT INTO users (name, email, password_hash)
            VALUES (?, ?, ?)
        """, (
            name,
            email,
            generate_password_hash(password)
        ))

        conn.commit()

        return render_template(
            "login.html",
            success="Registration successful! Please log in.",
            email=email
        )

    except sqlite3.IntegrityError:
        conn.rollback()
        return render_template(
            "register.html",
            error="This email is already registered.",
            name=name,
            email=email
        )

    except sqlite3.Error:
        conn.rollback()
        app.logger.exception("Registration failed")
        return render_template(
            "register.html",
            error="Unable to create your account. Please try again.",
            name=name,
            email=email
        ), 500

    finally:
        conn.close()


# ---------------- LOGIN ----------------

@app.route("/login", methods=["GET", "POST"])
def login():
    if session.get("user_id"):
        return redirect(url_for("home"))

    if request.method == "GET":
        return render_template("login.html")

    email = clean_text(request.form.get("email")).lower()
    password = request.form.get("password", "")

    conn = get_db()

    try:
        user = conn.execute("""
            SELECT id, name, email, password_hash
            FROM users
            WHERE email = ?
        """, (email,)).fetchone()

    finally:
        conn.close()

    if user is None or not check_password_hash(
        user["password_hash"], password
    ):
        return render_template(
            "login.html",
            error="Invalid email or password.",
            email=email
        ), 401

    session.clear()
    session["user_id"] = user["id"]
    session["user_name"] = user["name"]

    return redirect(url_for("home"))


# ---------------- LOGOUT ----------------

@app.route("/logout", methods=["GET", "POST"])
@login_required
def logout():
    session.clear()
    return redirect(url_for("login"))


# ---------------- HOME DASHBOARD ----------------

@app.route("/")
@login_required
def home():
    return render_template(
        "home.html",
        user_name=session.get("user_name")
    )


# ---------------- EMERGENCY PAGES ----------------

@app.route("/emergency")
@login_required
def emergency():
    return render_template("emergency.html")


@app.route("/emergency-history")
@app.route("/emergency-history-page")
@login_required
def emergency_history_page():
    return render_template("emergency-history.html")


# ---------------- BLOOD AVAILABILITY ----------------

@app.route("/blood-availability", methods=["GET"])
@login_required
def blood_availability():
    records = get_blood_records()

    accepts_json = "application/json" in request.headers.get(
        "Accept", ""
    ).lower()

    if request.args.get("format") == "json" or accepts_json:
        return jsonify({
            "success": True,
            "results": records,
            "count": len(records)
        })

    return render_template(
        "blood-availability.html",
        blood_data=records,
        blood_availability=records
    )


# ---------------- JOIN THE NETWORK ----------------

@app.route("/add-blood", methods=["POST"])
@login_required
def add_blood():
    data = read_data()

    name = clean_text(data.get("name"))
    blood_group = clean_text(data.get("blood_group")).upper()
    location = clean_text(data.get("location"))
    phone = clean_text(data.get("phone"))
    provider_type = clean_text(
        data.get("provider_type") or "Individual Donor"
    )
    status = clean_text(data.get("status") or "Normal")

    try:
        units = int(data.get("units", 0))
    except (ValueError, TypeError):
        return jsonify({
            "success": False,
            "message": "Units must be a whole number."
        }), 400

    if not name or not location or not phone:
        return jsonify({
            "success": False,
            "message": "Enter your name, phone number and location."
        }), 400

    if blood_group not in BLOOD_GROUPS:
        return jsonify({
            "success": False,
            "message": "Select a valid blood group."
        }), 400

    if units < 1:
        return jsonify({
            "success": False,
            "message": "Units must be at least 1."
        }), 400

    if status not in ["Emergency", "Critical", "Normal"]:
        status = "Normal"

    conn = get_db()

    try:
        cursor = conn.execute("""
            INSERT INTO blood_availability
                (name, blood_group, units, location, phone,
                 provider_type, status)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            name, blood_group, units, location, phone,
            provider_type, status
        ))

        conn.commit()

        return jsonify({
            "success": True,
            "message": "You have joined the BloodBridge network!",
            "id": cursor.lastrowid
        })

    except sqlite3.Error:
        conn.rollback()
        app.logger.exception("Adding blood availability failed")
        return jsonify({
            "success": False,
            "message": "Unable to save your details. Please try again."
        }), 500

    finally:
        conn.close()


# ---------------- UPDATE BLOOD UNITS ----------------

@app.route("/update-blood-units", methods=["POST"])
@login_required
def update_blood_units():
    data = read_data()

    try:
        record_id = int(data.get("id"))
        units = int(data.get("units"))
    except (ValueError, TypeError):
        return jsonify({
            "success": False,
            "message": "Enter a valid record ID and whole number of units."
        }), 400

    if record_id < 1 or units < 0:
        return jsonify({
            "success": False,
            "message": "Record ID must be positive and units cannot be negative."
        }), 400

    conn = get_db()

    try:
        cursor = conn.execute("""
            UPDATE blood_availability
            SET units = ?
            WHERE id = ?
        """, (units, record_id))

        if cursor.rowcount == 0:
            conn.rollback()
            return jsonify({
                "success": False,
                "message": "Blood availability record not found."
            }), 404

        conn.commit()

        message = (
            "Units set to zero. The record remains saved but is hidden "
            "from public availability results."
            if units == 0
            else "Available blood units updated successfully."
        )

        return jsonify({
            "success": True,
            "message": message,
            "id": record_id,
            "units": units
        })

    except sqlite3.Error:
        conn.rollback()
        app.logger.exception("Updating blood units failed")
        return jsonify({
            "success": False,
            "message": "Unable to update blood units. Please try again."
        }), 500

    finally:
        conn.close()


# ---------------- FIND BLOOD ----------------

@app.route("/find-blood", methods=["GET", "POST"])
@login_required
def find_blood():
    if request.method == "GET":
        blood_group = clean_text(
            request.args.get("blood_group")
        ).upper()
        location = clean_text(request.args.get("location"))
    else:
        data = read_data()
        blood_group = clean_text(
            data.get("blood_group")
        ).upper()
        location = clean_text(data.get("location"))

    if blood_group and blood_group not in BLOOD_GROUPS:
        return jsonify({
            "success": False,
            "message": "Invalid blood group."
        }), 400

    conn = get_db()

    try:
        query = """
            SELECT *
            FROM blood_availability
            WHERE units > 0
        """
        params = []

        if blood_group:
            query += " AND blood_group = ?"
            params.append(blood_group)

        if location:
            query += " AND LOWER(location) LIKE ?"
            params.append("%" + location.lower() + "%")

        query += """
            ORDER BY
                CASE
                    WHEN status = 'Emergency' THEN 0
                    WHEN status = 'Critical' THEN 1
                    ELSE 2
                END,
                id DESC
        """

        results = as_dicts(
            conn.execute(query, params).fetchall()
        )

        return jsonify({
            "success": True,
            "results": results,
            "count": len(results)
        })

    finally:
        conn.close()


# ---------------- SUBMIT EMERGENCY REQUEST ----------------

@app.route("/submit-emergency", methods=["POST"])
@login_required
def submit_emergency():
    data = read_data()

    patient_name = clean_text(data.get("patient_name"))
    patient_phone = clean_text(
        data.get("contact_number") or data.get("patient_phone")
    )
    hospital_name = clean_text(data.get("hospital_name"))
    blood_group = clean_text(data.get("blood_group")).upper()
    location = clean_text(data.get("location"))
    priority = clean_text(data.get("priority")).title()
    additional_info = clean_text(data.get("additional_info"))

    try:
        units = int(data.get("units", 0))
    except (ValueError, TypeError):
        return jsonify({
            "success": False,
            "message": "Units must be a whole number."
        }), 400

    if not all([
        patient_name, patient_phone, hospital_name,
        blood_group, location, priority
    ]):
        return jsonify({
            "success": False,
            "message": "Please complete all required fields."
        }), 400

    if blood_group not in BLOOD_GROUPS:
        return jsonify({
            "success": False,
            "message": "Select a valid blood group."
        }), 400

    if units < 1:
        return jsonify({
            "success": False,
            "message": "Required units must be at least 1."
        }), 400

    if priority not in ["Critical", "Urgent", "Normal"]:
        return jsonify({
            "success": False,
            "message": "Invalid emergency priority."
        }), 400

    conn = get_db()

    try:
        cursor = conn.execute("""
            INSERT INTO emergency_requests (
                patient_name, patient_phone, hospital_name,
                blood_group, units, location, priority,
                additional_info, status, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'Pending', ?)
        """, (
            patient_name, patient_phone, hospital_name,
            blood_group, units, location, priority,
            additional_info,
            datetime.now().isoformat(timespec="seconds")
        ))

        conn.commit()

        return jsonify({
            "success": True,
            "message": "Emergency request submitted successfully.",
            "request_id": cursor.lastrowid,
            "status": "Pending"
        })

    except sqlite3.Error:
        conn.rollback()
        app.logger.exception("Emergency submission failed")
        return jsonify({
            "success": False,
            "message": "Unable to save the emergency request."
        }), 500

    finally:
        conn.close()


# ---------------- EMERGENCY HISTORY API ----------------

@app.route("/emergency-requests", methods=["GET"])
@login_required
def emergency_requests():
    conn = get_db()

    try:
        rows = conn.execute("""
            SELECT *
            FROM emergency_requests
            ORDER BY id DESC
        """).fetchall()

        return jsonify({
            "success": True,
            "results": as_dicts(rows)
        })

    finally:
        conn.close()


# ---------------- UPDATE EMERGENCY STATUS ----------------

@app.route("/update-emergency-status", methods=["POST"])
@login_required
def update_emergency_status():
    data = read_data()

    try:
        request_id = int(data.get("request_id"))
    except (ValueError, TypeError):
        return jsonify({
            "success": False,
            "message": "Invalid request ID."
        }), 400

    status = clean_text(data.get("status")).title()

    if request_id < 1 or status not in [
        "Pending", "Fulfilled", "Cancelled"
    ]:
        return jsonify({
            "success": False,
            "message": "Choose a valid request status."
        }), 400

    conn = get_db()

    try:
        cursor = conn.execute("""
            UPDATE emergency_requests
            SET status = ?
            WHERE id = ?
        """, (status, request_id))

        if cursor.rowcount == 0:
            conn.rollback()
            return jsonify({
                "success": False,
                "message": "Emergency request not found."
            }), 404

        conn.commit()

        return jsonify({
            "success": True,
            "message": "Request status updated.",
            "request_id": request_id,
            "status": status
        })

    except sqlite3.Error:
        conn.rollback()
        app.logger.exception("Status update failed")
        return jsonify({
            "success": False,
            "message": "Unable to update the status."
        }), 500

    finally:
        conn.close()


# ---------------- POTENTIAL BLOOD MATCHES ----------------

@app.route("/emergency-matches", methods=["POST"])
@login_required
def emergency_matches():
    data = read_data()
    blood_group = clean_text(data.get("blood_group")).upper()
    location = clean_text(data.get("location"))

    if blood_group not in BLOOD_GROUPS:
        return jsonify({
            "success": False,
            "message": "Provide a valid blood group."
        }), 400

    compatible_groups = COMPATIBLE_DONORS[blood_group]
    placeholders = ",".join("?" for _ in compatible_groups)

    conn = get_db()

    try:
        rows = conn.execute(f"""
            SELECT *
            FROM blood_availability
            WHERE units > 0
              AND blood_group IN ({placeholders})
            ORDER BY
                CASE
                    WHEN LOWER(location) = LOWER(?) THEN 0
                    WHEN LOWER(location) LIKE LOWER(?) THEN 1
                    ELSE 2
                END,
                units DESC,
                id DESC
        """, (
            *compatible_groups,
            location,
            "%" + location + "%"
        )).fetchall()

        results = []

        for row in rows:
            item = dict(row)
            provider_location = clean_text(item.get("location"))

            if location and provider_location.lower() == location.lower():
                item["match_scope"] = "Same location"
            elif location and location.lower() in provider_location.lower():
                item["match_scope"] = "Nearby location"
            else:
                item["match_scope"] = "Other location"

            results.append(item)

        return jsonify({
            "success": True,
            "requested_blood_group": blood_group,
            "compatible_donor_groups": compatible_groups,
            "local_matches": sum(
                item["match_scope"] == "Same location"
                for item in results
            ),
            "results": results,
            "verification_note": (
                "These are preliminary potential matches. A hospital "
                "or blood bank must verify availability, compatibility "
                "and crossmatching before transfusion."
            )
        })

    finally:
        conn.close()


# ---------------- BACKWARD-COMPATIBLE ROUTES ----------------

@app.route("/request-blood", methods=["POST"])
@login_required
def request_blood_alias():
    return submit_emergency()


@app.route("/emergency-request", methods=["POST"])
@login_required
def emergency_request_alias():
    return submit_emergency()


# ---------------- RUN APPLICATION ----------------

create_database()

if __name__ == "__main__":
    app.run(debug=True)