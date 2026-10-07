"""
ChikitAI Backend v5.0 — Bolna Edition
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Migrated from VAPI to Bolna AI.

Key architectural changes vs v4 (VAPI):
  ✦ Tool endpoints     — each tool is a direct POST endpoint
                         (Bolna calls them individually, no single dispatch)
  ✦ Webhook            — /webhook/bolna receives end-of-call + call events
  ✦ Outbound call      — POST https://api.bolna.ai/call
  ✦ STT/TTS            — handled entirely by Bolna+Sarvam in dashboard
                         (no /sarvam/transcribe or /sarvam/speak endpoints)
  ✦ Language           — Sarvam returns language_code in Bolna's call context
  ✦ Session init       — via /webhook/bolna call-started event (not assistant-request)

What stays identical:
  ✦ All 7 tool business logic functions (_tool_*)
  ✦ hospital_db.json data layer
  ✦ Slot conflict matrix + capacity enforcement
  ✦ Atomic DB save + corruption guard
  ✦ Rate limiting, session GC, structured errors
  ✦ Dashboard endpoints + index.html
  ✦ ngrok auto-tunnel in lifespan
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

from __future__ import annotations
import json, uuid, os, httpx, asyncio, shutil, traceback, base64
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from dotenv import load_dotenv

load_dotenv()

# Plivo / Sarvam / OpenAI clients (imported after load_dotenv)
from sarvam_client import SarvamSTT, sarvam_tts
from llm_engine    import ConversationManager, OPENING_GREETING, OPENING_LANG

# ═══════════════════════════════════════════════════════════
# CONFIG
# ═══════════════════════════════════════════════════════════

DB_PATH           = os.getenv("DB_PATH", "hospital_db.json")
DB_BACKUP         = DB_PATH + ".bak"
BOLNA_API_KEY     = os.getenv("BOLNA_API_KEY", "")
BOLNA_AGENT_ID    = os.getenv("BOLNA_AGENT_ID", "")
BOLNA_FROM_NUMBER = os.getenv("BOLNA_FROM_NUMBER", "")
NGROK_AUTHTOKEN   = os.getenv("NGROK_AUTHTOKEN", "")
PORT              = int(os.getenv("PORT", 8000))
SESSION_TTL_H     = 2

# ── New: direct Plivo + Sarvam + OpenAI pipeline ─────────────
SARVAM_API_KEY  = os.getenv("SARVAM_API_KEY",  "")
OPENAI_API_KEY  = os.getenv("OPENAI_API_KEY",  "")
PUBLIC_HOST     = os.getenv("PUBLIC_HOST", "")   # e.g. concededly-cognominal-beryl.ngrok-free.dev
PLIVO_AUTH_ID   = os.getenv("PLIVO_AUTH_ID",  "")
PLIVO_AUTH_TOKEN= os.getenv("PLIVO_AUTH_TOKEN","")

# DTMF fallback menu (triggered by Bolna's Keypad Input feature)
DTMF_MENU = {
    "1": "book_appointment",
    "2": "modify_appointment",
    "3": "cancel_appointment",
    "4": "check_specialty_availability",
    "0": "speak_to_operator",
}

FALLBACK_MENU = {
    "en": "I didn't catch that. Press 1 to book, 2 to modify, 3 to cancel, or 4 to check availability.",
    "hi": "Mujhe samajh nahi aaya. 1 dabaiye appointment book karne ke liye, 2 modify ke liye, 3 cancel ke liye.",
    "or": "Mun bujhipari nahi. 1 dabanti appointment book karibaku, 2 modify karibaku, 3 cancel karibaku.",
}


# ═══════════════════════════════════════════════════════════
# APP + RATE LIMITER
# ═══════════════════════════════════════════════════════════

limiter = Limiter(key_func=get_remote_address, default_limits=["60/minute"])

@asynccontextmanager
async def lifespan(application: FastAPI):
    # ── Startup ───────────────────────────────────────────
    try:
        load_db()
        print("✓ Database loaded successfully")
    except Exception as e:
        print(f"✗ Database load FAILED on startup: {e}")

    print("✓ Sarvam API key configured"  if SARVAM_API_KEY  else "⚠ SARVAM_API_KEY not set")
    print("✓ OpenAI API key configured"  if OPENAI_API_KEY  else "⚠ OPENAI_API_KEY not set")
    print("✓ Plivo Auth ID configured"   if PLIVO_AUTH_ID   else "⚠ PLIVO_AUTH_ID not set")
    print("✓ Plivo From Number set"      if os.getenv("PLIVO_FROM_NUMBER") else "⚠ PLIVO_FROM_NUMBER not set")

    # ── ngrok tunnel ──────────────────────────────────────
    ngrok_tunnel = None
    if NGROK_AUTHTOKEN:
        try:
            import ngrok as ngrok_lib
            ngrok_tunnel = await ngrok_lib.forward(
                PORT,
                authtoken=NGROK_AUTHTOKEN,
                domain="concededly-cognominal-beryl.ngrok-free.dev"
            )
            public_url = ngrok_tunnel.url()
            print(f"✓ ngrok tunnel active: {public_url}")
            print(f"  → Plivo Answer URL: {public_url}/plivo/answer")
            print(f"  → Trigger call:     {public_url}/trigger-call")
        except Exception as e:
            print(f"⚠ ngrok failed to start: {e}")
    else:
        print("⚠ NGROK_AUTHTOKEN not set — tunnel not started")

    print(f"✓ ChikitAI v6.0 (Plivo + Sarvam + OpenAI) ready on port {PORT}")
    yield

    # ── Shutdown ──────────────────────────────────────────
    if ngrok_tunnel:
        try:
            import ngrok as ngrok_lib
            await ngrok_lib.disconnect(ngrok_tunnel.url())
            print("✓ ngrok tunnel closed")
        except Exception:
            pass

app = FastAPI(title="ChikitAI", version="6.0", lifespan=lifespan)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# ── In-memory stores ──────────────────────────────────────
SESSIONS:    dict = {}
THOUGHT_LOG: list = []
ACTIVE_CALL: dict = None


# ═══════════════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════════════

def err(code: str, detail: str, status: int = 400) -> JSONResponse:
    log(f"ERROR [{code}] {detail}")
    return JSONResponse(status_code=status, content={"error": detail, "code": code})

def log(msg: str):
    ts    = datetime.now().strftime("%H:%M:%S")
    entry = f"[{ts}] {msg}"
    THOUGHT_LOG.append(entry)
    if len(THOUGHT_LOG) > 25:
        THOUGHT_LOG.pop(0)
    print(entry)

def load_db() -> dict:
    try:
        with open(DB_PATH) as f:
            return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError) as e:
        log(f"DB CORRUPT/MISSING: {e} — attempting backup restore")
        if os.path.exists(DB_BACKUP):
            try:
                with open(DB_BACKUP) as f:
                    return json.load(f)
            except Exception:
                pass
        raise RuntimeError("Database unavailable.") from e

def save_db(data: dict):
    tmp = DB_PATH + ".tmp"
    try:
        with open(tmp, "w") as f:
            json.dump(data, f, indent=4)
        if os.path.exists(DB_PATH):
            shutil.copy2(DB_PATH, DB_BACKUP)
        os.replace(tmp, DB_PATH)
    except Exception as e:
        log(f"DB SAVE ERROR: {e}")
        if os.path.exists(tmp):
            os.remove(tmp)
        raise


# ═══════════════════════════════════════════════════════════
# DATA LAYER — Slot Conflict Matrix
# ═══════════════════════════════════════════════════════════

def _get_booked_slots(db: dict, doctor_id: str, exclude_app_id: str = None) -> set:
    return {
        f"{b['day']} {b['time']}"
        for b in db["current_bookings"]
        if  b["doctor_id"]      == doctor_id
        and b["status"]         == "Confirmed"
        and b["appointment_id"] != exclude_app_id
    }

def _free_slots(doctor: dict, booked: set) -> list[str]:
    return [
        f"{day} {slot}"
        for day  in doctor["available_days"]
        for slot in doctor["slots"]
        if  f"{day} {slot}" not in booked
    ]

def _slot_valid_for_doctor(doctor: dict, day: str, time: str) -> bool:
    return day in doctor["available_days"] and time in doctor["slots"]

def _next_available(db: dict, doctor_id: str, exclude: str = None, limit: int = 3) -> list[str]:
    doctor = next((d for d in db["doctors"] if d["id"] == doctor_id), None)
    if not doctor:
        return []
    return _free_slots(doctor, _get_booked_slots(db, doctor_id, exclude))[:limit]

def _build_slot_matrix(db: dict) -> dict:
    matrix = {}
    for doc in db["doctors"]:
        booked = _get_booked_slots(db, doc["id"])
        matrix[doc["id"]] = {}
        for day in doc["available_days"]:
            for slot in doc["slots"]:
                key = f"{day} {slot}"
                matrix[doc["id"]][key] = "booked" if key in booked else "free"
    return matrix


# ═══════════════════════════════════════════════════════════
# SESSION MANAGEMENT
# ═══════════════════════════════════════════════════════════

def _init_session(call_id: str, phone: str) -> dict:
    global ACTIVE_CALL
    _gc_stale_sessions()
    db      = load_db()
    patient = next((p for p in db["patients"] if p["phone"] == phone), None)
    session = {
        "call_id":             call_id,
        "patient_phone":       phone,
        "patient_name":        patient["name"] if patient else "Unknown",
        "is_existing":         bool(patient),
        "language":            None,
        "last_appointment_id": None,
        "started_at":          datetime.now().isoformat(),
        "transcript":          "",
    }
    SESSIONS[call_id] = session
    ACTIVE_CALL = {"name": session["patient_name"], "phone": phone, "is_existing": session["is_existing"]}
    return session

def _close_session(call_id: str, transcript: str):
    global ACTIVE_CALL
    if call_id not in SESSIONS:
        return
    SESSIONS[call_id]["transcript"] = transcript
    SESSIONS[call_id]["ended_at"]   = datetime.now().isoformat()
    try:
        db = load_db()
        db.setdefault("call_transcripts", []).append({
            "call_id":    call_id,
            "phone":      SESSIONS[call_id]["patient_phone"],
            "patient":    SESSIONS[call_id]["patient_name"],
            "language":   SESSIONS[call_id].get("language", "unknown"),
            "started_at": SESSIONS[call_id]["started_at"],
            "ended_at":   SESSIONS[call_id]["ended_at"],
            "transcript": transcript,
        })
        save_db(db)
    except Exception as e:
        log(f"Transcript persist failed: {e}")
    ACTIVE_CALL = None

def _gc_stale_sessions():
    cutoff = datetime.now() - timedelta(hours=SESSION_TTL_H)
    stale  = [cid for cid, s in SESSIONS.items()
               if datetime.fromisoformat(s["started_at"]) < cutoff]
    for cid in stale:
        log(f"GC stale session: {cid}")
        del SESSIONS[cid]


# ═══════════════════════════════════════════════════════════
# TOOL IMPLEMENTATIONS
# ═══════════════════════════════════════════════════════════

def _resolve_phone(args: dict, body: dict) -> str:
    """
    Return a valid E.164 phone number.
    Priority: extracted param → from_number fallback → +91 prefix on 10 digits.
    """
    extracted = args.get("patient_phone") or args.get("phone") or ""
    extracted  = extracted.strip()
    if extracted.startswith("+") and len(extracted) >= 12:
        return extracted
    # Bolna always sends the real caller number as from_number
    from_number = body.get("from_number", "").strip()
    if from_number.startswith("+") and len(from_number) >= 12:
        log(f"Phone fallback: using from_number {from_number}")
        return from_number
    # Last resort: strip non-digits and prepend +91 if 10 digits remain
    digits = "".join(c for c in extracted if c.isdigit())
    if len(digits) == 10:
        return f"+91{digits}"
    return extracted

def _resolve_doctor_id(args: dict, db: dict) -> str:
    """
    Return a valid doctor_id.
    Priority: explicit doctor_id param → fuzzy match on doctor_name.
    """
    doctor_id = args.get("doctor_id", "").strip()
    if doctor_id:
        # Validate it actually exists
        if any(d["id"] == doctor_id for d in db["doctors"]):
            return doctor_id
    # Fallback: try to match by name
    name_hint = args.get("doctor_name", "").lower().strip()
    name_hint = name_hint.replace("daktar", "").replace("doctor", "").replace("dr.", "").strip()
    if name_hint:
        doctor = next(
            (d for d in db["doctors"] if name_hint in d["name"].lower()),
            None
        )
        if doctor:
            log(f"doctor_id resolved from name '{name_hint}' → {doctor['id']}")
            return doctor["id"]
    return ""

def _tool_check_specialty(call_id: str, args: dict) -> str:
    specialty = args.get("specialty", "").strip()
    db = load_db()
    doctors = [d for d in db["doctors"] if d["specialty"].lower() == specialty.lower()]
    if not doctors:
        avail = sorted({d["specialty"] for d in db["doctors"]})
        return f"No doctors found for '{specialty}'. Available specialties: {', '.join(avail)}."
    lines = []
    for d in doctors:
        free = _free_slots(d, _get_booked_slots(db, d["id"]))
        lines.append(f"{d['name']} — {', '.join(free[:4]) if free else 'fully booked this week'}")
    return f"{specialty} doctors:\n" + "\n".join(lines)

def _tool_check_doctor(call_id: str, args: dict) -> str:
    query  = args.get("doctor_name", "").lower()
    query  = query.replace("daktar", "").replace("doctor", "").replace("dr.", "").strip()
    if not query:
        return "ERROR: Doctor Not Found. Please ask the user to clarify the doctor name."
    db     = load_db()
    doctor = next((d for d in db["doctors"] if query in d["name"].lower()), None)
    if not doctor:
        return "ERROR: Doctor Not Found"
    free = _free_slots(doctor, _get_booked_slots(db, doctor["id"]))
    if not free:
        return "ERROR: No Slots Available"

    # Return English slots — the LLM agent will translate them into the user's language
    # (Odia, Hindi, or English) before speaking, as instructed in the system prompt.
    return f"Slots available for {doctor['name']} ({doctor['specialty']}): {', '.join(free[:4])}"

def _tool_book_appointment(call_id: str, args: dict) -> str:
    patient_name  = args.get("patient_name",  "").strip()
    patient_phone = args.get("patient_phone", "").strip()
    day           = args.get("day",  "").strip()
    time_slot     = args.get("time", "").strip()

    # Revert native language strings back to English strictly for Database lookups
    # — Odia day names —
    day = day.replace("ସୋମବାର", "Monday").replace("ମଙ୍ଗଳବାର", "Tuesday").replace("ବୁଧବାର", "Wednesday")
    day = day.replace("ଗୁରୁବାର", "Thursday").replace("ବୃହସ୍ପତିବାର", "Thursday").replace("ଶୁକ୍ରବାର", "Friday").replace("ଶନିବାର", "Saturday").replace("ରବିବାର", "Sunday")
    # — Hindi day names —
    day = day.replace("सोमवार", "Monday").replace("मंगलवार", "Tuesday").replace("बुधवार", "Wednesday")
    day = day.replace("गुरुवार", "Thursday").replace("शुक्रवार", "Friday").replace("शनिवार", "Saturday").replace("रविवार", "Sunday")
    # — Odia time suffixes —
    time_slot = time_slot.replace("ସକାଳେ", "AM").replace("ଦ୍ୱିପ୍ରହରେ", "PM")
    # — Hindi time words —
    time_slot = time_slot.replace("सुबह", "AM").replace("दोपहर", "PM")

    db = load_db()

    # ── Resolve doctor_id (guard against LLM omitting it) ─
    doctor_id = _resolve_doctor_id(args, db)
    if not doctor_id:
        return (
            "I need to know which doctor to book with. "
            "Please tell me the doctor's name and I will complete the booking."
        )

    # ── Resolve phone (fallback to from_number if needed) ─
    patient_phone = _resolve_phone(args, args)

    if not all([patient_name, patient_phone, day, time_slot]):
        missing = [f for f, v in {
            "patient name": patient_name,
            "phone":        patient_phone,
            "day":          day,
            "time":         time_slot,
        }.items() if not v]
        return f"Still need: {', '.join(missing)}. Please provide these to complete the booking."

    doctor = next((d for d in db["doctors"] if d["id"] == doctor_id), None)
    if not doctor:
        return f"Doctor ID '{doctor_id}' not found. Please check the doctor name."

    if not _slot_valid_for_doctor(doctor, day, time_slot):
        return (f"{doctor['name']} is not available on {day} at {time_slot}. "
                f"Their days: {', '.join(doctor['available_days'])}; "
                f"times: {', '.join(doctor['slots'])}.")

    booked   = _get_booked_slots(db, doctor_id)
    slot_key = f"{day} {time_slot}"
    if slot_key in booked:
        alts = _next_available(db, doctor_id, limit=3)
        return (f"'{slot_key}' is already taken. "
                f"Next available: {', '.join(alts) if alts else 'none this week'}.")

    app_id  = f"APP{len(db['current_bookings']) + 200}"
    booking = {
        "appointment_id": app_id,
        "patient_name":   patient_name,
        "patient_phone":  patient_phone,
        "doctor_id":      doctor_id,
        "doctor_name":    doctor["name"],
        "specialty":      doctor["specialty"],
        "day":            day,
        "time":           time_slot,
        "status":         "Confirmed",
        "booked_at":      datetime.now().isoformat(),
    }
    db["current_bookings"].append(booking)
    save_db(db)
    if call_id in SESSIONS:
        SESSIONS[call_id]["last_appointment_id"] = app_id
    log(f"BOOKED {app_id}: {patient_name} → {doctor['name']} on {day} {time_slot}")
    return f"Confirmed! ID: {app_id}. {doctor['name']} ({doctor['specialty']}) on {day} at {time_slot}."

def _tool_modify_appointment(call_id: str, args: dict) -> str:
    app_id   = args.get("appointment_id", "").strip()
    new_day  = args.get("new_day",  "").strip()
    new_time = args.get("new_time", "").strip()

    db      = load_db()
    # Normalise day/time from any spoken language to English for DB storage
    for odia, eng in [("ସୋମବାର","Monday"),("ମଙ୍ଗଳବାର","Tuesday"),("ବୁଧବାର","Wednesday"),
                      ("ଗୁରୁବାର","Thursday"),("ଶୁକ୍ରବାର","Friday"),("ଶନିବାର","Saturday"),("ରବିବାର","Sunday")]:
        new_day = new_day.replace(odia, eng)
    for hindi, eng in [("सोमवार","Monday"),("मंगलवार","Tuesday"),("बुधवार","Wednesday"),
                       ("गुरुवार","Thursday"),("शुक्रवार","Friday"),("शनिवार","Saturday"),("रविवार","Sunday")]:
        new_day = new_day.replace(hindi, eng)
    new_time = new_time.replace("ସକାଳେ", "AM").replace("ଦ୍ୱିପ୍ରହରେ", "PM")
    new_time = new_time.replace("सुबह", "AM").replace("दोपहर", "PM")
    booking = next((b for b in db["current_bookings"] if b["appointment_id"] == app_id), None)
    if not booking:
        return f"Appointment '{app_id}' not found."
    if booking["status"] == "Cancelled":
        return f"'{app_id}' is already cancelled and cannot be modified."

    doctor = next((d for d in db["doctors"] if d["id"] == booking["doctor_id"]), None)
    if doctor and not _slot_valid_for_doctor(doctor, new_day, new_time):
        return (f"{booking['doctor_name']} is not available on {new_day} at {new_time}. "
                f"Their days: {', '.join(doctor['available_days'])}.")

    booked = _get_booked_slots(db, booking["doctor_id"], exclude_app_id=app_id)
    if f"{new_day} {new_time}" in booked:
        alts = _next_available(db, booking["doctor_id"], exclude=app_id, limit=3)
        return f"'{new_day} {new_time}' is taken. Alternatives: {', '.join(alts) if alts else 'none'}."

    old = f"{booking['day']} {booking['time']}"
    booking["day"], booking["time"] = new_day, new_time
    save_db(db)
    log(f"MODIFIED {app_id}: {old} → {new_day} {new_time}")
    return f"Updated! {booking['doctor_name']} on {new_day} at {new_time}. ID: {app_id}."

def _tool_cancel_appointment(call_id: str, args: dict) -> str:
    app_id  = args.get("appointment_id", "").strip()
    db      = load_db()
    booking = next((b for b in db["current_bookings"] if b["appointment_id"] == app_id), None)
    if not booking:
        return f"Appointment '{app_id}' not found."
    if booking["status"] == "Cancelled":
        return f"'{app_id}' is already cancelled."
    booking["status"] = "Cancelled"
    save_db(db)
    log(f"CANCELLED {app_id} for {booking['patient_name']}")
    return f"Cancelled: {booking['doctor_name']} on {booking['day']} at {booking['time']}. ID: {app_id}."

def _tool_get_patient_appointments(call_id: str, args: dict) -> str:
    phone = args.get("patient_phone", "").strip()
    db    = load_db()
    active = [b for b in db["current_bookings"]
              if b.get("patient_phone") == phone and b["status"] == "Confirmed"]
    if not active:
        return "No active appointments found for this number."
    lines = [f"{b['appointment_id']}: {b['doctor_name']} ({b['specialty']}) — {b['day']} at {b['time']}"
             for b in active]
    return "Your confirmed appointments:\n" + "\n".join(lines)

def _tool_register_patient(call_id: str, args: dict) -> str:
    name  = args.get("name",  "").strip()
    phone = args.get("phone", "").strip()
    db    = load_db()
    existing = next((p for p in db["patients"] if p["phone"] == phone), None)
    if existing:
        return f"{existing['name']} is already registered with us."
    db["patients"].append({"phone": phone, "name": name, "history": "", "registered": True})
    save_db(db)
    if call_id in SESSIONS:
        SESSIONS[call_id].update({"patient_name": name, "patient_phone": phone, "is_existing": True})
    log(f"REGISTERED: {name} ({phone})")
    return f"Welcome, {name}! You are now registered at City Health Institute. How can I help you?"


# ═══════════════════════════════════════════════════════════
# BOLNA TOOL ENDPOINTS
# Each tool is a separate POST endpoint — Bolna calls them directly.
# Bolna sends: { "patient_name": "...", "doctor_id": "...", ... }
# We return:   { "result": "..." }
# The call_id comes from Bolna's context variable {call_sid}
# ═══════════════════════════════════════════════════════════

def _call_id_from_request(body: dict) -> str:
    """Extract call_id from Bolna's injected context variables."""
    return body.get("call_sid") or body.get("call_id") or "unknown"

