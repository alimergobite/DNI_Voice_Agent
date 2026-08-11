# DNI Voice Agent — Complete Codebase Reference for LLMs

> **Project**: Dubai National Insurance (DNI) Real-Time AI Voice Agent  
> **Purpose**: Automated outbound & inbound insurance phone calls via AI  
> **Last Updated**: August 2026  

---

## 1. Project Overview

This is a **production real-time voice agent** that makes and receives phone calls on behalf of Dubai National Insurance / Platinum Insurance Broker LLC. The agent ("Aisha") calls customers, verifies their identity (KYC), collects feedback, and logs everything to a dashboard.

### Core Flow
```
Twilio (Phone Network) ↔ WebSocket Bridge ↔ LiveKit (WebRTC) ↔ AI Agent Pipeline (STT → LLM → TTS)
```

### Key Business Logic
- **Outbound calls**: Agent calls a customer, greets them, performs KYC verification (date of birth, Emirates ID, or trade licence), collects a 1-10 rating, and ends the call.
- **Inbound calls**: Agent answers, asks if the customer needs a new policy or has an existing one, and assists.
- **Post-call**: Transcript is sent to Gemini for structured extraction (intent, sentiment, status, summary), then saved to SQLite and displayed on the dashboard.

---

## 2. Technology Stack

| Layer | Technology | Details |
|-------|-----------|---------|
| **Telephony** | Twilio | Outbound dialing, call recording, mulaw audio over WebSocket |
| **Media Server** | LiveKit (self-hosted) | WebRTC rooms, audio routing, agent dispatch |
| **Agent Framework** | `livekit-agents` v1.6+ | `AgentSession`, `VoicePipelineAgent`, VAD, turn handling |
| **STT** | Sarvam AI (`saaras:v3`) | Primary. Hindi/English/Hinglish via WebSocket streaming. Language: `en-IN` |
| **STT Fallback** | Deepgram (`nova-2-general`) | Secondary. English-India. Used if Sarvam is down |
| **LLM** | Azure OpenAI (`grok-4-20-reasoning`) | Via `https://microfoundryergo.services.ai.azure.com/openai/v1` |
| **TTS Primary** | ElevenLabs (`eleven_flash_v2_5`) | Low-latency streaming. Voice ID configurable |
| **TTS Fallback** | Sarvam AI (`bulbul:v3`, speaker `ritu`) | Used when `tts_provider=sarvam` is passed from frontend |
| **VAD** | Silero VAD | `activation_threshold=0.7`, `min_speech_duration=0.05`, `min_silence_duration=0.25` |
| **Backend API** | FastAPI + Uvicorn | REST endpoints for dialing, call logs, room management |
| **Database** | SQLite (`dni_voice_agent.db`) | Call logs with transcripts, ratings, recordings |
| **Post-Call Analysis** | Google Gemini (`gemini-2.5-flash`) | Extracts structured JSON from transcripts |
| **Frontend** | Next.js (React, TypeScript) | Dashboard with call history, live call modal, new call form |
| **Deployment** | PM2 + Docker Compose + Nginx | Ubuntu server at `demo2.ergobite.com` |

---

## 3. Directory Structure

