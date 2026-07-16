import asyncio
import json
import os
import sys
import time

# Ensure project root is in python path to prevent ModuleNotFoundError when run by PM2
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from dotenv import load_dotenv
load_dotenv(override=True)

from google import genai
from livekit.agents import AutoSubscribe, JobContext, JobRequest, WorkerOptions, cli
from livekit.agents.voice import AgentSession, Agent
from livekit.api import LiveKitAPI
from livekit.plugins import silero

custom_vad = silero.VAD.load(min_speech_duration=0.05, min_silence_duration=0.25, activation_threshold=0.7)


from backend.services.llm_service import get_llm_engine
from backend.services.stt_service import get_stt_engine
from backend.services.tts_service import get_tts_engine
from backend.services.prompts import get_outbound_prompt
from backend.config import settings
from backend.database import SessionLocal, CallLog


# Call logging logic has been moved to the FastAPI backend (main.py) to decouple it from the LiveKit agent lifecycle.


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
        min_endpointing_delay=0.3,
        llm=get_llm_engine(),
        tts=get_tts_engine(tts_provider),
        preemptive_generation=False,
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
            print("[Agent] Phone disconnected. Initiating fast teardown.")
            
            # Extract transcript
            transcript = ""
            try:
                messages = session.history.messages()
                for msg in messages:
                    if msg.role in ["user", "assistant"]:
                        text_content = msg.content
                        if isinstance(text_content, list):
                            text_content = " ".join([p for p in text_content if isinstance(p, str)])
                        transcript += f"{msg.role.upper()}: {text_content}\n"
            except:
                pass

            if transcript.strip():
                # Send to FastAPI backend
                import requests
                metadata = globals().get("_last_metadata", {})
                duration = int(time.time() - getattr(session, 'start_time', time.time() - 120))
                payload = {
                    "customer_name": customer_name,
                    "policy_type": policy_type,
                    "transcript": transcript,
                    "metadata": metadata,
                    "duration": duration,
                    "recording_url": getattr(session, 'recording_url', None)
                }
                try:
                    # Use a short timeout. We just need to hand off the payload to the backend.
                    # The backend will process the Gemini summary asynchronously.
                    requests.post("http://127.0.0.1:5000/api/process_log", json=payload, timeout=2)
                except Exception as e:
                    print(f"[Agent] Failed to hand off log to backend: {e}")

            asyncio.create_task(ctx.room.disconnect())

    ctx.room.on(
        "disconnected",
        lambda *args: print("[Agent] Room disconnected.")
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