def _safe_tool(call_id: str, fn, args: dict) -> JSONResponse:
    try:
        result = fn(call_id, args)
        log(f"TOOL ◀ {result[:100]}{'…' if len(result) > 100 else ''}")
        return JSONResponse({"result": result})
    except RuntimeError:
        return JSONResponse({"result": "Our systems are briefly unavailable. Please call back in a moment."})
    except Exception as e:
        log(f"TOOL ERROR: {traceback.format_exc()}")
        return JSONResponse({"result": "Something went wrong. Please try again."})


@app.post("/tool/check-specialty")
@limiter.limit("60/minute")
async def tool_check_specialty(request: Request):
    body    = await request.json()
    call_id = _call_id_from_request(body)
    log(f"TOOL ▶ check_specialty | {body}")
    return _safe_tool(call_id, _tool_check_specialty, body)

@app.post("/tool/check-doctor")
@limiter.limit("60/minute")
async def tool_check_doctor(request: Request):
    body    = await request.json()
    call_id = _call_id_from_request(body)
    log(f"TOOL ▶ check_doctor | {body}")
    return _safe_tool(call_id, _tool_check_doctor, body)

@app.post("/tool/book-appointment")
@limiter.limit("30/minute")
async def tool_book_appointment(request: Request):
    body    = await request.json()
    body["patient_phone"] = _resolve_phone(body, body)
    call_id = _call_id_from_request(body)
    log(f"TOOL ▶ book_appointment | {body}")
    return _safe_tool(call_id, _tool_book_appointment, body)

