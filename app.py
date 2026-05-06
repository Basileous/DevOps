"""
CareBase — Healthcare Appointment Management System
A Flask-based REST API with user auth, appointment booking, and AI symptom analysis.
"""

from flask import Flask, jsonify, request, send_from_directory, session
from flask_cors import CORS
from datetime import datetime
from hashlib import sha256
import os, secrets

app = Flask(__name__, static_folder="frontend", static_url_path="")
app.secret_key = os.environ.get("SECRET_KEY", secrets.token_hex(32))
CORS(app, supports_credentials=True)

# ---------------------------------------------------------------------------
# In-memory data stores
# ---------------------------------------------------------------------------

doctors = [
    {"id": 1, "name": "Dr. Sarah Ahmed",    "specialty": "Cardiology",       "experience": 12, "rating": 4.8},
    {"id": 2, "name": "Dr. James Wilson",    "specialty": "Neurology",        "experience": 9,  "rating": 4.6},
    {"id": 3, "name": "Dr. Fatima Khan",     "specialty": "Dermatology",      "experience": 7,  "rating": 4.9},
    {"id": 4, "name": "Dr. Michael Chen",    "specialty": "Orthopedics",      "experience": 15, "rating": 4.7},
    {"id": 5, "name": "Dr. Aisha Malik",     "specialty": "General Medicine", "experience": 10, "rating": 4.5},
]

# Users: { username: { "username": str, "email": str, "password_hash": str, "full_name": str } }
users = {}

# Appointments list
appointments = []
next_appointment_id = 1

# Available time slots
TIME_SLOTS = [
    "09:00 AM", "09:30 AM", "10:00 AM", "10:30 AM",
    "11:00 AM", "11:30 AM", "12:00 PM", "12:30 PM",
    "02:00 PM", "02:30 PM", "03:00 PM", "03:30 PM",
    "04:00 PM", "04:30 PM", "05:00 PM",
]

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def hash_password(password):
    return sha256(password.encode()).hexdigest()

def get_current_user():
    username = session.get("username")
    if username and username in users:
        return users[username]
    return None

def is_slot_taken(doctor_id, date, time):
    """Check if a doctor already has an appointment at the given date and time."""
    for appt in appointments:
        if appt["doctor_id"] == doctor_id and appt["date"] == date and appt["time"] == time:
            return True
    return False

# ---------------------------------------------------------------------------
# Keyword-based symptom analyzer
# ---------------------------------------------------------------------------

SYMPTOM_MAP = {
    "Cardiology": {
        "keywords": ["chest pain", "heart", "palpitation", "shortness of breath",
                      "high blood pressure", "hypertension", "cardiac", "heartbeat"],
        "conditions": ["Possible cardiac arrhythmia", "Hypertension", "Angina"],
        "precautions": [
            "Avoid strenuous physical activity until evaluated",
            "Monitor your blood pressure regularly",
            "Reduce salt and caffeine intake",
        ],
    },
    "Neurology": {
        "keywords": ["headache", "migraine", "dizzy", "dizziness", "seizure",
                      "numbness", "tingling", "memory loss", "brain", "vertigo"],
        "conditions": ["Tension headache", "Migraine", "Vertigo"],
        "precautions": [
            "Rest in a quiet, dark room if experiencing migraines",
            "Stay hydrated and maintain a regular sleep schedule",
            "Avoid screen time for extended periods",
        ],
    },
    "Dermatology": {
        "keywords": ["skin", "rash", "acne", "eczema", "itching", "itchy",
                      "hives", "allergy", "allergic", "swelling", "redness"],
        "conditions": ["Contact dermatitis", "Allergic reaction", "Eczema flare-up"],
        "precautions": [
            "Avoid scratching the affected area",
            "Use fragrance-free moisturizers",
            "Identify and avoid potential allergens",
        ],
    },
    "Orthopedics": {
        "keywords": ["bone", "fracture", "joint", "knee", "back pain", "spine",
                      "muscle", "sprain", "ankle", "shoulder", "arthritis"],
        "conditions": ["Muscle strain", "Joint inflammation", "Possible ligament injury"],
        "precautions": [
            "Apply ice to reduce swelling (20 min on, 20 min off)",
            "Avoid putting weight on the affected area",
            "Use over-the-counter pain relief if needed",
        ],
    },
    "General Medicine": {
        "keywords": ["fever", "cold", "cough", "flu", "sore throat", "fatigue",
                      "nausea", "vomiting", "stomach", "diarrhea", "weakness",
                      "weight loss", "infection", "pain"],
        "conditions": ["Viral infection", "Common cold / Flu", "General fatigue"],
        "precautions": [
            "Rest and stay well hydrated",
            "Monitor your temperature regularly",
            "Consult a doctor if symptoms persist beyond 3 days",
        ],
    },
}


