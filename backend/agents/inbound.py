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
from livekit.agents import AutoSubscribe, JobContext, JobRequest, WorkerOptions, cli, turn_detector
from livekit.agents.voice import AgentSession, Agent
from livekit.plugins import silero

from backend.services.llm_service import get_llm_engine
from backend.services.stt_service import get_stt_engine
from backend.services.tts_service import get_tts_engine
from backend.services.prompts import get_inbound_prompt
from backend.config import settings

INBOUND_GREETING = (
    "Hello! Welcome to Dubai National Insurance. "
    "I'm Aisha, your AI insurance assistant. "
    "Are you looking for a new policy, or are you calling about an existing one?"
)

# ---------------------------------------------------------------------------
# Call Logging & Post-Call Analysis
# ---------------------------------------------------------------------------
async def process_call_log(session: AgentSession):
    """Runs after the call ends. Extracts structured data from the transcript via Gemini."""
    try:
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

        print("[Call Logging] Generating inbound call summary...")
        client = genai.Client(api_key=settings.GEMINI_API_KEY)
        prompt = (
            "You are an insurance call analyst. Read the following inbound call transcript.\n"
            "Respond ONLY with valid JSON:\n"
            "{\n"
            '  "customer_intent": "new_policy or existing_policy or other",\n'
            '  "sentiment": "Positive, Negative, or Neutral",\n'
            '  "summary": "short 2-sentence summary"\n'
            "}\n\n"
            f"Transcript:\n{transcript}"
        )

        def _call():
            response = client.models.generate_content(model="gemini-2.5-flash", contents=prompt)
            return response.text

        result = await asyncio.to_thread(_call)
        if result.startswith("```json"):
            result = result[7:-3].strip()
        elif result.startswith("```"):
            result = result[3:-3].strip()

        log_data = {
            "timestamp": int(time.time()),
            "type": "inbound",
            "transcript": transcript,
            "extracted_data": json.loads(result),
        }

        os.makedirs("Call_Logs", exist_ok=True)
        filename = f"Call_Logs/inbound_{log_data['timestamp']}.json"
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(log_data, f, indent=4)

        print(f"[Call Logging] Saved to {filename}")
    except Exception as e:
        print(f"[Call Logging Error] {e}")


# ---------------------------------------------------------------------------
# LiveKit Agent Entrypoint
# ---------------------------------------------------------------------------
async def entrypoint(ctx: JobContext):
    await ctx.connect(auto_subscribe=AutoSubscribe.AUDIO_ONLY)

    instructions = get_inbound_prompt("Valued Customer", "General Inquiry")

    session = AgentSession(
        stt=get_stt_engine(),
        llm=get_llm_engine(),
        tts=get_tts_engine(),
        vad=silero.VAD.load(
            activation_threshold=0.6,
            min_speech_duration=0.05,
            min_silence_duration=0.1,
        ),
        turn_detector=turn_detector.DefaultTurnDetector(silence_duration=0.4),
    )

    await session.start(room=ctx.room, agent=Agent(instructions=instructions))

    ctx.room.on(
        "disconnected",
        lambda *args: asyncio.create_task(process_call_log(session)),
    )

    try:
        await session.generate_reply(
            instructions=f"Say exactly: '{INBOUND_GREETING}'",
            allow_interruptions=False,
        )
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
            agent_name="inbound-agent",
            port=8081,
        )
    )