@app.post("/tool/modify-appointment")
@limiter.limit("30/minute")
async def tool_modify_appointment(request: Request):
    body    = await request.json()
    call_id = _call_id_from_request(body)
    log(f"TOOL ▶ modify_appointment | {body}")
    return _safe_tool(call_id, _tool_modify_appointment, body)

@app.post("/tool/cancel-appointment")
@limiter.limit("30/minute")
async def tool_cancel_appointment(request: Request):
    body    = await request.json()
    call_id = _call_id_from_request(body)
    log(f"TOOL ▶ cancel_appointment | {body}")
    return _safe_tool(call_id, _tool_cancel_appointment, body)

@app.post("/tool/get-appointments")
@limiter.limit("60/minute")
async def tool_get_appointments(request: Request):
    body    = await request.json()
    body["patient_phone"] = _resolve_phone(body, body)
    call_id = _call_id_from_request(body)
    log(f"TOOL ▶ get_patient_appointments | {body}")
    return _safe_tool(call_id, _tool_get_patient_appointments, body)

@app.post("/tool/register-patient")
@limiter.limit("30/minute")
async def tool_register_patient(request: Request):
    body    = await request.json()
    body["phone"] = _resolve_phone(body, body)
    call_id = _call_id_from_request(body)
    log(f"TOOL ▶ register_patient | {body}")
    return _safe_tool(call_id, _tool_register_patient, body)


