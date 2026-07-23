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
from livekit import api as livekit_api
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
        min_endpointing_delay=0.15,
        llm=get_llm_engine(),
        tts=get_tts_engine(tts_provider),
        preemptive_generation=True,
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

    # ── DIAGNOSTIC LOGGING: See exactly what Deepgram transcribes and what the LLM replies ──
    @session.on("user_input_transcribed")
    def _on_transcript(ev):
        print(f"[STT HEARD] \"{ev.transcript}\" (is_final={ev.is_final})")

    @session.on("agent_speech_started")
    def _on_agent_speech(ev):
        try:
            # Try to grab the text the agent is about to say
            print(f"[LLM REPLY] Agent is speaking...")
        except Exception:
            pass

    @session.on("conversation_item_added")
    def _on_conversation_item(ev):
        try:
            item = ev.item
            if hasattr(item, 'role') and hasattr(item, 'content'):
                content = item.content
                if isinstance(content, list):
                    content = " ".join([str(p) for p in content if p])
                print(f"[CONVERSATION] {item.role}: {content}")
                
                # Auto-hangup logic based on AI final message
                role_str = getattr(item.role, "value", str(item.role)).lower()
                if "assistant" in role_str:
                    text_lower = content.lower()
                    if "wonderful day" in text_lower or "thank you for your time" in text_lower or "security reasons i cannot proceed" in text_lower:
                        print("[Agent] Detected hardcoded goodbye phrase! Hanging up in 4s.")
                        
                        async def delayed_kill():
                            await asyncio.sleep(4)
                            try:
                                metadata = globals().get("_last_metadata", {})
                                call_sid = metadata.get("call_sid", "")
                                import urllib.request
                                url8 = f"http://localhost:8000/api/kill_room/{ctx.room.name}?call_sid={call_sid}"
                                url5 = f"http://localhost:5000/api/kill_room/{ctx.room.name}?call_sid={call_sid}"
                                try:
                                    urllib.request.urlopen(url8, timeout=5)
                                except Exception:
                                    try: urllib.request.urlopen(url5, timeout=5)
                                    except Exception: pass
                                await ctx.room.disconnect()
                            except Exception as e:
                                print(f"[Agent Error] Failed to delegate room kill: {e}")
                        asyncio.create_task(delayed_kill())

        except Exception as ex:
            print(f"[CONVERSATION LOG ERROR] {ex}")

    @ctx.room.on("participant_disconnected")
    def on_participant_disconnected(participant):
        # If either the phone hangs up, OR the dashboard operator clicks "End Call"
        identity_lower = participant.identity.lower()
        if identity_lower.startswith("phone_") or "operator" in identity_lower or "spectator" in identity_lower:
            print(f"[Agent] {participant.identity} disconnected. Initiating fast teardown.")
            
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
                import urllib.request, json
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
                    data = json.dumps(payload).encode()
                    req5 = urllib.request.Request("http://localhost:5000/api/process_log", data=data, headers={'Content-Type': 'application/json'})
                    req8 = urllib.request.Request("http://localhost:8000/api/process_log", data=data, headers={'Content-Type': 'application/json'})
                    try:
                        urllib.request.urlopen(req5, timeout=3)
                    except Exception:
                        try:
                            urllib.request.urlopen(req8, timeout=3)
                        except Exception:
                            pass
                except Exception as e:
                    print(f"[Agent] Failed to hand off log to backend: {e}")

            # Completely kill the room to forcefully drop the Twilio call and frontend modal
            async def run_kill_room():
                try:
                    metadata = globals().get("_last_metadata", {})
                    call_sid = metadata.get("call_sid", "")
                    import urllib.request
                    url5 = f"http://localhost:5000/api/kill_room/{ctx.room.name}?call_sid={call_sid}"
                    url8 = f"http://localhost:8000/api/kill_room/{ctx.room.name}?call_sid={call_sid}"
                    def make_req():
                        try: urllib.request.urlopen(url5, timeout=5)
                        except Exception:
                            try: urllib.request.urlopen(url8, timeout=5)
                            except Exception: pass
                    await asyncio.to_thread(make_req)
                except Exception as e:
                    print(f"[Agent Error] Kill room fallback: {e}")
                finally:
                    await ctx.room.disconnect()
            
            # Properly launch the async task
            asyncio.create_task(run_kill_room())

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
