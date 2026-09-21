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
        # 0.15s was committing the turn before Sarvam finished transcribing,
        # which fragmented replies mid-sentence and logged
        # "transcript arrives after turn has been committed".
        min_endpointing_delay=0.5,
        llm=get_llm_engine(),
        tts=get_tts_engine(tts_provider),
        preemptive_generation=True,
    )

    # Store start time and metadata for call logging
    session.start_time = time.time()
    global _last_metadata
    _last_metadata = metadata

    # Fillers spoken during the call, as (user_text_that_triggered_it, filler).
    # Kept out of session.history so the LLM never sees them; merged back into
    # the saved transcript below so the log matches what the caller heard.
    _spoken_fillers = []

    def _merge_fillers_into_transcript(transcript: str) -> str:
        """Insert each filler after the USER line that triggered it."""
        if not _spoken_fillers:
            return transcript

        pending = list(_spoken_fillers)
        out = []
        for line in transcript.split("\n"):
            out.append(line)
            if not line.startswith("USER:"):
                continue
            said = line[len("USER:"):].strip()
            for i, (trigger, filler) in enumerate(pending):
                # STT may split one utterance across several finals, so the
                # saved USER line can be longer than the fragment that fired
                # the filler; match on containment either way.
                if trigger and (trigger in said or said in trigger):
                    out.append(f"ASSISTANT: {filler}")
                    pending.pop(i)
                    break

        # Anything unmatched (e.g. the user line was dropped from history)
        # still belongs in the record rather than being silently lost.
        for _, filler in pending:
            out.append(f"ASSISTANT: {filler}")
        return "\n".join(out)

    # Helper to save transcript log reliably in ALL call teardown scenarios
    _log_saved = False
    def save_transcript_to_db():
        nonlocal _log_saved
        if _log_saved:
            return
        _log_saved = True
        
        transcript = ""
        try:
            messages = session.history.messages()
            for msg in messages:
                if msg.role in ["user", "assistant"]:
                    text_content = msg.content
                    if isinstance(text_content, list):
                        text_content = " ".join([p for p in text_content if isinstance(p, str)])
                    transcript += f"{msg.role.upper()}: {text_content}\n"
        except Exception:
            pass

        # Fillers are spoken with add_to_chat_ctx=False so they never enter the
        # LLM's context, but the caller did hear them, so splice them back in
        # here to keep the saved transcript a faithful record of the call.
        try:
            transcript = _merge_fillers_into_transcript(transcript)
        except Exception as e:
            print(f"[FILLER MERGE ERROR] {e}")

        if transcript.strip():
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

    # ── LATENCY MASKING: speak a short acknowledgement while the LLM thinks ──
    # The LLM needs ~3-5s to produce its first token with the full KYC prompt.
    # Without this the caller hears dead air, assumes the line dropped, and says
    # "hello?" — which barges in exactly as the agent finally starts speaking.
    # Saying a filler immediately keeps the line alive while the LLM generates.
    # Deliberately neutral: the scripted reply that follows carries the real
    # acknowledgement ("Got it, thank you."), so a filler that also acknowledges
    # would make Aisha say it twice.
    #
    # Stage-aware, because the script's next line differs by step. "One moment"
    # implies looking something up: right before a KYC check, wrong before
    # "That's great to hear!" (rating) or "No problem at all!" (review ask) —
    # and actively jarring before "I'm really sorry to hear that."
    VERIFY_FILLERS = [            # while a DOB / ID / licence check happens
        "Ok, one moment.",
        "Ok, just a second.",
        "Right, one moment.",
    ]
    NEUTRAL_FILLERS = [           # rating, review ask, open feedback
        "Ok.",
        "Mm-hmm.",
        "Right.",
    ]
    _filler_idx = {"verify": 0, "neutral": 0}
    # Turn 1 is the reply to the greeting; turns 2-3 are the KYC answers
    # (DOB then Emirates ID / trade licence); everything after is conversational.
    VERIFY_TURNS = (2, 3)
    _filler_state = {"turn": 0, "spoken_for_turn": -1, "fragments": []}

    # Sarvam marks mid-sentence fragments as is_final, so one spoken date of
    # birth can arrive as "X" / "book pay" / "2002". Firing on the first final
    # plays the filler over the caller's own voice - it is spoken, logged, and
    # inaudible. Wait this long for a follow-up final before deciding the turn
    # really ended.
    FILLER_DEBOUNCE = 0.6
    _filler_task = {"t": None}

    def _speak_filler(turn: int, trigger: str = ""):
        """Fire-and-forget a filler. Never let a filler failure break the call."""
        try:
            kind = "verify" if turn in VERIFY_TURNS else "neutral"
            pool = VERIFY_FILLERS if kind == "verify" else NEUTRAL_FILLERS
            text = pool[_filler_idx[kind] % len(pool)]
            _filler_idx[kind] += 1
            _spoken_fillers.append((trigger, text))
            print(f"[FILLER] {text}")
            # allow_interruptions=True so the caller can talk over the filler;
            # it is only a placeholder, never information they need to hear.
            session.say(text, allow_interruptions=True, add_to_chat_ctx=False)
        except Exception as e:
            print(f"[FILLER ERROR] {e}")

    # ── DIAGNOSTIC LOGGING: See exactly what Deepgram transcribes and what the LLM replies ──
    @session.on("user_input_transcribed")
    def _on_transcript(ev):
        print(f"[STT HEARD] \"{ev.transcript}\" (is_final={ev.is_final})")

        if not ev.is_final:
            return

        # A later fragment of the same utterance cancels the pending filler, so
        # only the last final in a burst speaks — and only once the caller has
        # actually stopped. Fragments accumulate into one utterance rather than
        # counting as separate turns, since "X" / "book pay" / "2002" is one
        # spoken date of birth, not three answers.
        pending = _filler_task["t"]
        if pending and not pending.done():
            pending.cancel()
            _filler_state["fragments"].append(ev.transcript)
        else:
            _filler_state["fragments"] = [ev.transcript]
            _filler_state["turn"] += 1

        # Turn 1 is the reply to the greeting, which is not a reply to anything
        # the agent asked, so acknowledging it makes no sense.
        if _filler_state["turn"] <= 1:
            return

        turn_at_schedule = _filler_state["turn"]
        utterance = " ".join(_filler_state["fragments"]).strip()

        async def _fire_after_debounce():
            try:
                await asyncio.sleep(FILLER_DEBOUNCE)
            except asyncio.CancelledError:
                return
            # Single-word replies ("yes", "no") are answered fast enough that a
            # filler would add delay rather than hide it. Checked after the
            # debounce, on the combined utterance.
            if len(utterance.split()) < 2:
                return
            if _filler_state["spoken_for_turn"] == turn_at_schedule:
                return
            _filler_state["spoken_for_turn"] = turn_at_schedule
            _speak_filler(turn_at_schedule, utterance)

        _filler_task["t"] = asyncio.create_task(_fire_after_debounce())

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
                            save_transcript_to_db()
                            try:
                                metadata = globals().get("_last_metadata", {})
                                call_sid = metadata.get("call_sid", "")
                                import urllib.request
                                url5 = f"http://localhost:5000/api/kill_room/{ctx.room.name}?call_sid={call_sid}"
                                url8 = f"http://localhost:8000/api/kill_room/{ctx.room.name}?call_sid={call_sid}"
                                try:
                                    urllib.request.urlopen(url5, timeout=5)
                                except Exception:
                                    try: urllib.request.urlopen(url8, timeout=5)
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
            save_transcript_to_db()

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
        lambda *args: (save_transcript_to_db(), print("[Agent] Room disconnected."))
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
