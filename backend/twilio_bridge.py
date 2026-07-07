import os
import json
import base64
import audioop
import asyncio
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from twilio.rest import Client
from livekit import rtc
from .config import settings

router = APIRouter()

@router.post("/api/twiml/{room_name}")
async def twiml_callback(room_name: str):
    """Twilio hits this URL ONLY when the call is answered (or human detected)."""
    twiml_str = (
        f'<Response>'
        f'<Connect>'
        f'<Stream url="wss://demo2.ergobite.com/ws/twilio/{room_name}" />'
        f'</Connect>'
        f'</Response>'
    )
    return HTMLResponse(content=twiml_str, media_type="text/xml")

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

    # Use a webhook URL so Twilio AMD can delay the TwiML execution until human detection
    twiml_url = f"https://demo2.ergobite.com/api/twiml/{room_name}"

    client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
    try:
        call = client.calls.create(
            url=twiml_url,
            to=request.phone_number,
            from_=os.getenv("TWILIO_PHONE_NUMBER"),
            record=True,
            machine_detection="Enable",
            async_amd="false"
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

    # Audio source for Twilio → LiveKit direction (Upsampled to 16kHz for VAD)
    audio_source = rtc.AudioSource(sample_rate=16000, num_channels=1)
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
            print("[Twilio Bridge] process_agent_audio task started")
            out_buffer = bytearray()
            ratecv_state = None
            
            async for event in audio_stream:
                try:
                    if stream_sid_box["sid"] is None:
                        continue

                    frame = event.frame
                    pcm_bytes = bytes(frame.data)

                    # 1. Resample to 8000 Hz if needed
                    if frame.sample_rate != 8000:
                        pcm_bytes, ratecv_state = audioop.ratecv(
                            pcm_bytes, 2, frame.num_channels, frame.sample_rate, 8000, ratecv_state
                        )
                    
                    # 2. Force mono if needed
                    if frame.num_channels == 2:
                        pcm_bytes = audioop.tomono(pcm_bytes, 2, 0.5, 0.5)

                    # 3. Convert 16-bit PCM → 8-bit mulaw
                    mulaw_bytes = audioop.lin2ulaw(pcm_bytes, 2)

                    # Buffer into 160-byte chunks (20ms @ 8kHz mulaw)
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
                        await websocket.send_text(msg)
                except Exception as e:
                    print(f"[Twilio Bridge] Frame drop error: {e}")

        # Helper to start processing agent audio
        def start_agent_audio(remote_track: rtc.Track):
            nonlocal agent_audio_task, agent_started
            if remote_track.kind == rtc.TrackKind.KIND_AUDIO and not agent_started:
                agent_started = True
                print("[Twilio Bridge] Agent audio track found — starting stream to phone")
                try:
                    audio_stream = rtc.AudioStream(remote_track)
                    agent_audio_task = asyncio.ensure_future(process_agent_audio(audio_stream))
                except Exception as e:
                    print(f"[Twilio Bridge] Failed to create AudioStream: {e}")

        @room.on("track_subscribed")
        def on_track_subscribed(
            remote_track: rtc.Track,
            publication: rtc.RemoteTrackPublication,
            participant: rtc.RemoteParticipant
        ):
            start_agent_audio(remote_track)

        # Check if the agent is already in the room and published its track before we connected
        for participant in room.remote_participants.values():
            for publication in participant.track_publications.values():
                if publication.track:
                    start_agent_audio(publication.track)

        # Main loop: receive Twilio WebSocket messages
        tw_ratecv_state = None
        async for raw in websocket.iter_text():
            msg = json.loads(raw)
            event = msg.get("event")

            if event == "start":
                stream_sid_box["sid"] = msg["start"]["streamSid"]
                print(f"[Twilio] Stream started: {stream_sid_box['sid']} for room {room_name}")

            elif event == "media":
                try:
                    # Twilio → LiveKit: decode mulaw, push 16kHz mono PCM for VAD compatibility
                    mulaw = base64.b64decode(msg["media"]["payload"])
                    pcm_8k = audioop.ulaw2lin(mulaw, 2)
                    
                    # Upsample 8kHz -> 16kHz (MUST KEEP STATE BETWEEN FRAMES)
                    pcm_16k, tw_ratecv_state = audioop.ratecv(pcm_8k, 2, 1, 8000, 16000, tw_ratecv_state)
                    samples = len(pcm_16k) // 2
                    
                    frame = rtc.AudioFrame(
                        data=pcm_16k,
                        sample_rate=16000,
                        num_channels=1,
                        samples_per_channel=samples
                    )
                    await audio_source.capture_frame(frame)
                except Exception as e:
                    with open("/tmp/twilio_media_error.log", "a") as f:
                        f.write(f"Media Event Error: {e}\n")

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