# ═══════════════════════════════════════════════════════════
# BOLNA WEBHOOK
# Receives call lifecycle events from Bolna's Analytics tab webhook URL
# ═══════════════════════════════════════════════════════════

@app.post("/webhook/bolna")
@limiter.limit("60/minute")
async def bolna_webhook(request: Request):
    """
    Bolna posts call lifecycle events here.
    Configure this URL in: Bolna Dashboard → Agent → Analytics Tab → Webhook URL
    """
    try:
        body = await request.json()
    except Exception:
        return err("INVALID_JSON", "Invalid JSON")

    event_type = body.get("type") or body.get("status") or body.get("event")
    call_id    = body.get("call_sid") or body.get("call_id") or body.get("id", "unknown")
    phone      = body.get("from_number") or body.get("customer_number", "unknown")

    log(f"BOLNA EVENT | {event_type} | {call_id}")

    # ── Call started ──────────────────────────────────────
    if event_type in ("call_started", "initiated", "ringing", "in-progress"):
        session = _init_session(call_id, phone)
        log(f"CALL START | {phone} | {session['patient_name']}")
        return {"status": "ok"}

    # ── Transcript / language update ──────────────────────
    if event_type in ("transcript", "speech_final"):
        if call_id in SESSIONS and body.get("language_code"):
            lang = body["language_code"].split("-")[0]   # "od-IN" → "or", "hi-IN" → "hi"
            lang_map = {"od": "or", "hi": "hi", "en": "en"}
            SESSIONS[call_id]["language"] = lang_map.get(lang, lang)
            log(f"LANG SET: {SESSIONS[call_id]['language']} | {call_id}")
        return {"status": "ok"}

    # ── Call ended ────────────────────────────────────────
    if event_type in ("call_completed", "completed", "call_ended", "disconnected", "hangup"):
        transcript = (body.get("transcript")
                      or body.get("conversation_transcript")
                      or "")
        _close_session(call_id, transcript)
        log(f"CALL END | {call_id} | duration={body.get('duration_ms', '?')}ms")
        return {"status": "ok"}

    # ── Call failed ───────────────────────────────────────
    if event_type in ("call_failed", "failed", "no-answer", "busy"):
        log(f"CALL FAILED | {call_id} | reason={body.get('reason', '?')}")
        _close_session(call_id, "")
        return {"status": "ok"}

    return {"status": "unhandled", "event": event_type}