```
DNI_Voice_Agent_Production/
├── .agents/
│   └── AGENTS.md                  # THIS FILE — project rules & documentation
├── .env                           # All API keys and secrets (never commit real keys)
├── requirements.txt               # Python dependencies
├── docker-compose.yml             # LiveKit server + Redis + Egress
├── livekit.yaml                   # LiveKit server configuration
├── egress.yaml                    # LiveKit Egress (recording) config
├── gcp-service-account.json       # Google Cloud service account for Gemini
├── dni_voice_agent.db             # SQLite database (auto-created)
│
├── backend/
│   ├── __init__.py
│   ├── config.py                  # Pydantic Settings — loads .env
│   ├── database.py                # SQLAlchemy models (CallLog table)
│   ├── main.py                    # FastAPI app — REST API + call log processing
│   ├── twilio_bridge.py           # WebSocket bridge: Twilio ↔ LiveKit audio
│   │
│   ├── agents/
│   │   ├── outbound.py            # Outbound call agent (primary production agent)
│   │   └── inbound.py             # Inbound call agent
│   │
│   └── services/
│       ├── llm_service.py         # LLM engine factory (Azure OpenAI)
│       ├── stt_service.py         # STT engine factory (Sarvam / Deepgram)
│       ├── tts_service.py         # TTS engine factory (ElevenLabs / Sarvam)
│       └── prompts.py             # System prompts for outbound & inbound agents
│
├── frontend/
│   ├── .env.local                 # Frontend env (NEXT_PUBLIC_LIVEKIT_URL, NEXT_PUBLIC_API_URL)
│   ├── src/app/
│   │   ├── page.tsx               # Main dashboard — single-page app (~1000 lines)
│   │   ├── layout.tsx             # Root layout
│   │   ├── globals.css            # Global styles
│   │   └── api/                   # Next.js API routes (if any)
│   └── package.json
│
└── recordings/                    # Local recording storage (mounted by Egress)
```

---

## 4. File-by-File Deep Dive

### 4.1 `backend/config.py` — Settings
- Uses `pydantic_settings.BaseSettings` to load all `.env` variables.
- All API keys have empty-string defaults so the app doesn't crash if a key is missing.
- Key settings: `LIVEKIT_URL`, `LIVEKIT_API_KEY`, `LIVEKIT_API_SECRET`, `AZURE_OPENAI_ENDPOINT`, `AZURE_OPENAI_API_KEY`, `SARVAM_API_KEY`, `ELEVENLABS_API_KEY`, `ELEVENLABS_VOICE_ID`, `GEMINI_API_KEY` (×3 for rotation), `DEEPGRAM_API_KEY`, Twilio creds.

### 4.2 `backend/database.py` — SQLAlchemy ORM
- Single table: `call_logs`
- Columns: `id`, `call_id` (sequential `#CAL-001`), `customer_name`, `phone_number`, `policy_type`, `date_of_birth`, `emirates_id`, `company_name`, `trade_licence`, `start_time`, `duration_seconds`, `rating` (float 1-10), `status` (Completed/Abandoned/Not Answered/Wrong Person/Callback Requested), `transcript`, `recording_url`
- Tables are auto-created on import via `Base.metadata.create_all()`

### 4.3 `backend/main.py` — FastAPI Application
- **`GET /`** — Health check
- **`GET /calls`** — Returns all call logs ordered by most recent
- **`POST /token`** — Generates a LiveKit JWT for frontend participants
- **`POST /api/process_log`** — Receives transcript JSON from the agent, runs Gemini analysis in background, saves to SQLite. This is the critical call-logging endpoint.
- **`POST /api/dial`** — See `twilio_bridge.py`
- Mounts `/recordings` static directory for serving audio files
- CORS is fully open (`allow_origins=["*"]`)

### 4.4 `backend/twilio_bridge.py` — The Audio Bridge (CRITICAL)
This is the most complex and fragile file. It handles:

#### Endpoints:
- **`POST /api/twiml/{room_name}`** — Returns TwiML XML that tells Twilio to open a `<Stream>` WebSocket to our server
- **`POST /api/dial`** — Initiates an outbound call: creates Twilio call → creates LiveKit room → dispatches agent
- **`GET /api/kill_room/{room_name}`** — Force-terminates a call: kills Twilio call + deletes LiveKit room
- **`GET /api/is_room_active/{room_name}`** — Checks if a room is still in the active map
- **`WS /ws/twilio/{room_name}`** — The core WebSocket bridge

#### WebSocket Bridge Flow (`/ws/twilio/{room_name}`):
1. **Twilio → LiveKit (Uplink)**:
   - Receives base64-encoded 8kHz mulaw from Twilio's `media` events
   - Decodes mulaw → 16-bit PCM via `audioop.ulaw2lin()`
   - Upsamples 8kHz → 16kHz via `audioop.ratecv()` (stateful — `tw_ratecv_state` persists across frames)
   - Buffers into 320-byte chunks (10ms at 16kHz, 160 samples)
   - Creates `rtc.AudioFrame` and pushes to LiveKit via `audio_source.capture_frame()`