def analyze_symptoms(symptom_text):
    text = symptom_text.lower()
    best_match, best_score = None, 0
    for specialty, data in SYMPTOM_MAP.items():
        score = sum(1 for kw in data["keywords"] if kw in text)
        if score > best_score:
            best_score = score
            best_match = specialty
    if not best_match:
        best_match = "General Medicine"
    info = SYMPTOM_MAP[best_match]
    recommended_doctor = next((d for d in doctors if d["specialty"] == best_match), doctors[-1])
    return {
        "specialty": best_match,
        "conditions": info["conditions"],
        "precautions": info["precautions"],
        "recommended_doctor": recommended_doctor,
    }


# ---------------------------------------------------------------------------
# Health Check
# ---------------------------------------------------------------------------

@app.route("/health", methods=["GET"])
def health_check():
    return jsonify({"status": "ok"}), 200

# ---------------------------------------------------------------------------
# Frontend
# ---------------------------------------------------------------------------

@app.route("/", methods=["GET"])
def serve_frontend():
    return send_from_directory(app.static_folder, "index.html")

# ---------------------------------------------------------------------------
# Auth Endpoints
# ---------------------------------------------------------------------------

@app.route("/api/auth/register", methods=["POST"])
def register():
    """Register a new user."""
    data = request.get_json()
    if not data:
        return jsonify({"error": "Request body must be JSON"}), 400

    full_name = (data.get("full_name") or "").strip()
    username  = (data.get("username") or "").strip().lower()
    email     = (data.get("email") or "").strip().lower()
    password  = (data.get("password") or "")

    if not all([full_name, username, email, password]):
        return jsonify({"error": "All fields are required"}), 400
    if len(username) < 3:
        return jsonify({"error": "Username must be at least 3 characters"}), 400
    if len(password) < 4:
        return jsonify({"error": "Password must be at least 4 characters"}), 400
    if username in users:
        return jsonify({"error": "Username already taken"}), 409

    users[username] = {
        "username": username,
        "full_name": full_name,
        "email": email,
        "password_hash": hash_password(password),
        "created_at": datetime.now().isoformat(),
    }
    session["username"] = username
    return jsonify({"message": "Registration successful", "user": {"username": username, "full_name": full_name, "email": email}}), 201


@app.route("/api/auth/login", methods=["POST"])
def login():
    """Log in an existing user."""
    data = request.get_json()
    if not data:
        return jsonify({"error": "Request body must be JSON"}), 400

    username = (data.get("username") or "").strip().lower()
    password = (data.get("password") or "")

    if not username or not password:
        return jsonify({"error": "Username and password are required"}), 400

    user = users.get(username)
    if not user or user["password_hash"] != hash_password(password):
        return jsonify({"error": "Invalid username or password"}), 401

    session["username"] = username
    return jsonify({"message": "Login successful", "user": {"username": user["username"], "full_name": user["full_name"], "email": user["email"]}}), 200


@app.route("/api/auth/logout", methods=["POST"])
def logout():
    """Log out the current user."""
    session.pop("username", None)
    return jsonify({"message": "Logged out successfully"}), 200


@app.route("/api/auth/me", methods=["GET"])
def get_me():
    """Get the currently logged-in user."""
    user = get_current_user()
    if not user:
        return jsonify({"error": "Not logged in"}), 401
    return jsonify({"user": {"username": user["username"], "full_name": user["full_name"], "email": user["email"]}}), 200

# ---------------------------------------------------------------------------
# API Endpoints
# ---------------------------------------------------------------------------

@app.route("/api/doctors", methods=["GET"])
def get_doctors():
    return jsonify({"doctors": doctors}), 200


