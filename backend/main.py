from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from .database import get_db, CallLog
from .config import settings
from livekit import api
import os

app = FastAPI(title=settings.APP_NAME)

# Allow React Frontend to communicate
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Ensure recordings directory exists and mount it
os.makedirs("recordings", exist_ok=True)
app.mount("/recordings", StaticFiles(directory="recordings"), name="recordings")

@app.get("/")
def read_root():
    return {"message": "DNI Voice Agent API is running"}

@app.get("/calls")
def get_calls(db: Session = Depends(get_db)):
    """Fetch all call logs for the dashboard"""
    return db.query(CallLog).order_by(CallLog.start_time.desc()).all()

@app.post("/token")
async def get_token(room_name: str, participant_name: str):
    """Generate a LiveKit token for the frontend"""
    token = api.AccessToken(settings.LIVEKIT_API_KEY, settings.LIVEKIT_API_SECRET)
    token.with_identity(participant_name).with_name(participant_name)
    token.with_grants(api.VideoGrants(roomJoin=True, room=room_name))
    return {"token": token.to_jwt()}