2. **LiveKit → Twilio (Downlink)**:
   - Subscribes to agent's audio track via `rtc.AudioStream.from_track(track, sample_rate=8000, num_channels=1)`
   - Converts 16-bit PCM → 8-bit mulaw via `audioop.lin2ulaw()`
   - Buffers into exactly 160-byte chunks (20ms at 8kHz)
   - Sends as base64-encoded JSON `{"event": "media", "streamSid": "...", "media": {"payload": "..."}}` via `websocket.send_text()`

3. **Room Events**:
   - `track_subscribed`: Starts the agent audio processing task
   - `disconnected`: Closes the Twilio WebSocket to drop the call

### 4.5 `backend/agents/outbound.py` — Outbound Agent (Production)
This is the main agent that makes calls. Key flow:

1. **Reads metadata** from the dispatch request (customer name, policy type, KYC data, TTS provider, call SID)
2. **Builds AgentSession** with STT (Sarvam), LLM (Azure OpenAI), TTS (ElevenLabs or Sarvam), VAD (Silero)
3. **Connects** to LiveKit room with `AUDIO_ONLY` subscription
4. **Starts session** locked to the phone participant via `RoomInputOptions(participant_identity=f"phone_{room_name}")`
5. **Waits for phone participant** to join (polling loop)
6. **Speaks greeting**: `"Hi, this is Aisha from Dubai National Insurance. Am I speaking with {customer_name}?"`
7. **Conversation loop** is handled automatically by LiveKit's `AgentSession` pipeline (STT→LLM→TTS)

#### Diagnostic Logging (important for debugging):
- `[STT HEARD] "text" (is_final=True/False)` — What the STT engine transcribed
- `[LLM REPLY] Agent is speaking...` — When the LLM starts generating
- `[CONVERSATION] role: text` — Each turn added to the conversation

#### Auto-Hangup Logic:
- Detects goodbye phrases in assistant messages: "wonderful day", "thank you for your time", "security reasons I cannot proceed"
- Waits 4 seconds, saves transcript, then kills the room

#### Transcript Saving:
- `save_transcript_to_db()` fires on: participant disconnect, room disconnect, or auto-hangup
- Uses `urllib.request` to POST to `http://localhost:5000/api/process_log` (fallback to `:8000`)
- Includes: customer_name, policy_type, full transcript, metadata, duration, recording_url

#### Double-Agent Prevention:
```python
async def request_fnc(req: JobRequest):
    if req.job.metadata:
        await req.accept()    # Explicit dispatch — accept
    else:
        await req.reject()    # Auto-dispatch — reject to prevent duplicates
```

### 4.6 `backend/agents/inbound.py` — Inbound Agent
- Simpler than outbound. No KYC logic.
- Greeting: "Hello! Welcome to Dubai National Insurance. I'm Aisha..."
- Post-call logging writes to `Call_Logs/inbound_{timestamp}.json` (file-based, not SQLite)
- Accepts ALL job requests (no metadata check needed for inbound)

### 4.7 `backend/services/llm_service.py` — LLM Factory
- Returns a `livekit.plugins.openai.LLM` instance
- Creates an `AsyncOpenAI` client pointed at the Azure endpoint
- Current model: `grok-4-20-reasoning` (temperature=0.0)
- **KNOWN ISSUE**: This model is a reasoning model with 15-20s time-to-first-token. See Section 7.

### 4.8 `backend/services/stt_service.py` — STT Factory
- Default: Sarvam AI `saaras:v3` with `language="en-IN"`
- Fallback: Deepgram `nova-2-general` with `language="en-IN"`
- The language parameter controls output script (en-IN = Roman, hi-IN = Devanagari, unknown = auto-detect)