# ═══════════════════════════════════════════════════════════
# DTMF HANDLER
# Enable "Keypad Input (DTMF)" in Bolna → Call Tab
# Then set this as your keypad webhook URL
# ═══════════════════════════════════════════════════════════

@app.post("/webhook/dtmf")
@limiter.limit("30/minute")
async def dtmf_handler(request: Request):
    try:
        body = await request.json()
    except Exception:
        return err("INVALID_JSON", "Invalid JSON")

    call_id = _call_id_from_request(body)
    digit   = str(body.get("digit", "")).strip()
    action  = DTMF_MENU.get(digit)

    if not action:
        return {"result": "Invalid option. Press 1 to book, 2 to modify, 3 to cancel, 4 to check availability, or 0 for operator."}

    if action == "speak_to_operator":
        log(f"DTMF | {call_id} → transfer to operator")
        return {"result": "Transferring you to our reception staff. Please hold."}

    log(f"DTMF | {call_id} → {action}")
    return {"result": f"The caller wants to: {action.replace('_', ' ')}. Please proceed."}


# ═══════════════════════════════════════════════════════════
# OUTBOUND CALL — Bolna trigger
# ═══════════════════════════════════════════════════════════

@app.post("/trigger-call")
@limiter.limit("10/minute")
async def trigger_call(request: Request):
    """
    Trigger an outbound call via PLIVO (not Bolna).
    Plivo dials the number → callee picks up → /plivo/answer → /plivo/stream
    Body: { "to": "+919876543210" }
    """
    try:
        body = await request.json()
    except Exception:
        return err("INVALID_JSON", "Invalid JSON")

    to          = body.get("to", "").strip()
    from_number = os.getenv("PLIVO_FROM_NUMBER", "")

    if not to:
        return err("NO_NUMBER", "Provide a 'to' phone number in E.164 format")
    if not PLIVO_AUTH_ID or not PLIVO_AUTH_TOKEN:
        return err("NO_PLIVO_CREDS", "PLIVO_AUTH_ID / PLIVO_AUTH_TOKEN not set in .env", 500)
    if not from_number:
        return err("NO_FROM_NUMBER", "PLIVO_FROM_NUMBER not set in .env", 500)

    host       = PUBLIC_HOST or "concededly-cognominal-beryl.ngrok-free.dev"
    answer_url = f"https://{host}/plivo/answer"

    payload = {
        "from":          from_number,
        "to":            to,
        "answer_url":    answer_url,
        "answer_method": "POST",
    }

    try:
        async with httpx.AsyncClient(timeout=15) as client:
            r = await client.post(
                f"https://api.plivo.com/v1/Account/{PLIVO_AUTH_ID}/Call/",
                json=payload,
                auth=(PLIVO_AUTH_ID, PLIVO_AUTH_TOKEN),
            )
            r.raise_for_status()
            data    = r.json()
            call_id = data.get("request_uuid", "unknown")
            log(f"PLIVO OUTBOUND triggered | to={to} | call_id={call_id}")
            return {"status": "initiated", "call_id": call_id, "to": to}
    except httpx.HTTPStatusError as e:
        return err("PLIVO_ERROR", f"Plivo API: {e.response.status_code} — {e.response.text}", 502)
    except Exception as e:
        log(f"trigger-call failed: {e}")
        return err("CALL_FAILED", str(e), 500)


