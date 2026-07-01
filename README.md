# DNI Voice Agent — Production Setup

## Prerequisites
- Python 3.10+
- Node.js 18+
- Docker Desktop (running)

---

## Step 1: Configure API Keys

Open the `.env` file and fill in your API keys:

```env
GEMINI_API_KEY=your_gemini_key_here
DEEPGRAM_API_KEY=your_deepgram_key_here
ELEVENLABS_API_KEY=your_elevenlabs_key_here
SARVAM_API_KEY=your_sarvam_key_here
```

**To switch TTS engine (ElevenLabs ↔ Sarvam)**, add this line to `.env`:
```env
TTS_ENGINE=sarvam   # or: TTS_ENGINE=elevenlabs
```

---

## Step 2: Start the Local LiveKit Server

```bash
docker-compose up -d
```

This starts a local LiveKit server (free, no subscription required).

---

## Step 3: Install Python Dependencies

```bash
pip install -r requirements.txt
```

---

## Step 4: Start the AI Voice Agents

Open **two separate terminals**:

**Terminal 1 — Inbound Agent:**
```bash
python -m backend.agents.inbound start
```

**Terminal 2 — Outbound Agent:**
```bash
python -m backend.agents.outbound start
```

---

## Step 5: Start the React Dashboard (Frontend)

Open a **third terminal**:

```bash
cd frontend
npm install
npm run dev
```

Open your browser at: **http://localhost:3000**

---

## Step 6: (Optional) Start the FastAPI Backend

Open a **fourth terminal** (only needed for the call log API):

```bash
uvicorn backend.main:app --reload --port 8000
```

---

## Project Structure

```
DNI_Voice_Agent_Production/
├── backend/
│   ├── config.py          ← Toggle TTS/LLM engine here
│   ├── database.py        ← SQLite call logs DB
│   ├── main.py            ← FastAPI server
│   ├── services/
│   │   ├── llm_service.py ← LLM engine (Gemini / GPT-4o)
│   │   ├── tts_service.py ← TTS engine (ElevenLabs / Sarvam)
│   │   ├── stt_service.py ← STT engine (Deepgram)
│   │   └── prompts.py     ← Call scripts (Inbound / Outbound)
│   └── agents/
│       ├── inbound.py     ← LiveKit Inbound Agent
│       └── outbound.py    ← LiveKit Outbound Agent
├── frontend/              ← React (Next.js) Dashboard
├── docker-compose.yml     ← Local LiveKit Server
├── livekit.yaml           ← LiveKit config
├── .env                   ← API Keys
└── requirements.txt       ← Python dependencies
```