### 4.9 `backend/services/tts_service.py` — TTS Factory
- Default: ElevenLabs `eleven_flash_v2_5` with configurable voice ID and `streaming_latency=2`
- Fallback: Sarvam AI `bulbul:v3` with speaker `ritu`
- The `tts_provider` parameter is passed from the frontend dial form

### 4.10 `backend/services/prompts.py` — System Prompts
- **Outbound prompt**: Extremely detailed. Includes:
  - Role: "Aisha from Platinum Insurance Broker LLC"
  - KYC flow: DOB verification → Emirates ID verification (individual) OR Trade Licence verification (corporate)
  - Strict 1-retry security rule (2 wrong attempts = immediate hangup)
  - Multilingual date matching (handles Hindi/Hinglish/English spoken dates)
  - No-echo rule (never repeat back sensitive data)
  - No-emoji rule (TTS engines crash on emojis)
  - English-only reply rule (TTS cannot pronounce Hindi/Arabic)
  - 4-step script: Introduction → KYC → Feedback (1-10 rating) → Closing
- **Inbound prompt**: Simple customer support assistant

### 4.11 `frontend/src/app/page.tsx` — Dashboard (Single Page App)
- **Call Activity Table**: Lists all calls with status badges, duration, ratings, pagination
- **Expandable Rows**: Click a call to see full transcript and play recording
- **New Call Modal**: Form with Individual/Corporate tabs, phone number, customer details, TTS provider selector
- **Quick Call Modal**: Simplified dial form
- **Live Call Modal**: Shows real-time transcription during active calls via LiveKit room connection
- **Stats Cards**: Total calls, avg duration, avg rating, active calls count
- **Search & Filter**: By customer name, status, policy type

---

## 5. Infrastructure & Deployment

### Server
- **Host**: `demo2.ergobite.com` (Ubuntu, IBM Cloud)
- **Nginx**: Reverse proxy on port 443 (HTTPS) → localhost:5000 (FastAPI) and localhost:3000 (Next.js)
- **PM2 Processes**:
  - `dni-agent`: Runs `python backend/agents/outbound.py start` (LiveKit agent worker on port 8082)
  - FastAPI: Runs via `uvicorn backend.main:app --port 5000`
  - Next.js frontend: `npm run start` on port 3000

### Docker Compose Services
- **LiveKit Server**: WebRTC media server on port 7880 (WS), 7881 (TCP), 50000-50200 (UDP/WebRTC)
- **Redis**: Required by LiveKit for room state
- **LiveKit Egress**: Records calls to `/recordings` directory

### LiveKit Configuration (`livekit.yaml`)
- API Key: `DNI_LIVEKIT_KEY`
- API Secret: `DNI_LIVEKIT_SECRET_THAT_IS_LONG_ENOUGH_FOR_SECURITY`
- TURN server enabled on UDP port 3478

### Deployment Workflow
```bash
# On the server:
cd /var/www/DNI_Voice_Agent_Production/
git pull origin master
pm2 restart dni-agent
```

---

## 6. Data Flow Diagrams

### Outbound Call Flow
```
1. Dashboard clicks "Dial" → POST /api/dial {phone, customer_name, policy_type, ...}
2. FastAPI creates Twilio call with TwiML URL → Twilio dials the phone number
3. FastAPI creates LiveKit room + dispatches agent (outbound_agent)
4. When call is answered → Twilio hits POST /api/twiml/{room_name} → returns <Stream> TwiML
5. Twilio opens WebSocket to WS /ws/twilio/{room_name}
6. Bridge joins LiveKit room as "phone_{room_name}" participant
7. Agent joins same room, publishes audio track
8. Audio flows bidirectionally: Phone ↔ Twilio WS ↔ Bridge ↔ LiveKit ↔ Agent
9. Agent greets, STT transcribes user speech, LLM generates reply, TTS speaks it
10. On disconnect → transcript saved via POST /api/process_log → Gemini analysis → SQLite
```

