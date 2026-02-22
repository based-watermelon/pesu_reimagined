from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from auth import create_session,get_session
from data_fetcher import fetch_student_data, summarize_for_ai
from security import filter_data_for_role, build_ai_context
from ai_handler import ask_ai

app=FastAPI(title="PESU Reimagined API")

data_cache={}

app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_methods=['*'],
    allow_headers=['*'],
)

class LoginRequest(BaseModel):
    username:str
    password:str

class ChatRequest(BaseModel):
    message:str
    token:str

@app.get("/api/health")
def health():
    return {"message":"PESU Reimagined is running!"}

@app.post("/login")
async def login(body: LoginRequest):
    if not body.username or not body.password:
        raise HTTPException(400, detail="Missing credentials")
    try:
        raw_data = await fetch_student_data(body.username, body.password)
    except Exception as e:
        raise HTTPException(401, detail=f"PESU login failed: {str(e)}")

    token = create_session(body.username, body.password, "student")
    data_cache[token] = raw_data

    return {"token": token, "role": "student", "username": body.username}

@app.post("/chat")
async def chat(body : ChatRequest):
    session= get_session(body.token)
    if not session:
        raise HTTPException(401,detail="Invalid or expired token")
    raw_data = data_cache.get(body.token)
    if not raw_data:
        try:
            raw_data= await fetch_student_data(session["username"], session["password"])
            data_cache[body.token]=raw_data
        except Exception as e:
            raise HTTPException(500, detail=f"Could not fetch PESU data: {str(e)}")
    filtered= filter_data_for_role(raw_data, session["role"])
    prompt= build_ai_context(filtered, body.message)
    reply= ask_ai(prompt)
    return {"reply":reply, "role":session["role"]}

app.mount("/", StaticFiles(directory="frontend", html=True), name="static")





