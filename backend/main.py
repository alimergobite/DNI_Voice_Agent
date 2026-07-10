from dotenv import load_dotenv
load_dotenv()  # Load .env before anything else

from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from .database import get_db, CallLog
from .config import settings
from .twilio_bridge import router as twilio_router
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

# Include Twilio routes
app.include_router(twilio_router)

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
    token.with_grants(api.VideoGrants(room_join=True, room=room_name))
    return {"token": token.to_jwt()}

from pydantic import BaseModel
from fastapi import BackgroundTasks
import time, json

class CallLogPayload(BaseModel):
    customer_name: str
    policy_type: str
    transcript: str
    metadata: dict = {}
    duration: int = 0
    recording_url: str | None = None

def _process_call_log_background(payload: CallLogPayload):
    from google import genai
    import asyncio
    print("[Call Logging API] Generating call summary in background...")
    client = genai.Client(api_key=settings.GEMINI_API_KEY)
    prompt = (
        "You are an insurance call analyst. Read the following transcript and extract structured data.\n"
        "Respond ONLY with valid JSON matching this exact structure:\n"
        "{\n"
        '  "customer_intent": "short string describing the call purpose",\n'
        '  "sentiment": "Positive, Negative, or Neutral",\n'
        '  "rating": "number 1-10 or null if not mentioned",\n'
        '  "kyc_verified": "true or false",\n'
        '  "status": "Must be exactly one of: \'Completed\', \'Abandoned\', \'Not Answered\', \'Wrong Person\', or \'Callback Requested\'. If someone else answers and says the person is not there, output \'Wrong Person\'. If they ask to call back later, output \'Callback Requested\'. If the customer hung up mid-conversation, output \'Abandoned\'. If they never spoke, output \'Not Answered\'. If the call finished its logical flow, output \'Completed\'.",\n'
        '  "summary": "short 2-sentence summary"\n'
        "}\n\n"
        f"Transcript:\n{payload.transcript}"
    )

    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash", 
            contents=prompt + "\n\nCRITICAL: Return ONLY raw JSON without any markdown code blocks (e.g. no ```json)."
        )
        result = response.text
    except Exception as api_err:
        print(f"[Call Logging API Error] Gemini API failed: {api_err}")
        result = "{}"

    extracted = {}
    try:
        clean_result = result.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
        extracted = json.loads(clean_result)
    except Exception as e:
        print(f"[Call Logging API Warning] Failed to parse Gemini JSON output: {e}")

    # Save to SQLite DB
    db = next(get_db())
    
    # Fetch Twilio recording if available
    final_recording_url = payload.recording_url
    if not final_recording_url and payload.metadata.get("call_sid"):
        try:
            from twilio.rest import Client
            import os
            client = Client(os.getenv("TWILIO_ACCOUNT_SID"), os.getenv("TWILIO_AUTH_TOKEN"))
            # Fetch recordings for this call
            recordings = client.recordings.list(call_sid=payload.metadata.get("call_sid"), limit=1)
            if recordings:
                # Construct the MP3 media URL (uri ends in .json by default)
                final_recording_url = f"https://api.twilio.com{recordings[0].uri}".replace(".json", ".mp3")
                print(f"[Call Logging API] Retrieved Twilio recording URL: {final_recording_url}")
        except Exception as e:
            print(f"[Call Logging API Warning] Failed to fetch Twilio recording: {e}")

    try:
        db_log = CallLog(
            call_id=f"temp-{int(time.time())}",
            customer_name=payload.customer_name,
            phone_number=payload.metadata.get("phone", "+971 00 000 0000"),
            policy_type=payload.policy_type,
            date_of_birth=payload.metadata.get("date_of_birth"),
            emirates_id=payload.metadata.get("emirates_id"),
            company_name=payload.metadata.get("company_name"),
            trade_licence=payload.metadata.get("trade_licence"),
            duration_seconds=payload.duration,
            rating=float(extracted.get("rating")) if str(extracted.get("rating")).replace('.','',1).isdigit() else None,
            status=extracted.get("status", "Completed"),
            transcript=payload.transcript,
            recording_url=final_recording_url
        )
        db.add(db_log)
        db.commit()
        db.refresh(db_log)
        
        # Update to sequential call ID
        db_log.call_id = f"#CAL-{db_log.id:03d}"
        db.commit()
        
        print(f"[Call Logging API] Saved to SQLite database as {db_log.call_id}")
    except Exception as db_e:
        print(f"[Database Error] {db_e}")
    finally:
        db.close()

@app.post("/api/process_log")
def process_log(payload: CallLogPayload, background_tasks: BackgroundTasks):
    """Receives transcript from LiveKit agent instantly upon disconnect and processes it in the background"""
    background_tasks.add_task(_process_call_log_background, payload)
    return {"status": "processing"}
