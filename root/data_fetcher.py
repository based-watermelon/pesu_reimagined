from pesuacademy import PESUAcademy

async def fetch_student_data(username: str, password: str) -> dict:
    pesu = None
    try:
        pesu = await PESUAcademy.login(username=username, password=password)
        import asyncio
        attendance_data, timetable_data, profile_data = await asyncio.gather(
            pesu.get_attendance(),
            pesu.get_timetable(),
            pesu.get_profile(),
        )
        return {
            "username": username,
            "attendance": _serialize_attendance(attendance_data),
            "timetable": _serialize_timetable(timetable_data),
            "profile": _serialize_profile(profile_data),
        }
    except Exception as e:
        raise Exception(f"PESU fetch failed: {e}")
    finally:
        if pesu:
            await pesu.close()

def _serialize_attendance(data: dict) -> dict:
    result = {}
    for semester, courses in data.items():
        result[str(semester)] = [course.model_dump(mode='json') for course in courses]
    return result

def _serialize_timetable(timetable) -> dict:
    return timetable.model_dump(mode='json') if timetable else {}

def _serialize_profile(profile) -> dict:
    return profile.model_dump(mode='json') if profile else {}

def summarize_for_ai(data: dict) -> str:
    lines = [f"Student: {data.get('username')}"]
    profile = data.get("profile", {})
    if profile.get("name"):
        lines.append(f"Name: {profile['name']}")
    attendance = data.get("attendance", {})
    if attendance:
        latest_sem = max(attendance.keys(), key=int)
        lines.append(f"Attendance (Semester {latest_sem}):")
        for course in attendance[latest_sem]:
            name = course.get("name") or course.get("subject_name") or "Unknown"
            pct  = course.get("attendance_percentage") or course.get("percentage") or "N/A"
            lines.append(f"  {name}: {pct}%")  # ← now inside the loop
    return "\n".join(lines)