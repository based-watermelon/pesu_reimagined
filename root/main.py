from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from auth import create_session, get_session, delete_session
from data_fetcher import fetch_student_data, fetch_faculty_data, fetch_guest_data
from security import filter_data_for_role, build_ai_context
from ai_handler import ask_ai
from rag import load_knowledge

app = FastAPI(title="PESU Reimagined API")

data_cache       = {}
guest_data_cache = {}


@app.on_event("startup")
async def startup():
    load_knowledge()


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class LoginRequest(BaseModel):
    username: str
    password: str

class ChatRequest(BaseModel):
    message: str
    token:   str

class GuestChatRequest(BaseModel):
    message: str

class LogoutRequest(BaseModel):
    token: str


# error message cleaner 
def _clean_error(raw: str) -> str:
    r = raw.lower()
    if "invalid credentials" in r or "incorrect" in r or "wrong password" in r or "authentication" in r:
        return "Incorrect username or password. Please check your PESU portal credentials."
    if "failed to fetch semester" in r or "semester data" in r or "endpoint" in r:
        return "Could not connect to the PESU portal. Please check your credentials and try again."
    if "timeout" in r or "timed out" in r:
        return "The PESU portal is taking too long to respond. Please try again in a moment."
    if "network" in r or "connection" in r or "connect" in r:
        return "Network error reaching the PESU portal. Check your internet connection."
    if "login failed" in r or "fetch failed" in r:
        return "Login failed. Please verify your username and password are correct."
    if "not found" in r or "404" in r:
        return "Account not found. Double-check your SRN or username."
    for prefix in [
        "pesu fetch failed: ", "faculty pesu fetch failed: ",
        "pesu login failed: ", "faculty login failed: ",
    ]:
        if r.startswith(prefix):
            return _clean_error(raw[len(prefix):])
    return "Login failed. Please check your credentials and try again."


# Health 
@app.get("/api/health")
def health():
    return {"message": "PESU Reimagined is running!", "modes": ["student", "faculty", "guest"]}


# Root redirect -> login page 
@app.get("/")
def root():
    return RedirectResponse(url="/login.html")


@app.get("/api/debug-data")
async def debug_data(token: str = Query(...)):
    session = get_session(token)
    if not session:
        raise HTTPException(401, detail="Session expired.")
    raw = data_cache.get(token)
    if not raw:
        raise HTTPException(404, detail="No cached data. Log in first.")
    import json
    # Showing just the first course and first timetable slot so field names are clear
    att = raw.get("attendance", {})
    sem_keys = sorted([k for k in att.keys() if str(k).isdigit()], key=int)
    first_course = att.get(sem_keys[-1], [{}])[0] if sem_keys else {}
    tt = raw.get("timetable", {})
    schedule = tt.get("schedule", tt) if tt else {}
    first_day = next(iter(schedule.values()), []) if schedule else []
    first_slot = first_day[0] if first_day else {}
    return {
        "attendance_first_course_fields": list(first_course.keys()),
        "attendance_first_course_values": first_course,
        "timetable_first_slot_fields":    list(first_slot.keys()),
        "timetable_first_slot_values":    first_slot,
        "profile_fields":                 list(raw.get("profile", {}).keys()),
    }


# returns cached data for the session (dashboard refresh) 
@app.get("/me")
async def me(token: str = Query(...)):
    session = get_session(token)
    if not session:
        raise HTTPException(401, detail="Session expired. Please log in again.")
    raw = data_cache.get(token)
    if not raw:
        try:
            if session["role"] == "faculty":
                raw = await fetch_faculty_data(session["username"], session["password"])
            else:
                raw = await fetch_student_data(session["username"], session["password"])
            data_cache[token] = raw
        except Exception as e:
            raise HTTPException(500, detail=_clean_error(str(e)))
    return {"data": raw, "role": session["role"], "username": session["username"]}


# Student login 
@app.post("/login")
async def login(body: LoginRequest):
    if not body.username or not body.password:
        raise HTTPException(400, detail="Please enter your username and password.")
    try:
        raw_data = await fetch_student_data(body.username, body.password)
    except Exception as e:
        raise HTTPException(401, detail=_clean_error(str(e)))
    token = create_session(body.username, body.password, "student")
    data_cache[token] = raw_data
    return {"token": token, "role": "student", "username": body.username, "data": raw_data}


# Faculty login 
@app.post("/faculty-login")
async def faculty_login(body: LoginRequest):
    if not body.username or not body.password:
        raise HTTPException(400, detail="Please enter your faculty ID and password.")
    try:
        raw_data = await fetch_faculty_data(body.username, body.password)
    except Exception as e:
        raise HTTPException(401, detail=_clean_error(str(e)))
    token = create_session(body.username, body.password, "faculty")
    data_cache[token] = raw_data
    return {"token": token, "role": "faculty", "username": body.username, "data": raw_data}


# Parent login 
@app.post("/parent-login")
async def parent_login(body: LoginRequest):
    """Parent logs in with the ward's SRN and password."""
    if not body.username or not body.password:
        raise HTTPException(400, detail="Please enter the ward's SRN and password.")
    try:
        raw_data = await fetch_student_data(body.username, body.password)
    except Exception as e:
        raise HTTPException(401, detail=_clean_error(str(e)))
    token = create_session(body.username, body.password, "parent")
    data_cache[token] = raw_data
    return {"token": token, "role": "parent", "username": body.username, "data": raw_data}


# Guest chat
@app.post("/guest-chat")
async def guest_chat(body: GuestChatRequest):
    global guest_data_cache
    if not guest_data_cache:
        guest_data_cache = await fetch_guest_data()
    filtered = filter_data_for_role(guest_data_cache, "guest")
    prompt   = build_ai_context(filtered, body.message)
    reply    = ask_ai(prompt)
    return {"reply": reply, "role": "guest"}


# Authenticated chat 
@app.post("/chat")
async def chat(body: ChatRequest):
    session = get_session(body.token)
    if not session:
        raise HTTPException(401, detail="Session expired. Please log in again.")

    raw_data = data_cache.get(body.token)
    if not raw_data:
        try:
            if session["role"] == "faculty":
                raw_data = await fetch_faculty_data(session["username"], session["password"])
            else:
                raw_data = await fetch_student_data(session["username"], session["password"])
            data_cache[body.token] = raw_data
        except Exception as e:
            raise HTTPException(500, detail=_clean_error(str(e)))

    filtered = filter_data_for_role(raw_data, session["role"])
    prompt   = build_ai_context(filtered, body.message)
    reply    = ask_ai(prompt)
    return {"reply": reply, "role": session["role"]}


#logout 
@app.post("/logout")
async def logout(body: LogoutRequest):
    delete_session(body.token)
    data_cache.pop(body.token, None)
    return {"message": "Logged out successfully"}


# Static files
app.mount("/", StaticFiles(directory="frontend", html=True), name="static")