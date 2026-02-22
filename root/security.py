import json
from rag import retrieve


def filter_data_for_role(raw_data: dict, role: str) -> dict:
    if role == "student":
        return {
            "role":       "student",
            "username":   raw_data.get("username"),
            "profile":    raw_data.get("profile"),
            "attendance": raw_data.get("attendance"),
            "timetable":  raw_data.get("timetable"),
        }
    elif role == "faculty":
        return {
            "role":       "faculty",
            "username":   raw_data.get("username"),
            "profile":    raw_data.get("profile"),
            "attendance": raw_data.get("attendance"),   
            "timetable":  raw_data.get("timetable"),    
        }
    elif role == "parent":
        return {
            "role":       "parent",
            "username":   raw_data.get("username"),
            "profile":    raw_data.get("profile"),
            "attendance": raw_data.get("attendance"),
        }
    elif role == "guest":
        return {
            "role":        "guest",
            "public_info": raw_data.get("public_pesu_info", {}),
        }
    else:
        return {"role": "unknown", "error": "Unrecognised role."}



_PERSONAS = {
    "student": (
        "You are PESU Reimagined, a smart academic assistant for PES University students. "
        "Help with attendance, timetable, CGPA, and academic standing. "
        "When showing attendance use a markdown table: | Subject | % | Status |. "
        "Mark below 75% as AT RISK, 75-84% as CAUTION, 85%+ as SAFE. "
        "Thresholds matter — always flag AT RISK subjects clearly. "
        "Be concise and use markdown."
    ),
    "faculty": (
        "You are PESU Reimagined in Faculty Mode for PES University. "
        "You are speaking with a faculty member or teaching assistant, not a student. "
        "Their timetable is a TEACHING schedule — refer to classes as sessions they conduct, not attend. "
        "Their attendance record reflects their own professional compliance, not academic risk. "
        "Do not use student-facing language like \'safe to bunk\' or \'debarment risk\'. "
        "Instead focus on: teaching load, schedule overview, department policies, exam/CIA timelines. "
        "If asked about other students\' data, say: \'Individual student data is not accessible in faculty mode.\' "
        "Use markdown."
    ),
    "parent": (
        "You are PESU Reimagined in Parent Mode for PES University. "
        "You are speaking with a parent viewing their child\'s academic record. "
        "Present attendance clearly. Flag anything below 85% as a concern worth discussing. "
        "Below 75% is critical — explain debarment risk plainly. "
        "Use markdown."
    ),
    "guest": (
        "You are PESU Reimagined in Guest Mode for PES University. "
        "The user is NOT logged in. Answer only from the data and knowledge base provided. "
        "For personal questions say: \'Please log in to access your personal data.\' "
        "Never invent specific personal details. Use markdown."
    ),
}


def build_ai_context(filtered: dict, user_msg: str) -> str:
    role    = filtered.get("role", "unknown")
    persona = _PERSONAS.get(role, "You are PESU Reimagined, a PES University academic assistant.")

    data = dict(filtered)
    if "attendance" in data and isinstance(data["attendance"], dict) and data["attendance"]:
        try:
            latest = str(max(data["attendance"].keys(), key=int))
            data["attendance"] = {latest: data["attendance"][latest]}
        except Exception:
            pass

    data_str = json.dumps(data, indent=2, default=str)

    rag_block = retrieve(user_msg)
    rag_section = (
        f"\n\nSTATIC KNOWLEDGE BASE (use this to answer institutional questions):\n{rag_block}"
        if rag_block else ""
    )

    return (
        f"{persona}\n\n"
        "RULES:\n"
        "- Use ONLY the personal data and knowledge base provided. Never invent.\n"
        "- If something is missing say: \'I do not have that information.\'\n"
        "- Read all keys in each course object to find subject name and percentage.\n\n"
        f"USER ROLE: {role}\n\n"
        f"PERSONAL DATA:\n{data_str}"
        f"{rag_section}\n\n"
        f"QUESTION: {user_msg}\n\n"
        "Answer helpfully and concisely. Use markdown."
    )