### Audio Encoding Pipeline
```
Phone → Twilio (8kHz mulaw) → Bridge (ulaw→PCM, 8k→16k upsample) → LiveKit (16kHz PCM) → Agent STT
Agent TTS → LiveKit (varies) → Bridge (AudioStream@8kHz, PCM→mulaw, 160-byte buffer) → Twilio → Phone
```

---

## 7. CRITICAL Rules & Known Issues

### 7.1 Twilio Outbound Audio Buffering (CRITICAL)
- **Constraint**: Twilio's WebSocket strictly requires audio packets to be exactly **160 bytes (20ms at 8000Hz mulaw)**.
- **Rule**: Never stream varying frame sizes to Twilio. Always implement a `bytearray` buffer that accumulates `mulaw` data and slices off exactly 160 bytes per `websocket.send_text()` call.
- **Symptom of Failure**: Buffer underflow, leading to extremely robotic, stuttering audio and severe delays (15-30s) in the agent's response.

### 7.2 LiveKit Audio Resampling (Downlink: LiveKit → Twilio)
- **Constraint**: Never use Python's `audioop` (e.g., `audioop.ratecv`) to **downsample** LiveKit audio to 8000Hz. The async nature of LiveKit frames corrupts the filter state.
- **Rule**: Use LiveKit's internal FFI resampling engine by requesting the exact sample rate during stream creation: `rtc.AudioStream.from_track(track=remote_track, sample_rate=8000, num_channels=1)`.
- **Note**: `audioop.ratecv` IS used for **upsampling** (Twilio → LiveKit, 8kHz→16kHz) and works fine there because the bridge controls frame timing.

### 7.3 Preventing Double Agent Dispatch
- **Constraint**: If you manually dispatch an agent into a room via `create_dispatch`, LiveKit's default `request_fnc` will auto-dispatch a second agent into the same room, resulting in garbled overlapping audio.
- **Rule**: Ensure the worker's `request_fnc(req: JobRequest)` explicitly checks for metadata. E.g., `if req.job.metadata: await req.accept() else: await req.reject()`.

### 7.4 Agent Session Startup Order
- **Constraint**: Calling `ctx.wait_for_participant()` before `session.start()` blocks the entire agent initialization until the Twilio bridge completes its handshake.
- **Rule**: Always call `await session.start()` immediately after `ctx.connect()`. Only block the `session.say()` or `session.chat()` commands with `wait_for_participant()`.

### 7.5 LLM Model Latency (CRITICAL — ACTIVE ISSUE)
- **Constraint**: Reasoning models (e.g., `grok-4-20-reasoning`) perform internal chain-of-thought before producing visible output. This causes **15-20 seconds of silence** on the phone before the first word is spoken.
- **Tested Results** (August 11, 2026): 3 consecutive streaming tests showed time-to-first-token of 15.64s, 19.39s, and 14.56s.
- **Additional Problem**: The LiveKit OpenAI plugin does NOT handle reasoning model streaming correctly. Reasoning models send `reasoning_content` deltas before `content` deltas. The plugin ignores `reasoning_content` and may error with: `"model output must contain either output text or tool calls, these cannot both be empty"`.
- **Rule**: NEVER use a reasoning model (any model with "reasoning" in the name) for real-time voice. Use fast, non-reasoning models that produce the first token in <1 second.

