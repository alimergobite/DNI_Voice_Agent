import os
import json
import base64
import audioop
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
        
    room_name = f"twilio_{request.phone_number.strip('+')}_{os.urandom(4).hex()}"
    
    # We use dynamic TwiML. Twilio will dial the user, and when they answer, connect them to our WebSocket bridge.
    twiml_str = (
        f'<Response>'
        f'<Connect>'
        f'<Stream url="wss://demo2.ergobite.com/ws/twilio/{room_name}" />'
        f'</Connect>'
        f'</Response>'
    )
    
    client = Client(os.getenv("TWILIO_ACCOUNT_SID"), os.getenv("TWILIO_AUTH_TOKEN"))
    try:
        call = client.calls.create(
            twiml=twiml_str,
            to=request.phone_number,
            from_=os.getenv("TWILIO_PHONE_NUMBER")
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
        
    return {"status": "dialing", "call_sid": call.sid, "room_name": room_name}

@router.websocket("/ws/twilio/{room_name}")
async def twilio_websocket_bridge(websocket: WebSocket, room_name: str):
    await websocket.accept()
    
    # Initialize LiveKit Room Connection for this phone call
    room = rtc.Room()
    
    # We need an audio source to push Twilio's audio into LiveKit
    audio_source = rtc.AudioSource(sample_rate=8000, num_channels=1)
    track = rtc.LocalAudioTrack.create_audio_track("phone_mic", audio_source)
    options = rtc.TrackPublishOptions()
    options.source = rtc.TrackSource.SOURCE_MICROPHONE
    
    try:
        # Generate a valid JWT token for the LiveKit Room
        from livekit import api
        token = api.AccessToken(settings.LIVEKIT_API_KEY, settings.LIVEKIT_API_SECRET)
        token.with_identity(f"phone_{room_name}").with_name("Customer Phone")
        token.with_grants(api.VideoGrants(roomJoin=True, room=room_name))
        jwt_token = token.to_jwt()
        
        # Connect to LiveKit
        await room.connect(settings.LIVEKIT_URL, jwt_token)
        
        # Publish the phone's audio track to the LiveKit room so the agent can hear it
        publication = await room.local_participant.publish_track(track, options)
        
        stream_sid_box = {"sid": None}
        
        @room.on("track_subscribed")
        def on_track_subscribed(track: rtc.Track, publication: rtc.RemoteTrackPublication, participant: rtc.RemoteParticipant):
            if track.kind == rtc.TrackKind.KIND_AUDIO:
                print(f"[Twilio Bridge] Agent audio track subscribed!")
                audio_stream = rtc.AudioStream(track)
                asyncio.create_task(process_agent_audio(audio_stream, stream_sid_box, websocket))
                
        async def process_agent_audio(audio_stream: rtc.AudioStream, stream_sid_box: dict, websocket: WebSocket):
            state = None
            async for event in audio_stream:
                if stream_sid_box["sid"] is None:
                    continue
                # event.frame is rtc.AudioFrame (PCM 16-bit). Usually 48000Hz from LiveKit.
                # 1. Resample to 8000Hz
                pcm_data = event.frame.data.tobytes()
                resampled_pcm, state = audioop.ratecv(pcm_data, 2, event.frame.num_channels, event.frame.sample_rate, 8000, state)
                # 2. Encode to mulaw
                mulaw_data = audioop.lin2ulaw(resampled_pcm, 2)
                # 3. Base64 encode and send
                payload = base64.b64encode(mulaw_data).decode('utf-8')
                media_msg = {
                    "event": "media",
                    "streamSid": stream_sid_box["sid"],
                    "media": {"payload": payload}
                }
                try:
                    await websocket.send_text(json.dumps(media_msg))
                except Exception:
                    break
        
        while True:
            data = await websocket.receive_text()
            msg = json.loads(data)
            
            if msg['event'] == 'start':
                stream_sid_box["sid"] = msg['start']['streamSid']
                print(f"[Twilio] Stream started: {stream_sid_box['sid']} for room {room_name}")
                
            elif msg['event'] == 'media':
                # Twilio sends base64 encoded mulaw at 8000Hz
                payload = msg['media']['payload']
                mulaw_data = base64.b64decode(payload)
                
                # Convert mulaw to 16-bit PCM for LiveKit
                pcm_data = audioop.ulaw2lin(mulaw_data, 2)
                
                # Create AudioFrame and push to LiveKit
                # Twilio sends 20ms chunks usually, so 160 samples per chunk
                samples_per_channel = len(pcm_data) // 2
                frame = rtc.AudioFrame(
                    data=pcm_data,
                    sample_rate=8000,
                    num_channels=1,
                    samples_per_channel=samples_per_channel
                )
                await audio_source.capture_frame(frame)
                
            elif msg['event'] == 'stop':
                print(f"[Twilio] Stream stopped: {stream_sid_box['sid']}")
                break
                
    except WebSocketDisconnect:
        print("[Twilio] WebSocket disconnected")
    except Exception as e:
        print(f"[Twilio Bridge Error] {e}")
    finally:
        await room.disconnect()