@app.route("/api/time-slots", methods=["GET"])
def get_time_slots():
    """Return available time slots. Optionally filter by doctor_id and date to show only free slots."""
    doctor_id = request.args.get("doctor_id", type=int)
    date = request.args.get("date", "")
    if doctor_id and date:
        taken = {appt["time"] for appt in appointments if appt["doctor_id"] == doctor_id and appt["date"] == date}
        available = [s for s in TIME_SLOTS if s not in taken]
        return jsonify({"slots": available, "total": len(TIME_SLOTS), "available": len(available)}), 200
    return jsonify({"slots": TIME_SLOTS, "total": len(TIME_SLOTS), "available": len(TIME_SLOTS)}), 200


@app.route("/api/appointments", methods=["GET"])
def get_appointments():
    """Return appointments. If logged in, return only the user's appointments."""
    user = get_current_user()
    if user:
        user_appts = [a for a in appointments if a["username"] == user["username"]]
        return jsonify({"appointments": user_appts}), 200
    return jsonify({"appointments": []}), 200


@app.route("/api/appointments", methods=["POST"])
def create_appointment():
    """Book a new appointment. User must be logged in."""
    global next_appointment_id

    user = get_current_user()
    if not user:
        return jsonify({"error": "You must be logged in to book an appointment"}), 401

    data = request.get_json()
    if not data:
        return jsonify({"error": "Request body must be JSON"}), 400

    required_fields = ["date", "time", "symptoms"]
    missing = [f for f in required_fields if f not in data or not str(data[f]).strip()]
    if missing:
        return jsonify({"error": f"Missing required fields: {', '.join(missing)}"}), 400

    # Run symptom analysis
    analysis = analyze_symptoms(data["symptoms"])

    # Doctor selection: use provided doctor_id, or let AI pick
    doctor_id = data.get("doctor_id")
    if doctor_id:
        doctor = next((d for d in doctors if d["id"] == int(doctor_id)), None)
        if not doctor:
            doctor = analysis["recommended_doctor"]
    else:
        doctor = analysis["recommended_doctor"]

    date_str = data["date"].strip()
    time_str = data["time"].strip()

    # Check for double-booking
    if is_slot_taken(doctor["id"], date_str, time_str):
        return jsonify({"error": f"{doctor['name']} is already booked on {date_str} at {time_str}. Please choose a different time slot."}), 409

    appointment = {
        "id": next_appointment_id,
        "username": user["username"],
        "patient_name": user["full_name"],
        "doctor_id": doctor["id"],
        "doctor_name": doctor["name"],
        "specialty": doctor["specialty"],
        "date": date_str,
        "time": time_str,
        "symptoms": data["symptoms"].strip(),
        "status": "pending",
        "created_at": datetime.now().isoformat(),
        "ai_analysis": {
            "predicted_conditions": analysis["conditions"],
            "precautions": analysis["precautions"],
            "matched_specialty": analysis["specialty"],
        },
    }

    appointments.append(appointment)
    next_appointment_id += 1
    return jsonify({"message": "Appointment booked successfully", "appointment": appointment}), 201


@app.route("/api/appointments/<int:appointment_id>", methods=["GET"])
def get_appointment(appointment_id):
    appointment = next((a for a in appointments if a["id"] == appointment_id), None)
    if not appointment:
        return jsonify({"error": "Appointment not found"}), 404
    return jsonify({"appointment": appointment}), 200


@app.route("/api/appointments/<int:appointment_id>", methods=["DELETE"])
def delete_appointment(appointment_id):
    global appointments
    user = get_current_user()
    appointment = next((a for a in appointments if a["id"] == appointment_id), None)
    if not appointment:
        return jsonify({"error": "Appointment not found"}), 404
    if user and appointment["username"] != user["username"]:
        return jsonify({"error": "You can only cancel your own appointments"}), 403
    appointments = [a for a in appointments if a["id"] != appointment_id]
    return jsonify({"message": "Appointment cancelled successfully"}), 200


@app.route("/api/analyze", methods=["POST"])
def analyze():
    data = request.get_json()
    if not data or not data.get("symptoms", "").strip():
        return jsonify({"error": "Please provide symptoms text"}), 400
    result = analyze_symptoms(data["symptoms"])
    return jsonify({
        "specialty": result["specialty"],
        "predicted_conditions": result["conditions"],
        "precautions": result["precautions"],
        "recommended_doctor": result["recommended_doctor"],
    }), 200

# ---------------------------------------------------------------------------
# Static files
# ---------------------------------------------------------------------------

@app.route("/static/<path:filename>")
def serve_static(filename):
    return send_from_directory("static", filename)

# ---------------------------------------------------------------------------
# Run
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
