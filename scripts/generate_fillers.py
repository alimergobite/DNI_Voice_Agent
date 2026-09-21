"""Pre-render the conversational fillers to raw 8kHz mulaw.

Run once (and again whenever the filler phrases or the TTS voice change):

    python scripts/generate_fillers.py

Writes backend/fillers/<slug>.ulaw - raw mulaw at 8000 Hz, exactly the
format twilio_bridge.py sends, so playback is a byte-for-byte copy with no
TTS call, no resampling and no involvement from LiveKit's speech scheduler.
"""

import asyncio
import audioop
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from dotenv import load_dotenv

load_dotenv(override=True)

from livekit.agents.utils import http_context  # noqa: E402

from backend.services.tts_service import get_tts_engine  # noqa: E402

FILLERS = {
    "one_moment": "One moment.",
    "just_a_second": "Just a second.",
    "checking": "Let me check that.",
    "okay": "Okay.",
}

OUT_DIR = os.path.join(os.path.dirname(__file__), "..", "backend", "fillers")


async def render(tts, text: str) -> bytes:
    """Synthesize text and return it as 8kHz mulaw."""
    pcm = bytearray()
    src_rate = None
    async for ev in tts.synthesize(text):
        frame = ev.frame
        src_rate = frame.sample_rate
        pcm += bytes(frame.data)

    if not pcm:
        raise RuntimeError(f"TTS returned no audio for {text!r}")

    # Downsample to 8kHz, then encode as mulaw. ratecv is safe here: this is a
    # one-off offline conversion of a complete buffer, not the live async
    # stream that AGENTS.md 7.2 warns about.
    pcm8k, _ = audioop.ratecv(bytes(pcm), 2, 1, src_rate, 8000, None)
    ulaw = audioop.lin2ulaw(pcm8k, 2)

    # Pad to a whole number of 160-byte frames so playback sends every byte.
    # 0xFF is mulaw silence, and the clip already ends quiet, so this is
    # inaudible.
    if len(ulaw) % 160:
        ulaw += b"\xff" * (160 - len(ulaw) % 160)
    return ulaw


async def main() -> None:
    provider = sys.argv[1] if len(sys.argv) > 1 else "sarvam"
    os.makedirs(OUT_DIR, exist_ok=True)

    async with http_context.open():
        tts = get_tts_engine(provider)
        # First synthesis pays a cold-start penalty; discard it so the timings
        # printed below reflect steady state.
        async for _ in tts.synthesize("warm up"):
            pass

        for slug, text in FILLERS.items():
            ulaw = await render(tts, text)
            path = os.path.join(OUT_DIR, f"{slug}.ulaw")
            with open(path, "wb") as fh:
                fh.write(ulaw)
            print(f"{slug:16} {text!r:22} {len(ulaw):6d} bytes  {len(ulaw)/8000:.2f}s")

    print(f"\nWrote {len(FILLERS)} files to {os.path.normpath(OUT_DIR)}")


if __name__ == "__main__":
    asyncio.run(main())