# ═══════════════════════════════════════════════════════════
# HEALTH ENDPOINT
# ═══════════════════════════════════════════════════════════

@app.get("/health")
async def health():
    try:
        load_db()
        db_ok = True
    except Exception:
        db_ok = False
    return {
        "status":      "healthy" if db_ok else "degraded",
        "db":          "ok" if db_ok else "error",
        "bolna_key":   "configured" if BOLNA_API_KEY  else "missing",
        "bolna_agent": "configured" if BOLNA_AGENT_ID else "missing",
        "sessions":    len(SESSIONS),
        "version":     "5.0",
    }


# ═══════════════════════════════════════════════════════════
# DASHBOARD & UTILITY ENDPOINTS
# ═══════════════════════════════════════════════════════════

@app.get("/demo-state")
async def get_state():
    db = load_db()
    return {
        "appointments":   db["current_bookings"],
        "active_call":    ACTIVE_CALL,
        "thoughts":       THOUGHT_LOG[-10:],
        "sessions_count": len(SESSIONS),
        "transcripts":    len(db.get("call_transcripts", [])),
    }

@app.get("/availability")
async def get_availability():
    return _build_slot_matrix(load_db())

@app.get("/doctors")
async def list_doctors():
    return load_db()["doctors"]

@app.get("/specialties")
async def list_specialties():
    return load_db()["specialties"]