### 7.6 TTS Emoji/Markdown Crash Prevention
- **Constraint**: ElevenLabs and Sarvam TTS engines crash or produce garbage audio when the LLM output contains emojis (😊, 👋) or markdown formatting (*, #, **).
- **Rule**: The system prompt includes a `CRITICAL NO-EMOJI RULE`. If changing the LLM or prompt, always preserve this rule.

### 7.7 TTS Language Limitation
- **Constraint**: Both ElevenLabs and Sarvam TTS cannot pronounce Hindi or Arabic text.
- **Rule**: The system prompt forces English-only replies regardless of user's language. Always preserve the `CRITICAL LANGUAGE RULE` in prompts.

### 7.8 Sarvam STT Language Parameter
- `language="en-IN"` → Outputs Roman script (English). Good for mixed Hindi/English speech.
- `language="hi-IN"` → Outputs Devanagari script (Hindi). Converts English words to Hindi script too (e.g., "speaking" → "स्पीकिंग").
- `language="unknown"` → Auto-detects language per segment. May be inconsistent.
- **Current Setting**: `en-IN` (recommended for this use case)

---

## 8. Environment Variables (`.env`)

| Variable | Purpose |
|----------|---------|
| `LIVEKIT_URL` | WebSocket URL for LiveKit server (`ws://localhost:7880`) |
| `LIVEKIT_API_KEY` | LiveKit auth key |
| `LIVEKIT_API_SECRET` | LiveKit auth secret (must be 32+ chars) |
| `AZURE_OPENAI_ENDPOINT` | Azure OpenAI-compatible endpoint for LLM |
| `AZURE_OPENAI_API_KEY` | API key for Azure endpoint |
| `SARVAM_API_KEY` | Sarvam AI key for STT and TTS |
| `DEEPGRAM_API_KEY` | Deepgram key (fallback STT) |
| `ELEVENLABS_API_KEY` | ElevenLabs key for TTS |
| `ELEVENLABS_VOICE_ID` | ElevenLabs voice to use |
| `GEMINI_API_KEY` / `_2` / `_3` | Google Gemini keys for post-call analysis (3 for rotation) |
| `GROQ_API_KEY` | Groq key (not currently active) |
| `TWILIO_ACCOUNT_SID` | Twilio account SID |
| `TWILIO_AUTH_TOKEN` | Twilio auth token |
| `TWILIO_PHONE_NUMBER` | Twilio outbound caller ID |
| `ANTHROPIC_API_KEY` | Anthropic key (not currently active) |
| `GOOGLE_APPLICATION_CREDENTIALS` | Path to GCP service account JSON |

---

## 9. API Contracts

### `POST /api/dial` — Initiate Outbound Call
```json
{
  "phone_number": "+971501234567",
  "customer_name": "Ali Mohammed",
  "policy_type": "individual",
  "date_of_birth": "1990-02-03",
  "emirates_id": "1234",
  "company_name": "",
  "trade_licence": "",
  "tts_provider": "elevenlabs"
}
```
Response: `{"status": "dialing", "call_sid": "CA...", "room_name": "dni-outbound-abc12345"}`

### `POST /api/process_log` — Save Call Transcript
```json
{
  "customer_name": "Ali Mohammed",
  "policy_type": "individual",
  "transcript": "ASSISTANT: Hi...\nUSER: Yes speaking...",
  "metadata": {"phone": "+971...", "call_sid": "CA...", "date_of_birth": "...", "emirates_id": "..."},
  "duration": 120,
  "recording_url": null
}
```
Response: `{"status": "processing"}` — Analysis happens in background.

### `GET /api/kill_room/{room_name}?call_sid=CA...` — Force End Call
Terminates both the Twilio call and the LiveKit room.

### `GET /calls` — Fetch All Call Logs
Returns array of `CallLog` objects ordered by most recent.

---

## 10. Common Debugging Checklist

1. **Agent not greeting?** → Check PM2 logs for errors during `session.start()` or `session.say()`. Verify TTS API key is valid.
2. **Agent greets but doesn't reply?** → Check `[STT HEARD]` lines in PM2 logs. If present, the LLM is either too slow (reasoning model) or erroring silently. If absent, the Twilio→LiveKit audio bridge is broken.
3. **Robotic/stuttering audio?** → Twilio buffer issue. Ensure 160-byte chunks on downlink.
4. **Transcript in Hindi script?** → STT `language` is set to `hi-IN`. Change to `en-IN`.
5. **No call logs in dashboard?** → Check if the `process_log` endpoint is reachable from the agent (localhost:5000 or :8000).
6. **Double agent / overlapping audio?** → `request_fnc` is not rejecting auto-dispatched jobs.
7. **"worker is at full capacity"** → Too many concurrent calls. The agent worker has a load threshold of 0.7.
