import asyncio
import json
import os
import time
from dotenv import load_dotenv
load_dotenv(override=True)

from google import genai
from livekit.agents import AutoSubscribe, JobContext, JobRequest, WorkerOptions, cli
from livekit.agents.voice import AgentSession, Agent
from livekit.api import LiveKitAPI, RoomCompositeEgressRequest, EncodedFileOutput
from livekit.plugins import silero

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
            '  "summary": "short 2-sentence summary"\n'
            "}\n\n"
            f"Transcript:\n{transcript}"
        )

        def _call():
            response = client.models.generate_content(model="gemini-2.5-flash", contents=prompt)
            return response.text

        result = await asyncio.to_thread(_call)
        # Parse JSON
        extracted = {}
        try:
            extracted = json.loads(result)
        except:
            print("[Call Logging Warning] Failed to parse Gemini JSON output")

        log_data = {
            "timestamp": int(time.time()),
            "customer_name": customer_name,
            "policy_type": policy_type,
            "transcript": transcript,
            "extracted_data": extracted,
        }

        # Save to SQLite DB
        db = SessionLocal()
        try:
            db_log = CallLog(
                call_id=f"temp-{log_data['timestamp']}",
                customer_name=customer_name,
                phone_number=metadata.get("phone", "+971 00 000 0000") if 'metadata' in locals() else "+971 00 000 0000",
                policy_type=policy_type,
                duration_seconds=int(time.time() - getattr(session, 'start_time', time.time() - 120)),
                rating=float(extracted.get("rating")) if str(extracted.get("rating")).replace('.','',1).isdigit() else None,
                status="Completed",
                transcript=transcript,
                recording_url=getattr(session, 'recording_url', None)
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
    await ctx.connect(auto_subscribe=AutoSubscribe.AUDIO_ONLY)

    # The frontend sets metadata on the participant's token, not the room itself.
    metadata = {}
    for p in ctx.room.remote_participants.values():
        if p.metadata:
            try:
                metadata = json.loads(p.metadata)
                break
            except Exception:
                pass

    customer_name = metadata.get("customer_name", "Valued Customer")
    policy_type = metadata.get("policy_type", "individual")

    instructions = get_outbound_prompt(customer_name, policy_type, metadata)
    greeting_text = f"Hi, this is Aisha from Dubai National Insurance. Am I speaking with {customer_name}?"

    session = AgentSession(
        stt=get_stt_engine(),
        llm=get_llm_engine(),
        tts=get_tts_engine(api_key_override=metadata.get("elevenlabs_api_key")),
        vad=silero.VAD.load(
            activation_threshold=0.5,
            min_speech_duration=0.3,
            min_silence_duration=0.6,
        ),
    )
    
    # Store start time for duration calculation
    session.start_time = time.time()
    
    # We pass metadata down to the logger
    global _last_metadata
    _last_metadata = metadata

    await session.start(room=ctx.room, agent=Agent(instructions=instructions))

    # Trigger LiveKit Egress in the background so it doesn't delay the greeting
    async def start_recording():
        try:
            api = LiveKitAPI(settings.LIVEKIT_URL, settings.LIVEKIT_API_KEY, settings.LIVEKIT_API_SECRET)
            output = EncodedFileOutput(filepath=f"/out/{ctx.room.name}.mp4")
            request = RoomCompositeEgressRequest(
                room_name=ctx.room.name,
                file=output,
                layout="speaker"
            )
            await api.egress.start_room_composite_egress(request)
            session.recording_url = f"http://localhost:8000/recordings/{ctx.room.name}.mp4"
            print(f"[Recording] Started recording: {session.recording_url}")
            await api.aclose()
        except Exception as e:
            print(f"[Recording Error] Failed to start egress: {e}")
            session.recording_url = None

    asyncio.create_task(start_recording())

    ctx.room.on(
        "disconnected",
        lambda *args: asyncio.create_task(process_call_log(session, customer_name, policy_type)),
    )

    try:
        # Give WebRTC a tiny moment to establish the audio connection
        await asyncio.sleep(1.0)
        # Use say() to skip LLM latency and speak instantly
        await session.say(greeting_text, allow_interruptions=False)
    except Exception as e:
        print(f"[Agent Error] {e}")
        raise e


async def request_fnc(req: JobRequest) -> None:
    await req.accept()


if __name__ == "__main__":
    cli.run_app(
        WorkerOptions(
            entrypoint_fnc=entrypoint,
            request_fnc=request_fnc,
            port=8082,
        )
    )
