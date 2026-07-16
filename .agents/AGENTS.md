# LiveKit & Twilio Voice Integration Rules

When building or debugging real-time voice pipelines between LiveKit and Twilio WebSockets, adhere to these strict requirements:

### 1. Twilio Outbound Audio Buffering (CRITICAL)
- **Constraint**: Twilio's WebSocket strictly requires audio packets to be exactly **160 bytes (20ms at 8000Hz mulaw)**. 
- **Rule**: Never stream varying frame sizes to Twilio. Always implement a `bytearray` buffer that accumulates `mulaw` data and slices off exactly 160 bytes per `websocket.send_text()` call.
- **Symptom of Failure**: Buffer underflow, leading to extremely robotic, stuttering audio and severe delays (15-30s) in the agent's response.

### 2. LiveKit Audio Resampling
- **Constraint**: Never use Python's `audioop` (e.g., `audioop.ratecv`) to downsample LiveKit audio to 8000Hz. The async nature of LiveKit frames corrupts the filter state.
- **Rule**: Use LiveKit's internal FFI resampling engine by requesting the exact sample rate during stream creation: `rtc.AudioStream.from_track(track=remote_track, sample_rate=8000, num_channels=1)`.

### 3. Preventing Double Agent Dispatch
- **Constraint**: If you manually dispatch an agent into a room via `create_dispatch`, LiveKit's default `request_fnc` will auto-dispatch a second agent into the same room, resulting in garbled overlapping audio.
- **Rule**: Ensure the worker's `request_fnc(req: JobRequest)` explicitly checks for metadata. E.g., `if req.job.metadata: await req.accept() else: await req.reject()`. 

### 4. Agent Session Startup Order
- **Constraint**: Calling `ctx.wait_for_participant()` before `session.start()` blocks the entire agent initialization until the Twilio bridge completes its handshake.
- **Rule**: Always call `await session.start()` immediately after `ctx.connect()`. Only block the `session.say()` or `session.chat()` commands with `wait_for_participant()`.
