"""
Bolna Custom Function Schema Generator for ChikitAI
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

HOW TO USE:
  1. Run:  python bolna_tool_schemas.py https://concededly-cognominal-beryl.ngrok-free.dev
  2. This prints 7 JSON blocks, one per tool
  3. In Bolna: Agent → Tools Tab → Add function → Add your own custom function
  4. Paste each JSON block into the editor, click Save

The URL is your ngrok public URL (printed when you run python main.py).
"""

import json, sys

def schemas(base_url: str) -> list:
    return [

        # ── 1. Check Specialty ────────────────────────────────────
        {
            "name": "check_specialty_availability",
            "description": "Use this when the caller asks which doctors are available for a medical specialty like Cardiology, Orthopedics, Neurology, Pediatrics, Gynecology, General Medicine, Dermatology, or ENT. Returns doctor names and available time slots.",
            "pre_call_message": "",
            "parameters": {
                "type": "object",
                "properties": {
                    "specialty": {
                        "type": "string",
                        "description": "The medical specialty name, e.g. Cardiology, Orthopedics, ENT"
                    }
                },
                "required": ["specialty"]
            },
            "key": "custom_task",
            "value": {
                "method": "POST",
                "param": {
                    "specialty": "%(specialty)s",
                    "call_sid":  "%(call_sid)s"
                },
                "url":       f"{base_url}/tool/check-specialty",
                "api_token": "",
                "headers":   {}
            }
        },

        # ── 2. Check Doctor ───────────────────────────────────────
        {
            "name": "check_doctor_availability",
            "description": "Use this when the caller asks about a specific doctor's available time slots, e.g. 'Is Dr. Mahapatra available?' or 'When can I see Dr. Nanda?'. Returns free slots for that doctor.",
            "pre_call_message": "",
            "parameters": {
                "type": "object",
                "properties": {
                    "doctor_name": {
                        "type": "string",
                        "enum": [
                            "ANUPAM JENA", "SUBASIS MISHRA", "SANTOSH RATH", 
                            "DEBASHIS MISHRA", "OM MISHRA", "PRERANA DASH"
                        ],
                        "description": "Full name of the doctor in English ONLY. Pick the closest match from the provided options."
                    }
                },
                "required": ["doctor_name"]
            },
            "key": "custom_task",
            "value": {
                "method": "POST",
                "param": {
                    "doctor_name": "%(doctor_name)s",
                    "call_sid":    "%(call_sid)s"
                },
                "url":       f"{base_url}/tool/check-doctor",
                "api_token": "",
                "headers":   {}
            }
        },

        # ── 3. Book Appointment ───────────────────────────────────
        {
            "name": "book_appointment",
            "description": "Use this ONLY after the caller has confirmed the doctor, day, and time. Books a new appointment. Always repeat back the doctor name, day, and time and get explicit yes confirmation before calling this.",
            "pre_call_message": "",
            "parameters": {
                "type": "object",
                "properties": {
                    "patient_name": {
                        "type": "string",
                        "description": "Full name of the patient"
                    },
                    "patient_phone": {
                        "type": "string",
                        "description": "Patient phone number. MUST be in digit format, e.g. 8510840607 or +919876543210. IF user says number in Odia words (like ଆଠ ପାଞ୍ଚ), translate it to English digits BEFORE passing here. NEVER pass Odia words in this field."
                    },
                    "doctor_id": {
                        "type": "string",
                        "description": "Doctor ID from the reference table: DR001=Dr. ANUPAM JENA, DR002=Dr. SUBASIS MISHRA, DR003=Dr. SANTOSH RATH, DR004=Dr. DEBASHIS MISHRA, DR005=Dr. OM MISHRA, DR006=Dr. PRERANA DASH. Always include this."
                    },
                    "doctor_name": {
                        "type": "string",
                        "description": "Full name of the doctor, e.g. Dr. Priya Nanda. Include alongside doctor_id as a fallback."
                    },
                    "day": {
                        "type": "string",
                        "description": "Day of the week, e.g. Monday, Wednesday"
                    },
                    "time": {
                        "type": "string",
                        "description": "Time slot, e.g. 10:00 AM"
                    }
                },
                "required": ["patient_name", "patient_phone", "doctor_id", "day", "time"]
            },
            "key": "custom_task",
            "value": {
                "method": "POST",
                "param": {
                    "patient_name":  "%(patient_name)s",
                    "patient_phone": "%(patient_phone)s",
                    "doctor_id":     "%(doctor_id)s",
                    "doctor_name":   "%(doctor_name)s",
                    "day":           "%(day)s",
                    "time":          "%(time)s",
                    "call_sid":      "%(call_sid)s"
                },
                "url":       f"{base_url}/tool/book-appointment",
                "api_token": "",
                "headers":   {}
            }
        },

        # ── 4. Modify Appointment ─────────────────────────────────
        {
            "name": "modify_appointment",
            "description": "Use this when the caller wants to reschedule an existing appointment. First call get_patient_appointments to find the appointment ID. Always confirm the new day and time before calling this.",
            "pre_call_message": "",
            "parameters": {
                "type": "object",
                "properties": {
                    "appointment_id": {
                        "type": "string",
                        "description": "The appointment ID to modify, e.g. APP101"
                    },
                    "new_day": {
                        "type": "string",
                        "description": "New day of the week, e.g. Thursday"
                    },
                    "new_time": {
                        "type": "string",
                        "description": "New time slot, e.g. 2:00 PM"
                    }
                },
                "required": ["appointment_id", "new_day", "new_time"]
            },
            "key": "custom_task",
            "value": {
                "method": "POST",
                "param": {
                    "appointment_id": "%(appointment_id)s",
                    "new_day":        "%(new_day)s",
                    "new_time":       "%(new_time)s",
                    "call_sid":       "%(call_sid)s"
                },
                "url":       f"{base_url}/tool/modify-appointment",
                "api_token": "",
                "headers":   {}
            }
        },

        # ── 5. Cancel Appointment ─────────────────────────────────
        {
            "name": "cancel_appointment",
            "description": "Use this when the caller wants to cancel an existing appointment. First call get_patient_appointments to find the appointment ID. Always ask 'Are you sure you want to cancel?' and get confirmation before calling this.",
            "pre_call_message": "",
            "parameters": {
                "type": "object",
                "properties": {
                    "appointment_id": {
                        "type": "string",
                        "description": "The appointment ID to cancel, e.g. APP101"
                    }
                },
                "required": ["appointment_id"]
            },
            "key": "custom_task",
            "value": {
                "method": "POST",
                "param": {
                    "appointment_id": "%(appointment_id)s",
                    "call_sid":       "%(call_sid)s"
                },
                "url":       f"{base_url}/tool/cancel-appointment",
                "api_token": "",
                "headers":   {}
            }
        },

        # ── 6. Get Patient Appointments ───────────────────────────
        {
            "name": "get_patient_appointments",
            "description": "Use this when the caller asks what appointments they have, or when you need the appointment ID before modifying or cancelling. Returns all confirmed appointments for the given phone number.",
            "pre_call_message": "",
            "parameters": {
                "type": "object",
                "properties": {
                    "patient_phone": {
                        "type": "string",
                        "description": "Patient phone number. MUST be in digit format. IF user says number in Odia words, translate it to English digits BEFORE passing here."
                    }
                },
                "required": ["patient_phone"]
            },
            "key": "custom_task",
            "value": {
                "method": "POST",
                "param": {
                    "patient_phone": "%(patient_phone)s",
                    "call_sid":      "%(call_sid)s"
                },
                "url":       f"{base_url}/tool/get-appointments",
                "api_token": "",
                "headers":   {}
            }
        },

        # ── 7. Register New Patient ───────────────────────────────
        {
            "name": "register_new_patient",
            "description": "Use this when the caller is not yet registered in our system. Collect their full name and phone number first, then call this to register them before proceeding to book an appointment.",
            "pre_call_message": "",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "Full name of the new patient"
                    },
                    "phone": {
                        "type": "string",
                        "description": "Patient phone number. MUST be digits. IF user says number in Odia words, convert to English digits first."
                    }
                },
                "required": ["name", "phone"]
            },
            "key": "custom_task",
            "value": {
                "method": "POST",
                "param": {
                    "name":     "%(name)s",
                    "phone":    "%(phone)s",
                    "call_sid": "%(call_sid)s"
                },
                "url":       f"{base_url}/tool/register-patient",
                "api_token": "",
                "headers":   {}
            }
        },
    ]


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python bolna_tool_schemas.py https://concededly-cognominal-beryl.ngrok-free.dev")
        print()
        print("Example:")
        print("  python bolna_tool_schemas.py https://concededly-cognominal-beryl.ngrok-free.dev")
        sys.exit(1)

    base_url = sys.argv[1].rstrip("/")
    tools    = schemas(base_url)

    print(f"\n{'='*60}")
    print(f"ChikitAI — Bolna Tool Schemas")
    print(f"Server: {base_url}")
    print(f"{'='*60}")
    print("Paste each block below into Bolna → Tools Tab → Add custom function\n")

    for i, tool in enumerate(tools, 1):
        print(f"── Tool {i}/{len(tools)}: {tool['name']} {'─'*(44-len(tool['name']))}")
        print(json.dumps(tool, indent=2))
        print()

    print(f"{'='*60}")
    print(f"All {len(tools)} schemas generated. Paste them one by one into Bolna.")
