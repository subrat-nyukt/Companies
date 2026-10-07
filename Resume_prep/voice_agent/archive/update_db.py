import json
import re

with open('hospital_db.json', 'r', encoding='utf-8') as f:
    db = json.load(f)

# Update doctors
doctors = [
    {
        "id": "DR001",
        "name": "Dr. ANUPAM JENA",
        "specialty": "Cardiology",
        "available_days": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"],
        "slots": ["9:00 AM", "10:00 AM", "11:00 AM"],
        "max_per_slot": 1
    },
    {
        "id": "DR002",
        "name": "Dr. SUBASIS MISHRA",
        "specialty": "Cardiology",
        "available_days": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"],
        "slots": ["3:00 PM", "4:00 PM", "5:00 PM"],
        "max_per_slot": 1
    },
    {
        "id": "DR003",
        "name": "Dr. SANTOSH RATH",
        "specialty": "Orthopedics",
        "available_days": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"],
        "slots": ["10:00 AM", "2:00 PM", "3:00 PM"],
        "max_per_slot": 1
    },
    {
        "id": "DR004",
        "name": "Dr. DEBASHIS MISHRA",
        "specialty": "Orthopedics",
        "available_days": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"],
        "slots": ["3:00 PM", "4:00 PM", "5:00 PM"],
        "max_per_slot": 1
    },
    {
        "id": "DR005",
        "name": "Dr. OM MISHRA",
        "specialty": "Neurology",
        "available_days": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"],
        "slots": ["11:00 AM", "12:00 PM", "1:00 PM"],
        "max_per_slot": 1
    },
    {
        "id": "DR006",
        "name": "Dr. PRERANA DASH",
        "specialty": "Neurology",
        "available_days": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"],
        "slots": ["3:00 PM", "4:00 PM", "5:00 PM"],
        "max_per_slot": 1
    }
]

db['doctors'] = doctors
db['specialties'] = ["Cardiology", "Orthopedics", "Neurology"]

with open('hospital_db.json', 'w', encoding='utf-8') as f:
    json.dump(db, f, indent=4)

# Update agent_prompt.py
with open('agent_prompt.py', 'r', encoding='utf-8') as f:
    prompt_content = f.read()

old_doctors_str = """Doctor ID Reference (use these exact IDs when calling book_appointment):
- Dr. Suresh Mahapatra  → DR001  (Cardiology)
- Dr. Priya Nanda       → DR002  (Cardiology)
- Dr. Ramesh Pattnaik   → DR003  (Orthopedics)
- Dr. Anjali Mishra     → DR004  (Neurology)
- Dr. Bikash Mohanty    → DR005  (Pediatrics)
- Dr. Sarita Das        → DR006  (Gynecology)
- Dr. Arun Sahoo        → DR007  (General Medicine)
- Dr. Lipsa Rath        → DR008  (Dermatology)
- Dr. Nirmal Behera     → DR009  (ENT)"""

new_doctors_str = """Doctor ID Reference (use these exact IDs when calling book_appointment):
- Dr. ANUPAM JENA       → DR001  (Cardiology)
- Dr. SUBASIS MISHRA    → DR002  (Cardiology)
- Dr. SANTOSH RATH      → DR003  (Orthopedics)
- Dr. DEBASHIS MISHRA   → DR004  (Orthopedics)
- Dr. OM MISHRA         → DR005  (Neurology)
- Dr. PRERANA DASH      → DR006  (Neurology)"""

prompt_content = prompt_content.replace(old_doctors_str, new_doctors_str)

with open('agent_prompt.py', 'w', encoding='utf-8') as f:
    f.write(prompt_content)
