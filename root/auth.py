import uuid
from datetime import datetime, timedelta
active_sessions={}
def create_session(username,password,role):
    token= str(uuid.uuid4())
    active_sessions[token]={
        "username": username,
        "password":password,
        "role":role,
        "expires_at":datetime.now()+ timedelta(hours=2)
        }
    return token
def get_session(token):
    session=active_sessions.get(token)
    if not session:
        return None
    if datetime.now() > session["expires_at"]:
        del active_sessions[token]
        return None
    return session
def delete_session(token):
    active_sessions.pop(token,None)