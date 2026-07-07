import asyncio
import json
import os
import time
from dotenv import load_dotenv
load_dotenv(override=True)

from google import genai
from livekit.agents import AutoSubscribe, JobContext, JobRequest, WorkerOptions, cli
from livekit.agents.voice import AgentSession, Agent
from livekit.api import LiveKitAPI
from livekit.plugins import silero

# Initialize VAD globally so it doesn't block the async event loop during job dispatch.
# We use an activation_threshold of 0.6 to completely ignore Twilio static noise.
# Since the prompt now asks for their full name, their natural speech will easily trigger this threshold.
custom_vad = silero.VAD.load(min_speech_duration=0.05, min_silence_duration=0.25, activation_threshold=0.6)

from backend.services.llm_service import get_llm_engine
from backend.services.stt_service import get_stt_engine
from backend.services.tts_service import get_tts_engine
from backend.services.prompts import get_outbound_prompt
from backend.config import settings
from backend.database import SessionLocal, CallLog


# ---------------------------------------------------------------------------
# Call Logging & Post-Call Analysis
# ---------------------------------------------------------------------------
async def process_call_log(session: AgentSession, customer_name: str, policy_type: str):
    """Runs after the call ends. Extracts structured data from the transcript via Gemini."""
    try:
        # Fetch metadata saved during entrypoint
        metadata = globals().get("_last_metadata", {})
        messages = session.history.messages()
        if not messages:
            return

        transcript = ""
        for msg in messages:
            if msg.role in ["user", "assistant"]:
                text_content = msg.content
                if isinstance(text_content, list):
                    text_content = " ".join([p for p in text_content if isinstance(p, str)])
                transcript += f"{msg.role.upper()}: {text_content}\n"

        if not transcript.strip():
            return

        print("[Call Logging] Generating call summary...")
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
            f"Transcript:\n{transcript}"
        )

        def _call():
            response = client.models.generate_content(
                model="gemini-2.5-flash", 
                contents=prompt + "\n\nCRITICAL: Return ONLY raw JSON without any markdown code blocks (e.g. no ```json)."
            )
            return response.text

        result = await asyncio.to_thread(_call)
        # Parse JSON
        extracted = {}
        try:
            clean_result = result.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
            extracted = json.loads(clean_result)
        except Exception as e:
            print(f"[Call Logging Warning] Failed to parse Gemini JSON output: {e}\nRaw output: {result}")

        log_data = {
            "timestamp": int(time.time()),
            "customer_name": customer_name,
            "policy_type": policy_type,
            "transcript": transcript,
            "extracted_data": extracted,
        }

        # Try to fetch Twilio Recording URL
        recording_url = getattr(session, 'recording_url', None)
        call_sid = _last_metadata.get("call_sid") if '_last_metadata' in globals() else None
        
        if call_sid and settings.TWILIO_ACCOUNT_SID and settings.TWILIO_AUTH_TOKEN:
            try:
                from twilio.rest import Client
                twilio_client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
                recordings = twilio_client.recordings.list(call_sid=call_sid, limit=1)
                if recordings:
                    rec = recordings[0]
                    recording_url = f"https://api.twilio.com/2010-04-01/Accounts/{settings.TWILIO_ACCOUNT_SID}/Recordings/{rec.sid}.mp3"
                    print(f"[Call Logging] Found Twilio recording: {recording_url}")
            except Exception as e:
                print(f"[Call Logging] Failed to fetch Twilio recording: {e}")

        # Save to SQLite DB
        db = SessionLocal()
        try:
            db_log = CallLog(
                call_id=f"temp-{log_data['timestamp']}",
                customer_name=customer_name,
                phone_number=_last_metadata.get("phone", "+971 00 000 0000") if '_last_metadata' in globals() else "+971 00 000 0000",
                policy_type=policy_type,
                date_of_birth=_last_metadata.get("date_of_birth") if '_last_metadata' in globals() else None,
                emirates_id=_last_metadata.get("emirates_id") if '_last_metadata' in globals() else None,
                company_name=_last_metadata.get("company_name") if '_last_metadata' in globals() else None,
                trade_licence=_last_metadata.get("trade_licence") if '_last_metadata' in globals() else None,
                duration_seconds=int(time.time() - getattr(session, 'start_time', time.time() - 120)),
                rating=float(extracted.get("rating")) if str(extracted.get("rating")).replace('.','',1).isdigit() else None,
                status=extracted.get("status", "Completed"),
                transcript=transcript,
                recording_url=recording_url
            )
            db.add(db_log)
            db.commit()
            db.refresh(db_log)
            
            # Update to sequential call ID
            db_log.call_id = f"#CAL-{db_log.id:03d}"
            db.commit()
            
            print(f"[Call Logging] Saved to SQLite database as {db_log.call_id}")
        except Exception as db_e:
            print(f"[Database Error] {db_e}")
        finally:
            db.close()
            
    except Exception as e:
        print(f"[Call Logging Error] {e}")


