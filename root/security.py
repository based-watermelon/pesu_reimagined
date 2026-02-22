import json

def filter_data_for_role(raw_data, role):
    if role == "student":
        return {
            "role": "student",
            "username": raw_data.get("username"),
            "attendance": raw_data.get("attendance"),
            "timetable": raw_data.get("timetable"),
        }
    elif role == "parent":
        att = raw_data.get("attendance")
        return {
            "role": "parent",
            "child": raw_data.get("username"),
            "attendance_summary": "Data available" if att else "No data",
        }
    elif role == "faculty":
        return {"role": "faculty", "note": "Faculty view coming soon."}
    else:  
        return {
            "role": "guest",
            "public_info": "PESU minimum attendance is 75%. Merit scholarships require 9.0 CGPA.",
            "note": "Please log in to access personal data.",
        }

def build_ai_context(filtered, user_msg):
    data_str = json.dumps(filtered, indent=2, default=str)
    return (
        "You are PESU-Reimagined, a helpful academic assistant for PES University.\n"
        "Only use the data provided. Never invent or assume data.\n"
        "If something is missing say: I do not have that information.\n\n"
        f"USER ROLE: {filtered.get('role')}\n"
        f"DATA:\n{data_str}\n\n"
        f"QUESTION: {user_msg}\n\nAnswer helpfully and concisely."
    )   