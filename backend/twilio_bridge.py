import os
import json
import base64
import audioop
import asyncio
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException
from pydantic import BaseModel
from twilio.rest import Client
from livekit import rtc
from .config import settings

router = APIRouter()

class DialRequest(BaseModel):
    phone_number: str
    customer_name: str = "Valued Customer"
    policy_type: str = "individual"

@router.post("/api/dial")
async def dial_outbound(request: DialRequest):
    if not os.getenv("TWILIO_ACCOUNT_SID") or not os.getenv("TWILIO_AUTH_TOKEN") or not os.getenv("TWILIO_PHONE_NUMBER"):
        raise HTTPException(status_code=500, detail="Twilio credentials not configured on the server")

    from livekit import api as lkapi

    room_name = f"twilio_{request.phone_number.strip('+')}_{os.urandom(4).hex()}"

    # Step 1: Dial the customer via Twilio and enable recording
    twiml_str = (
        f'<Response>'
        f'<Connect>'
        f'<Stream url="wss://demo2.ergobite.com/ws/twilio/{room_name}" />'
        f'</Connect>'
        f'</Response>'
    )

    client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
    try:
        call = client.calls.create(
            twiml=twiml_str,
            to=request.phone_number,
            from_=os.getenv("TWILIO_PHONE_NUMBER"),
            record=True  # Enables call recording on Twilio
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    # Build metadata including the Twilio call SID so the agent can fetch the recording later
    metadata = json.dumps({
        "customer_name": request.customer_name,
        "policy_type": request.policy_type,
        "phone": request.phone_number,
        "tts_provider": "elevenlabs",
        "call_sid": call.sid
    })

    # Step 2: Pre-create the LiveKit Room and dispatch the agent ONCE
    lk_api = lkapi.LiveKitAPI(settings.LIVEKIT_URL, settings.LIVEKIT_API_KEY, settings.LIVEKIT_API_SECRET)
    try:
        await lk_api.room.create_room(lkapi.CreateRoomRequest(name=room_name))
        await lk_api.agent_dispatch.create_dispatch(
            lkapi.CreateAgentDispatchRequest(
                agent_name="",
                room=room_name,
                metadata=metadata,
            )
        )
        print(f"[Twilio] Agent dispatched to room {room_name} for Call SID {call.sid}")
    except Exception as e:
        print(f"[Twilio] Agent dispatch warning: {e}")
    finally:
        await lk_api.aclose()

    return {"status": "dialing", "call_sid": call.sid, "room_name": room_name}

@router.websocket("/ws/twilio/{room_name}")
async def twilio_websocket_bridge(websocket: WebSocket, room_name: str):
    await websocket.accept()

    # Audio source for Twilio → LiveKit direction (Twilio sends 8kHz mulaw)
    audio_source = rtc.AudioSource(sample_rate=8000, num_channels=1)
    track = rtc.LocalAudioTrack.create_audio_track("phone_mic", audio_source)
    options = rtc.TrackPublishOptions()
    options.source = rtc.TrackSource.SOURCE_MICROPHONE

    room = rtc.Room()
    agent_audio_task = None

    try:
        from livekit import api
        token = api.AccessToken(settings.LIVEKIT_API_KEY, settings.LIVEKIT_API_SECRET)
        token.with_identity(f"phone_{room_name}").with_name("Customer Phone")
        token.with_grants(api.VideoGrants(room_join=True, room=room_name))
        jwt_token = token.to_jwt()

        await room.connect(settings.LIVEKIT_URL, jwt_token)
        await room.local_participant.publish_track(track, options)

        stream_sid_box = {"sid": None}
        agent_started = False

        async def process_agent_audio(audio_stream: rtc.AudioStream):
            """
            Reads 8kHz mono PCM frames directly from LiveKit (we requested 8000Hz),
            converts to mulaw, and sends 160-byte (20ms) chunks to Twilio.
            No audioop.ratecv needed — LiveKit resamples for us.
            """
            out_buffer = bytearray()
            async for event in audio_stream:
                if stream_sid_box["sid"] is None:
                    continue

                frame = event.frame
                pcm_bytes = bytes(frame.data)

                # Force mono if needed (safety fallback)
                if frame.num_channels == 2:
                    pcm_bytes = audioop.tomono(pcm_bytes, 2, 0.5, 0.5)

                # Convert 16-bit PCM → 8-bit mulaw
                mulaw_bytes = audioop.lin2ulaw(pcm_bytes, 2)

                # Buffer into exactly 160-byte chunks (20ms @ 8kHz mulaw)
                out_buffer.extend(mulaw_bytes)
                while len(out_buffer) >= 160:
                    chunk = bytes(out_buffer[:160])
                    out_buffer = out_buffer[160:]

                    payload = base64.b64encode(chunk).decode("utf-8")
                    msg = json.dumps({
                        "event": "media",
                        "streamSid": stream_sid_box["sid"],
                        "media": {"payload": payload}
                    })
                    try:
                        await websocket.send_text(msg)
                    except Exception:
                        return

        @room.on("track_subscribed")
        def on_track_subscribed(
            remote_track: rtc.Track,
            publication: rtc.RemoteTrackPublication,
            participant: rtc.RemoteParticipant
        ):
            nonlocal agent_audio_task, agent_started
            if remote_track.kind == rtc.TrackKind.KIND_AUDIO and not agent_started:
                agent_started = True
                print("[Twilio Bridge] Agent audio track subscribed — starting stream to phone")
                # Use from_track with explicit 8kHz mono so LiveKit resamples internally
                audio_stream = rtc.AudioStream.from_track(
                    track=remote_track,
                    sample_rate=8000,
                    num_channels=1,
                )
                agent_audio_task = asyncio.ensure_future(process_agent_audio(audio_stream))

        # Main loop: receive Twilio WebSocket messages
        async for raw in websocket.iter_text():
            msg = json.loads(raw)
            event = msg.get("event")

            if event == "start":
                stream_sid_box["sid"] = msg["start"]["streamSid"]
                print(f"[Twilio] Stream started: {stream_sid_box['sid']} for room {room_name}")

            elif event == "media":
                # Twilio → LiveKit: decode mulaw, push 8kHz mono PCM
                mulaw = base64.b64decode(msg["media"]["payload"])
                pcm = audioop.ulaw2lin(mulaw, 2)
                samples = len(pcm) // 2
                frame = rtc.AudioFrame(
                    data=pcm,
                    sample_rate=8000,
                    num_channels=1,
                    samples_per_channel=samples
                )
                await audio_source.capture_frame(frame)

            elif event == "stop":
                print(f"[Twilio] Stream stopped for room {room_name}")
                break

    except WebSocketDisconnect:
        print(f"[Twilio] WebSocket disconnected for room {room_name}")
    except Exception as e:
        print(f"[Twilio Bridge Error] {e}")
        import traceback
        traceback.print_exc()
    finally:
        if agent_audio_task and not agent_audio_task.done():
            agent_audio_task.cancel()
        await room.disconnect()