@app.get("/transcripts")
async def list_transcripts():
    return load_db().get("call_transcripts", [])

@app.post("/webhook/identify-caller")
async def identify(phone: str):
    """Dashboard demo button — simulates a call without Bolna."""
    call_id = f"DEMO-{uuid.uuid4().hex[:8]}"
    session = _init_session(call_id, phone)
    log(f"DEMO CALL | {phone} | {session['patient_name']}")
    return {"type": "EXISTING" if session["is_existing"] else "NEW",
            "name": session["patient_name"], "call_id": call_id}

@app.post("/clear-demo")
async def clear_demo():
    global ACTIVE_CALL
    ACTIVE_CALL = None
    THOUGHT_LOG.clear()
    return {"status": "cleared"}



# ═══════════════════════════════════════════════════════════
# PLIVO VOICE PIPELINE  (replaces Bolna)
# ═══════════════════════════════════════════════════════════
#
# ── Wait messages for latency masking ─────────────────────────────────
WAIT_MSGS = {
    "or": "ଟିକେ ମୁହୂର୍ତ୍ତ ଅପେକ୍ଷା କରନ୍ତୁ",
    "hi": "कृपया एक पल प्रतीक्षा करें",
    "en": "Please wait a moment."
}

# ═══════════════════════════════════════════════════════════

# ── Tool executor: bridges GPT-4o tool calls → local _tool_* ─────────

async def _tool_executor(tool_name: str, args: dict, call_sid: str) -> str:
    """
    Called by ConversationManager when GPT-4o invokes a tool.
    Routes to the existing _tool_* functions in this file.
    """
    try:
        fn_map = {
            "check_specialty_availability": _tool_check_specialty,
            "check_doctor_availability":    _tool_check_doctor,
            "book_appointment":             _tool_book_appointment,
            "modify_appointment":           _tool_modify_appointment,
            "cancel_appointment":           _tool_cancel_appointment,
            "get_patient_appointments":     _tool_get_patient_appointments,
            "register_new_patient":         _tool_register_patient,
        }
        fn = fn_map.get(tool_name)
        if not fn:
            return f"Unknown tool: {tool_name}"
        result = fn(call_sid, args)
        log(f"TOOL [{tool_name}] ◀ {result[:80]}")
        return result
    except Exception as e:
        log(f"TOOL ERROR [{tool_name}]: {e}")
        return "Tool error. Please try again."


# ── Helper: send mulaw audio back to Plivo over the WebSocket ─────────

async def _plivo_play(ws: WebSocket, mulaw_bytes: bytes):
    """Send TTS audio to Plivo as base64-encoded mulaw in JSON."""
    if not mulaw_bytes:
        return
    payload = base64.b64encode(mulaw_bytes).decode()
    await ws.send_text(json.dumps({
        "event": "playAudio",
        "media": {
            "contentType": "audio/x-mulaw",
            "sampleRate":  8000,
            "payload":     payload,
        },
    }))


# ── Plivo Outbound Call Trigger ────────────────────────────────────────

@app.post("/trigger-call")
async def trigger_outbound_call(request: Request):
    """
    Initiates an outbound call from your Plivo number to the patient.
    Expects JSON: {"to": "+91XXXXXXXXXX"}
    """
    data = await request.json()
    to_number = data.get("to")
    
    # Needs a Plivo FROM number from .env
    from_number = os.getenv("PLIVO_FROM_NUMBER", "")
    
    if not from_number:
        return JSONResponse({"error": "PLIVO_FROM_NUMBER not set in .env"}, status_code=400)
    if not to_number:
        return JSONResponse({"error": "Missing 'to' number formatting: +91XXXXXXXXXX"}, status_code=400)

    # The Answer URL must point to your /plivo/answer webhook
    host = PUBLIC_HOST or request.headers.get("host", "")
    answer_url = f"https://{host}/plivo/answer"

    auth = httpx.BasicAuth(PLIVO_AUTH_ID, PLIVO_AUTH_TOKEN)
    
    payload = {
        "from": from_number,
        "to": to_number,
        "answer_url": answer_url,
        "answer_method": "POST"
    }

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"https://api.plivo.com/v1/Account/{PLIVO_AUTH_ID}/Call/",
            json=payload,
            auth=auth
        )
        
    if resp.status_code in (200, 201):
        log(f"Triggered outbound call to {to_number}")
        return {"status": "success", "message": f"Calling {to_number}...", "plivo_response": resp.json()}
    else:
        log(f"Failed to trigger call: {resp.text}")
        return JSONResponse({"error": "Plivo API failed", "details": resp.json()}, status_code=resp.status_code)


# ── Plivo answer webhook ───────────────────────────────────────────────

