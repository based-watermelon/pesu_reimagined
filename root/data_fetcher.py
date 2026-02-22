from pesuacademy import PESUAcademy
import asyncio


async def fetch_student_data(username: str, password: str) -> dict:
    pesu = None
    try:
        pesu = await PESUAcademy.login(username=username, password=password)
        attendance_data, timetable_data, profile_data = await asyncio.gather(
            pesu.get_attendance(),
            pesu.get_timetable(),
            pesu.get_profile(),
        )
        return {
            "username":   username,
            "attendance": _serialize_attendance(attendance_data),
            "timetable":  _serialize_timetable(timetable_data),
            "profile":    _serialize_profile(profile_data),
        }
    except Exception as e:
        raise Exception(f"PESU fetch failed: {e}")
    finally:
        if pesu:
            await pesu.close()


async def fetch_faculty_data(username: str, password: str) -> dict:
    pesu = None
    try:
        pesu = await PESUAcademy.login(username=username, password=password)
        attendance_data, timetable_data, profile_data = await asyncio.gather(
            pesu.get_attendance(),
            pesu.get_timetable(),
            pesu.get_profile(),
        )
        profile = _serialize_profile(profile_data)

        # Try to fetch class section info
        section_info = {}
        public_pesu = None
        try:
            section = (
                profile.get("section") or profile.get("class_section") or
                profile.get("branch_section") or profile.get("section_id") or ""
            )
            if section:
                public_pesu = PESUAcademy()
                raw_section = await public_pesu.get_section_info(section=section)
                section_info = raw_section.model_dump(mode="json") if raw_section else {}
            else:
                section_info = {
                    "note": "Section field not found.",
                    "available_profile_keys": list(profile.keys()),
                }
        except Exception as se:
            section_info = {"note": f"Section info unavailable: {se}"}
        finally:
            if public_pesu:
                try:
                    await public_pesu.close()
                except Exception:
                    pass

        return {
            "username":     username,
            "role":         "faculty",
            "profile":      profile,
            "attendance":   _serialize_attendance(attendance_data),
            "timetable":    _serialize_timetable(timetable_data),
            "section_info": section_info,
        }
    except Exception as e:
        raise Exception(f"Faculty PESU fetch failed: {e}")
    finally:
        if pesu:
            await pesu.close()


async def fetch_guest_data() -> dict:
    return {
        "role": "guest",
        "public_pesu_info": {
            "institution": "PES University",
            "campuses": ["RR Campus (Ring Road, Bengaluru)", "EC Campus (Electronic City, Bengaluru)"],
            "attendance_rules": {
                "minimum_required": "75% — below this students are debarred from exams",
                "recommended": "85% — safe zone with buffer for emergencies",
                "condonation": "Medical certificates may allow up to 10% condonation",
            },
            "academic_structure": {
                "semesters_per_year": 2,
                "grading": "10-point CGPA scale",
                "assessments": "2 CIAs per semester plus End Semester Exam",
            },
            "scholarship_criteria": {
                "merit_scholarship": "CGPA 9.0+ — partial or full tuition fee waiver",
                "honours_degree": "8.5 CGPA required throughout the programme",
            },
            "contact": {"admissions": "admissions@pes.edu", "website": "https://pes.edu"},
        },
    }


def _serialize_attendance(data: dict) -> dict:
    result = {}
    for semester, courses in data.items():
        result[str(semester)] = [course.model_dump(mode="json") for course in courses]
    return result

def _serialize_timetable(timetable) -> dict:
    return timetable.model_dump(mode="json") if timetable else {}

def _serialize_profile(profile) -> dict:
    return profile.model_dump(mode="json") if profile else {}