# ---------------------------------------------------------------------------
# LiveKit Agent Entrypoint
# ---------------------------------------------------------------------------
async def entrypoint(ctx: JobContext):
    # Read customer metadata from the dispatch request (set in twilio_bridge.py /api/dial)
    metadata = {}
    if ctx.job.metadata:
        try:
            metadata = json.loads(ctx.job.metadata)
        except Exception:
            pass

    customer_name = metadata.get("customer_name", "Valued Customer")
    policy_type = metadata.get("policy_type", "individual")
    tts_provider = metadata.get("tts_provider", "elevenlabs")

    instructions = get_outbound_prompt(customer_name, policy_type, metadata)
    greeting_text = f"Hi, this is Aisha from Dubai National Insurance. Am I speaking with {customer_name}?"

    # Build the session
    session = AgentSession(
        stt=get_stt_engine(),
        vad=custom_vad,
        llm=get_llm_engine(),
        tts=get_tts_engine(tts_provider),
        min_endpointing_delay=0.1,
        max_endpointing_delay=0.5,
    )

    # Store start time and metadata for call logging
    session.start_time = time.time()
    global _last_metadata
    _last_metadata = metadata

    # Connect and subscribe ONLY to audio tracks
    await ctx.connect(auto_subscribe=AutoSubscribe.AUDIO_ONLY)

    from livekit.agents.voice.room_io import RoomInputOptions
    room_input_options = RoomInputOptions(participant_identity=f"phone_{ctx.room.name}")

    # Start the agent session against the room, locked to the phone participant
    await session.start(
        room=ctx.room, 
        agent=Agent(instructions=instructions),
        room_input_options=room_input_options
    )

    @ctx.room.on("participant_disconnected")
    def on_participant_disconnected(participant):
        if participant.identity.startswith("phone_"):
            asyncio.create_task(ctx.room.disconnect())

    ctx.room.on(
        "disconnected",
        lambda *args: asyncio.create_task(process_call_log(session, customer_name, policy_type)),
    )

    # Wait specifically for the Twilio Bridge participant (phone_) to join before greeting
    phone_participant = None
    while not phone_participant:
        # Check existing participants
        for p in ctx.room.remote_participants.values():
            if p.identity.startswith("phone_"):
                phone_participant = p
                break
        if not phone_participant:
            await asyncio.sleep(0.1)

    try:
        # Small pause so WebRTC audio path is fully established
        await asyncio.sleep(1.5)
        await session.say(greeting_text, allow_interruptions=False)
    except Exception as e:
        print(f"[Agent Error] {e}")
        raise e


async def request_fnc(req: JobRequest) -> None:
    # Only accept explicitly dispatched jobs (those with metadata set by the bridge).
    # This prevents LiveKit from auto-dispatching a second agent into the same room.
    if req.job.metadata:
        await req.accept()
    else:
        await req.reject()


if __name__ == "__main__":
    cli.run_app(
        WorkerOptions(
            agent_name="outbound_agent",
            entrypoint_fnc=entrypoint,
            request_fnc=request_fnc,
            port=8082,
        )
    )