@app.get("/plivo/answer")
@app.post("/plivo/answer")
async def plivo_answer(request: Request):
    """
    Plivo calls this URL when a new call comes in.
    We return XML telling Plivo to open a bidirectional audio stream
    to our /plivo/stream WebSocket endpoint.

    Configure in Plivo console:
      Answer URL:  https://<PUBLIC_HOST>/plivo/answer
      Answer method: GET or POST
    """
    params  = dict(request.query_params)
    call_id = params.get("CallUUID", "unknown")
    caller  = params.get("From", "unknown")
    log(f"PLIVO ANSWER | CallUUID={call_id} | From={caller}")

    # Build the WSS stream URL
    host       = PUBLIC_HOST or request.headers.get("host", "localhost")
    stream_url = f"wss://{host}/plivo/stream"

    xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
  <Stream bidirectional="true" keepCallAlive="true"
          contentType="audio/x-mulaw;rate=8000"
          extraHeaders="CallUUID={call_id}&amp;From={caller}">
    {stream_url}
  </Stream>
</Response>"""
    return Response(content=xml, media_type="application/xml")


# ── Plivo bidirectional WebSocket stream ──────────────────────────────

@app.websocket("/plivo/stream")
async def plivo_stream(ws: WebSocket):
    """
    Handles the bidirectional audio WebSocket from Plivo.

    Incoming JSON from Plivo:
      {"event": "start",  "start": {...}}
      {"event": "media",  "media": {"payload": "<base64_mulaw>"}}
      {"event": "stop"}

    We respond with:
      {"event": "playAudio", "media": {"contentType": ..., "payload": ...}}
    """
    await ws.accept()
    log("PLIVO STREAM | WebSocket opened")

    call_sid    = f"PLIVO-{uuid.uuid4().hex[:8]}"
    from_number = "unknown"
    conversation: ConversationManager | None = None
    stt: SarvamSTT | None = None
    stt_task    = None
    is_speaking = False   # True while TTS is playing

    async def on_thinking(lang: str):
        """Plays a 'wait' message instantly while LLM/Tools are working."""
        nonlocal is_speaking
        text = WAIT_MSGS.get(lang, WAIT_MSGS["en"])
        log(f"STREAM | Playing 'wait' message in [{lang}]: {text}")
        audio = await sarvam_tts(text, lang, SARVAM_API_KEY)
        if audio:
            await _plivo_play(ws, audio)

    async def on_transcript(text: str, lang: str, is_final: bool):
        nonlocal is_speaking, conversation
        if not is_final or not text.strip():
            return
        if is_speaking:
            log(f"STREAM | Skipping transcript (TTS busy): {text}")
            return

        log(f"STREAM | User [{lang}]: {text}")
        if conversation is None:
            return

        try:
            is_speaking = True
            llm_text = await conversation.get_response(text, lang)   # ← pass lang
            log(f"STREAM | Agent [{lang}]: {llm_text[:80]}")
            audio = await sarvam_tts(llm_text, lang, SARVAM_API_KEY)
            await _plivo_play(ws, audio)
        except Exception as e:
            log(f"STREAM | Pipeline error: {e}")
        finally:
            is_speaking = False

    try:
        async for raw in ws.iter_text():
            data  = json.loads(raw)
            event = data.get("event")

            # ── Call starts ───────────────────────────────────────────
            if event == "start":
                meta        = data.get("start", {})
                call_sid    = meta.get("callSid") or meta.get("callId") or call_sid
                custom      = meta.get("customParameters") or meta.get("extraHeaders") or {}
                from_number = custom.get("From") or meta.get("from_number") or "+91000000000"

                log(f"PLIVO STREAM START | {call_sid} | from={from_number}")
                
                # FORCE NUMBER: as requested by user
                from_number = "+918510840607"
                log(f"PLIVO STREAM | FORCING NUMBER to: {from_number}")
                
                _init_session(call_sid, from_number)

                # Build conversation manager with custom 'wait' callback
                conversation = ConversationManager(
                    call_sid, 
                    from_number, 
                    _tool_executor, 
                    on_thinking=on_thinking
                )

                # ── Play greeting FIRST so user always hears it ───────
                is_speaking = True
                log("Playing opening greeting via Sarvam TTS...")
                greeting_audio = await sarvam_tts(OPENING_GREETING, OPENING_LANG, SARVAM_API_KEY)
                if greeting_audio:
                    await _plivo_play(ws, greeting_audio)
                    log(f"✓ Greeting played ({len(greeting_audio)} bytes)")
                else:
                    log("⚠ Greeting TTS returned empty — check SARVAM_API_KEY")
                is_speaking = False

                # ── Connect STT after greeting ────────────────────────
                try:
                    stt = SarvamSTT(SARVAM_API_KEY)
                    await stt.connect()
                    stt_task = asyncio.create_task(stt.run(on_transcript))
                    log("✓ Sarvam STT connected")
                except Exception as stt_err:
                    log(f"⚠ STT connection failed: {stt_err}")

            # ── Audio chunk from caller ───────────────────────────────
            elif event == "media":
                if stt and not is_speaking:
                    payload = data["media"]["payload"]
                    await stt.send_audio(base64.b64decode(payload))

            # ── Call ends ─────────────────────────────────────────────
            elif event == "stop":
                log(f"PLIVO STREAM STOP | {call_sid}")
                break

    except WebSocketDisconnect:
        log(f"PLIVO STREAM | WebSocket disconnected | {call_sid}")
    except Exception as e:
        log(f"PLIVO STREAM ERROR | {e}\n{traceback.format_exc()}")
    finally:
        if stt:
            await stt.close()
        if stt_task:
            stt_task.cancel()
        _close_session(call_sid, "")
        log(f"PLIVO STREAM | Cleaned up | {call_sid}")


# ═══════════════════════════════════════════════════════════
# ENTRYPOINT
# ═══════════════════════════════════════════════════════════

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=PORT, reload=True)

