"use client";

import { useState, useEffect, useRef } from "react";
import {
  LiveKitRoom,
  RoomAudioRenderer,
  useTranscriptions,
  useRemoteParticipants,
  useRoomContext,
  useConnectionState,
} from "@livekit/components-react";
import { ConnectionState } from "livekit-client";
import "@livekit/components-styles";
import { 
  Mic, LayoutDashboard, LineChart, Bot, Megaphone, 
  Search, Plus, User, PhoneCall, TrendingUp, Smile, Radio,
  Filter, Download, Star, ChevronLeft, ChevronRight, X, ChevronDown, Phone, Monitor
} from "lucide-react";

// ─── Types ───────────────────────────────────────────────────────────────────
interface CallLog {
  id: string;
  customer_name: string;
  phone: string;
  policy_type: string;
  date_of_birth: string | null;
  emirates_id: string | null;
  company_name: string | null;
  trade_licence: string | null;
  date: string;
  duration: string;
  rating: string | null;
  status: string;
  transcript: string | null;
  recording_url: string | null;
}

interface FormData {
  policyType: "individual" | "corporate";
  phone: string;
  contactName: string;
  dateOfBirth: string;
  emiratesId: string;
  companyName: string;
  tradeLicence: string;
  elevenlabsApiKey: string;
  ttsProvider: string;
}

// ─── Mock Data ────────────────────────────────────────────────────────────────
const STATUS_STYLES: Record<string, string> = {
  Completed: "bg-emerald-100 text-emerald-700",
  completed: "bg-emerald-100 text-emerald-700",
  Escalated: "bg-rose-100 text-rose-700",
  "No Answer": "bg-slate-100 text-slate-600",
  "Callback Requested": "bg-amber-100 text-amber-700",
};

// ─── Avatar Helper ────────────────────────────────────────────────────────────
const AVATAR_COLORS = ["bg-blue-200 text-blue-700", "bg-purple-200 text-purple-700", "bg-emerald-200 text-emerald-700", "bg-amber-200 text-amber-700", "bg-rose-200 text-rose-700"];
function Avatar({ name, idx }: { name: string | null; idx: number }) {
  const safeName = name || "Unknown";
  const initials = safeName.split(" ").slice(0, 2).map(w => w[0] || "").join("").toUpperCase();
  return (
    <div className={`w-8 h-8 rounded-full flex items-center justify-center text-xs font-bold flex-shrink-0 ${AVATAR_COLORS[idx % AVATAR_COLORS.length]}`}>
      {initials}
    </div>
  );
}

// ─── Live Call Modal ──────────────────────────────────────────────────────────
function LiveCallModal({ token, onEnd }: { token: string; onEnd: () => void }) {
  const url = process.env.NEXT_PUBLIC_LIVEKIT_URL || "ws://127.0.0.1:7880";
  return (
    <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-50">
      <div className="bg-white rounded-3xl p-8 w-full max-w-md shadow-2xl flex flex-col items-center">
        <div className="flex items-center gap-3 mb-2">
          <div className="w-2.5 h-2.5 rounded-full bg-emerald-500 animate-pulse" />
          <span className="text-sm font-semibold text-slate-500 uppercase tracking-widest">Live Call</span>
        </div>
        <h2 className="text-2xl font-bold text-slate-900 mb-1">Aisha is calling…</h2>
        <p className="text-slate-400 text-sm mb-8">AI Voice Agent is active</p>

        <LiveKitRoom
          token={token}
          serverUrl={url}
          connect={true}
          audio={false}
          video={false}
          className="w-full flex flex-col items-center"
        >
          <RoomAudioRenderer />
          <CallStatusPanel onEnd={onEnd} />
          <button
            onClick={onEnd}
            className="mt-6 w-full py-3 bg-rose-500 hover:bg-rose-600 text-white font-semibold rounded-2xl transition-colors"
          >
            End Call
          </button>
        </LiveKitRoom>
      </div>
    </div>
  );
}

// ─── CallStatusPanel — single component for spectators ────────────────────────
function CallStatusPanel({ onEnd }: { onEnd: () => void }) {
  const participants = useRemoteParticipants();
  const connectionState = useConnectionState();
  const transcriptions = useTranscriptions();
  const [phoneEverJoined, setPhoneEverJoined] = useState(false);
  const [callStatus, setCallStatus] = useState<"waiting" | "ringing" | "active" | "ended">("waiting");
  const [messages, setMessages] = useState<{ id: string; text: string; isAgent: boolean }[]>([]);
  const bottomRef = useRef<HTMLDivElement>(null);

  // Participant presence → call status
  useEffect(() => {
    // If the spectator is currently reconnecting or disconnected, DO NOT trigger the close logic!
    if (connectionState !== ConnectionState.Connected) {
      return;
    }

    const hasPhone = participants.some(p => p.identity.startsWith("phone_"));
    const hasAgent = participants.some(
      p => !p.identity.startsWith("phone_") &&
           !p.identity.toLowerCase().includes("spectator") &&
           !p.identity.toLowerCase().includes("operator") &&
           !p.identity.toLowerCase().includes("dashboard")
    );

    let timeoutId: NodeJS.Timeout;

    if (hasPhone) {
      setPhoneEverJoined(true);
      setCallStatus("active");
    } else if (hasAgent && !hasPhone) {
      if (phoneEverJoined) {
        setCallStatus("ended");
        timeoutId = setTimeout(() => onEnd(), 3000);
      } else {
        setCallStatus("ringing");
      }
    } else if (!hasAgent && !hasPhone) {
      if (phoneEverJoined) {
        setCallStatus("ended");
        timeoutId = setTimeout(() => onEnd(), 3000);
      }
    }

    return () => {
      if (timeoutId) clearTimeout(timeoutId);
    };
  }, [participants, phoneEverJoined, connectionState, onEnd]);

  // Transcriptions
  useEffect(() => {
    setMessages(prev => {
      const next = [...prev];
      let changed = false;
      transcriptions.forEach(t => {
        const tAny = t as any;
        if (!tAny.text?.trim()) return;
        const isAgent = !(
          tAny.participant?.name === "Customer Phone" ||
          tAny.participant?.identity?.startsWith("phone_") ||
          tAny.segment?.participant?.identity?.startsWith("phone_")
        );
        const existing = next.findIndex(m => m.id === tAny.id);
        if (existing >= 0) {
          if (next[existing].text !== tAny.text) { next[existing].text = tAny.text; changed = true; }
        } else {
          next.push({ id: tAny.id, text: tAny.text, isAgent }); changed = true;
        }
      });
      return changed ? next : prev;
    });
  }, [transcriptions]);

  useEffect(() => { bottomRef.current?.scrollIntoView({ behavior: "smooth" }); }, [messages]);

  const statusConfig = {
    waiting: { label: "Connecting…",    dot: "bg-slate-300",                 },
    ringing: { label: "Ringing Phone…", dot: "bg-amber-400 animate-pulse",   },
    active:  { label: "Call Active",    dot: "bg-emerald-500 animate-pulse", },
    ended:   { label: "Call Ended",     dot: "bg-rose-400",                  },
  };
  const cfg = statusConfig[callStatus];

  return (
    <div className="w-full flex flex-col items-center gap-3">
      <div className="flex items-center gap-2 bg-slate-50 border border-slate-200 px-4 py-1.5 rounded-full">
        <div className={`w-2 h-2 rounded-full ${cfg.dot}`} />
        <span className="text-xs font-semibold text-slate-500 uppercase tracking-widest">{cfg.label}</span>
      </div>
      <p className="text-xs text-slate-400">
        {participants.length > 0
          ? `${participants.length} participant${participants.length !== 1 ? "s" : ""} in room`
          : "Waiting for call to connect…"}
      </p>
      <div className="flex items-end gap-1 h-12 w-36">
        {[...Array(7)].map((_, i) => (
          <div
            key={i}
            className={`flex-1 rounded-sm ${
              callStatus === "active" ? "bg-emerald-500" : "bg-slate-200"
            }`}
            style={{
              height: callStatus === "active" ? `${30 + ((i * 17 + Date.now() / 200) % 60)}%` : "20%",
              transition: "height 0.3s ease",
            }}
          />
        ))}
      </div>
      {messages.length > 0 ? (
        <div className="w-full max-h-40 overflow-y-auto flex flex-col gap-2 mt-2 pr-1">
          {messages.slice(-6).map((m, i) => (
            <div key={`${m.id}-${i}`} className={`flex ${m.isAgent ? "justify-start" : "justify-end"}`}>
              <div className={`px-3 py-2 rounded-xl text-xs max-w-[85%] ${
                m.isAgent ? "bg-slate-100 text-slate-700" : "bg-emerald-50 border border-emerald-200 text-slate-700"
              }`}>
                <span className={`block text-[10px] font-bold mb-0.5 ${
                  m.isAgent ? "text-emerald-600" : "text-slate-400"
                }`}>{m.isAgent ? "AISHA" : "CUSTOMER"}</span>
                {m.text}
              </div>
            </div>
          ))}
          <div ref={bottomRef} />
        </div>
      ) : (
        <p className="text-xs text-slate-400 italic mt-2">Conversation transcript will appear here…</p>
      )}
    </div>
  );
}


// ─── Quick Contact Type ───────────────────────────────────────────────────────
interface QuickContact {
  name: string;
  phone: string;
  policyType: "individual" | "corporate";
  dateOfBirth: string;
  emiratesId: string;
  companyName: string;
  tradeLicence: string;
}

// ─── Quick Contact Data ───────────────────────────────────────────────────────
const DEMO_CONTACT: QuickContact = {
  name: "Ahmed Al Mansoori",
  phone: "+918793296687",
  policyType: "individual",
  dateOfBirth: "1990-02-03",
  emiratesId: "5678",
  companyName: "",
  tradeLicence: "",
};

// ─── Quick Call TTS Modal ─────────────────────────────────────────────────────
function QuickCallModal({ contact, onClose, onCallStart }: {
  contact: QuickContact;
  onClose: () => void;
  onCallStart: (token: string) => void;
}) {
  const [ttsProvider, setTtsProvider] = useState("elevenlabs");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function handleQuickCall() {
    setLoading(true); setError("");
    try {
      const roomName = `dni-outbound-${Date.now()}`;
      const metadata = {
        customer_name: contact.name,
        policy_type: contact.policyType,
        date_of_birth: contact.dateOfBirth,
        emirates_id: contact.emiratesId,
        company_name: contact.companyName,
        trade_licence: contact.tradeLicence,
        phone: contact.phone,
        tts_provider: ttsProvider,
      };
      const res = await fetch("/api/token", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ roomName, participantName: "Operator", metadata }),
      });
      const data = await res.json();
      if (data.token) { onClose(); onCallStart(data.token); }
      else { setError(data.error || "Failed to start call."); }
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Unknown error");
    }
    setLoading(false);
  }

  async function handleDialPhone() {
    setLoading(true);
    setError("");
    try {
      // 1. Tell FastAPI to dial Twilio
      const dialRes = await fetch(`${process.env.NEXT_PUBLIC_API_URL || "http://localhost:5000"}/api/dial`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          phone_number: contact.phone,
          customer_name: contact.name,
          policy_type: contact.policyType || "individual"
        })
      });
      const dialData = await dialRes.json();
      if (!dialRes.ok) throw new Error(dialData.detail || "Twilio Dial Failed");
      
      const roomName = dialData.room_name;
      
      // 2. Generate a token to spectate the LiveKit room
      const tokenRes = await fetch("/api/token", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ roomName, participantName: "Dashboard Spectator", metadata: {} }),
      });
      const tokenData = await tokenRes.json();
      if (tokenData.token) { onClose(); onCallStart(tokenData.token); }
      else { setError(tokenData.error || "Failed to start room."); }
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Unknown error");
    }
    setLoading(false);
  }

  return (
    <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-[60] p-4">
      <div className="bg-white rounded-3xl w-full max-w-sm shadow-2xl overflow-hidden">
        <div className="px-7 pt-7 pb-2">
          <div className="flex items-center justify-between mb-1">
            <h2 className="text-xl font-bold text-slate-900">Quick Call</h2>
            <button onClick={onClose} className="w-8 h-8 rounded-full bg-slate-100 hover:bg-slate-200 flex items-center justify-center text-slate-500 transition-colors">
              <X size={16} />
            </button>
          </div>
          <p className="text-sm text-slate-500 mb-4">Calling <span className="font-semibold text-slate-700">{contact.name}</span></p>
        </div>
        <div className="px-7 pb-7 space-y-4">
          {/* TTS Provider */}
          <div>
            <label className="text-xs font-semibold text-slate-500 uppercase tracking-wider block mb-2">Select Voice</label>
            <div className="grid grid-cols-2 gap-2">
              <button
                onClick={() => setTtsProvider("elevenlabs")}
                className={`py-3 rounded-xl border-2 text-sm font-semibold transition-all ${
                  ttsProvider === "elevenlabs"
                    ? "border-emerald-500 bg-emerald-50 text-emerald-700"
                    : "border-slate-200 text-slate-500 hover:border-slate-300"
                }`}
              >
                🎙 ElevenLabs
              </button>
              <button
                onClick={() => setTtsProvider("sarvam")}
                className={`py-3 rounded-xl border-2 text-sm font-semibold transition-all ${
                  ttsProvider === "sarvam"
                    ? "border-emerald-500 bg-emerald-50 text-emerald-700"
                    : "border-slate-200 text-slate-500 hover:border-slate-300"
                }`}
              >
                🎙 Sarvam
              </button>
            </div>
          </div>
          {error && <p className="text-sm text-rose-500">{error}</p>}
          <div className="grid grid-cols-2 gap-2">
            <button
              onClick={handleQuickCall}
              disabled={loading}
              className="py-3 bg-slate-900 hover:bg-slate-700 text-white font-bold rounded-2xl transition-colors flex items-center justify-center gap-2 disabled:opacity-60"
            >
              <Monitor size={18} /> {loading ? "..." : "Web Call"}
            </button>
            <button
              onClick={handleDialPhone}
              disabled={loading || !contact.phone}
              className="py-3 bg-emerald-600 hover:bg-emerald-700 text-white font-bold rounded-2xl transition-colors flex items-center justify-center gap-2 disabled:opacity-60"
            >
              <Phone size={18} /> {loading ? "..." : "Dial Phone"}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

// ─── New Call Form Modal ──────────────────────────────────────────────────────
function NewCallModal({ onClose, onCallStart }: { onClose: () => void; onCallStart: (token: string) => void }) {
  const [form, setForm] = useState<FormData>({ policyType: "individual", phone: "", contactName: "", dateOfBirth: "", emiratesId: "", companyName: "", tradeLicence: "", ttsProvider: "elevenlabs", elevenlabsApiKey: "" });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const update = (k: keyof FormData, v: string) => setForm(f => ({ ...f, [k]: v }));

  async function handleCall() {
    if (!form.phone || !form.contactName) { setError("Phone number and contact name are required."); return; }
    setLoading(true); setError("");
    try {
      const roomName = `dni-outbound-${Date.now()}`;
      const metadata = {
        customer_name: form.contactName,
        policy_type: form.policyType,
        date_of_birth: form.dateOfBirth,
        emirates_id: form.emiratesId,
        company_name: form.companyName,
        trade_licence: form.tradeLicence,
        phone: form.phone,
        tts_provider: form.ttsProvider,
      };
      const res = await fetch("/api/token", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ roomName, participantName: "Operator", metadata }),
      });
      const data = await res.json();
      if (data.token) { onClose(); onCallStart(data.token); }
      else { setError(data.error || "Failed to start call."); }
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Unknown error");
    }
    setLoading(false);
  }

  return (
    <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-3xl w-full max-w-lg shadow-2xl overflow-hidden">
        {/* Header */}
        <div className="px-8 pt-8 pb-4">
          <div className="flex items-center justify-between mb-1">
            <h2 className="text-2xl font-bold text-slate-900">Initialize Voice Interaction</h2>
            <button onClick={onClose} className="w-8 h-8 rounded-full bg-slate-100 hover:bg-slate-200 flex items-center justify-center text-slate-500 transition-colors">
              <X size={16} />
            </button>
          </div>
          <p className="text-sm text-sky-500">Enter client details to authorize the AI voice agent for the outbound communication protocol.</p>
        </div>

        <div className="px-8 pb-8 space-y-4">
          {/* Policy Type */}
          <div>
            <label className="text-xs font-semibold text-slate-500 uppercase tracking-wider block mb-1.5">Policy Type</label>
            <div className="relative">
              <select value={form.policyType} onChange={e => update("policyType", e.target.value as "individual" | "corporate")} className="w-full border border-slate-200 rounded-xl px-4 py-3 pr-10 text-slate-800 font-medium appearance-none focus:outline-none focus:ring-2 focus:ring-emerald-400 bg-white">
                <option value="individual">Individual</option>
                <option value="corporate">Corporate</option>
              </select>
              <div className="pointer-events-none absolute right-3 top-1/2 -translate-y-1/2 text-slate-400">
                <ChevronDown size={16} />
              </div>
            </div>
          </div>

          {/* Phone + Contact Name */}
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="text-xs font-semibold text-slate-500 uppercase tracking-wider block mb-1.5">Phone Number</label>
              <div className="flex border border-slate-200 rounded-xl overflow-hidden focus-within:ring-2 focus-within:ring-emerald-400">
                <span className="px-3 py-3 bg-slate-50 text-slate-600 font-medium text-sm border-r border-slate-200">+971</span>
                <input type="tel" placeholder="50 000 0000" value={form.phone} onChange={e => update("phone", e.target.value)} className="flex-1 px-3 py-3 text-slate-800 focus:outline-none" />
              </div>
            </div>
            <div>
              <label className="text-xs font-semibold text-slate-500 uppercase tracking-wider block mb-1.5">Contact Person&apos;s Name</label>
              <input type="text" placeholder="e.g., Ahmed Ali" value={form.contactName} onChange={e => update("contactName", e.target.value)} className="w-full border border-slate-200 rounded-xl px-4 py-3 text-slate-800 focus:outline-none focus:ring-2 focus:ring-emerald-400" />
            </div>
          </div>

          {/* Individual fields */}
          {form.policyType === "individual" && (
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="text-xs font-semibold text-slate-500 uppercase tracking-wider block mb-1.5">Date of Birth</label>
                <input type="date" value={form.dateOfBirth} onChange={e => update("dateOfBirth", e.target.value)} className="w-full border border-slate-200 rounded-xl px-4 py-3 text-slate-800 focus:outline-none focus:ring-2 focus:ring-emerald-400" />
              </div>
              <div>
                <label className="text-xs font-semibold text-slate-500 uppercase tracking-wider block mb-1.5">Emirates ID (Last 4 Digits)</label>
                <input type="text" placeholder="0000" maxLength={4} value={form.emiratesId} onChange={e => update("emiratesId", e.target.value)} className="w-full border border-slate-200 rounded-xl px-4 py-3 text-slate-800 focus:outline-none focus:ring-2 focus:ring-emerald-400" />
              </div>
            </div>
          )}

          {/* Corporate fields */}
          {form.policyType === "corporate" && (
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="text-xs font-semibold text-slate-500 uppercase tracking-wider block mb-1.5">Company Name</label>
                <input type="text" placeholder="e.g., ABC LLC" value={form.companyName} onChange={e => update("companyName", e.target.value)} className="w-full border border-slate-200 rounded-xl px-4 py-3 text-slate-800 focus:outline-none focus:ring-2 focus:ring-emerald-400" />
              </div>
              <div>
                <label className="text-xs font-semibold text-slate-500 uppercase tracking-wider block mb-1.5">Trade Licence (Last 4 Digits)</label>
                <input type="text" placeholder="0000" maxLength={4} value={form.tradeLicence} onChange={e => update("tradeLicence", e.target.value)} className="w-full border border-slate-200 rounded-xl px-4 py-3 text-slate-800 focus:outline-none focus:ring-2 focus:ring-emerald-400" />
              </div>
            </div>
          )}

          {/* TTS Provider */}
          <div>
            <label className="text-xs font-semibold text-slate-500 uppercase tracking-wider block mb-1.5">Select Provider</label>
            <div className="relative">
              <select value={form.ttsProvider} onChange={e => update("ttsProvider", e.target.value)} className="w-full border border-slate-200 rounded-xl px-4 py-3 pr-10 text-slate-800 font-medium appearance-none focus:outline-none focus:ring-2 focus:ring-emerald-400 bg-white">
                <option value="elevenlabs">ElevenLabs (Archana Voice)</option>
                <option value="sarvam">Sarvam (Simran)</option>
              </select>
              <div className="pointer-events-none absolute right-3 top-1/2 -translate-y-1/2 text-slate-400">
                <ChevronDown size={16} />
              </div>
            </div>
          </div>

          {error && <p className="text-sm text-rose-500">{error}</p>}

          <button onClick={handleCall} disabled={loading} className="w-full py-4 bg-slate-900 hover:bg-slate-700 text-white font-bold rounded-2xl transition-colors flex items-center justify-center gap-2 text-base disabled:opacity-60">
            <Phone size={20} /> {loading ? "Connecting…" : "CALL NOW"}
          </button>
        </div>
      </div>
    </div>
  );
}

// ─── Main Dashboard Page ──────────────────────────────────────────────────────
export default function Home() {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [showNewCall, setShowNewCall] = useState(false);
  const [liveToken, setLiveToken] = useState<string | null>(null);
  const [calls, setCalls] = useState<CallLog[]>([]);
  const [activeNav, setActiveNav] = useState("Dashboard");
  const [selectedCall, setSelectedCall] = useState<CallLog | null>(null);
  const [quickCallContact, setQuickCallContact] = useState<QuickContact | null>(null);

  const fetchCalls = async () => {
    try {
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/calls`);
      if (res.ok) {
        const data = await res.json();
        if (Array.isArray(data)) {
          const formattedCalls = data.map((call: any) => ({
            id: String(call.call_id || `#CAL-${call.id}`),
            customer_name: call.customer_name ? String(call.customer_name) : "Unknown",
            phone: String(call.phone_number || ""),
            policy_type: String(call.policy_type || "individual"),
            date_of_birth: call.date_of_birth ? String(call.date_of_birth) : null,
            emirates_id: call.emirates_id ? String(call.emirates_id) : null,
            company_name: call.company_name ? String(call.company_name) : null,
            trade_licence: call.trade_licence ? String(call.trade_licence) : null,
            date: new Date(call.start_time).toLocaleDateString(),
            duration: call.duration_seconds 
              ? `${Math.floor(Number(call.duration_seconds) / 60)}:${(Number(call.duration_seconds) % 60).toString().padStart(2, '0')}` 
              : "0:00",
            rating: call.rating ? `${String(call.rating)}/10` : null,
            status: String(call.status || "Completed"),
            transcript: call.transcript ? String(call.transcript) : null,
            recording_url: call.recording_url ? String(call.recording_url) : null,
          }));
          setCalls(formattedCalls);
        } else {
          console.error("API did not return an array of calls:", data);
        }
      }
    } catch (err) {
      console.error("Failed to fetch calls:", err);
    }
  };

  useEffect(() => {
    fetchCalls();
    const interval = setInterval(fetchCalls, 3000); // refresh every 3 seconds
    return () => clearInterval(interval);
  }, []);

  const navItems = [
    { name: "Dashboard", icon: <LayoutDashboard size={20} /> },
  ];
  const totalCalls = calls.length;
  const completedCalls = calls.filter(c => c.status.toLowerCase() === "completed").length;
  const completionRate = totalCalls > 0 ? ((completedCalls / totalCalls) * 100).toFixed(1) : "0.0";
  
  const ratedCalls = calls.filter(c => c.rating);
  const avgSentiment = ratedCalls.length > 0 
    ? (ratedCalls.reduce((sum, c) => sum + parseFloat(c.rating!.split('/')[0]), 0) / ratedCalls.length).toFixed(1)
    : "0.0";
  const sentimentPercent = ratedCalls.length > 0 ? (parseFloat(avgSentiment) / 10) * 100 : 0;

  const stats: { label: string; value: string; sub: string; icon: any; hasBar?: boolean; barWidth?: number }[] = [
    { label: "Total Calls", value: totalCalls.toString(), sub: "Real-time volume", icon: <PhoneCall size={24} className="text-slate-400" /> },
    { label: "Completion Rate", value: `${completionRate}%`, sub: `${completedCalls} successful calls`, icon: <TrendingUp size={24} className="text-slate-400" /> },
    { label: "Active Campaigns", value: "1", sub: "● DNI Outbound Protocol", icon: <Radio size={24} className="text-slate-400" /> },
  ];

  if (!isAuthenticated) {
    return <LoginScreen onLogin={() => setIsAuthenticated(true)} />;
  }

  return (
    <>
    {quickCallContact && (
      <QuickCallModal
        contact={quickCallContact}
        onClose={() => setQuickCallContact(null)}
        onCallStart={(token) => setLiveToken(token)}
      />
    )}
    <div className="min-h-screen bg-[#F4F5F7] font-sans flex">
      {/* Sidebar */}
      <aside className="w-52 bg-white border-r border-slate-100 flex flex-col py-6 px-4 flex-shrink-0">
        <div className="flex items-center gap-2 px-2 mb-10">
          <Mic className="text-emerald-500" size={28} />
          <span className="text-xl font-bold text-slate-900">Aisha CRM</span>
        </div>
        <nav className="flex flex-col gap-1 flex-1">
          {navItems.map(item => (
            <button key={item.name} onClick={() => setActiveNav(item.name)}
              className={`flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-medium transition-colors text-left ${activeNav === item.name ? "bg-slate-100 text-slate-900" : "text-slate-500 hover:bg-slate-50 hover:text-slate-700"}`}>
              {item.icon}{item.name}
            </button>
          ))}
        </nav>
        <div className="flex items-center gap-3 px-2 mt-4">
          <div className="w-8 h-8 rounded-full bg-slate-200 flex items-center justify-center text-xs font-bold text-slate-600">JD</div>
          <div>
            <p className="text-xs font-semibold text-slate-800">John Doe</p>
            <p className="text-[10px] text-slate-400">Admin</p>
          </div>
        </div>
      </aside>

      {/* Main */}
      <main className="flex-1 flex flex-col overflow-hidden">
        {/* Topbar */}
        <header className="bg-white border-b border-slate-100 px-8 py-4 flex items-center gap-4">
          <div className="flex items-center gap-2">
            <Mic className="text-emerald-500" size={24} />
            <span className="text-lg font-bold text-slate-900">Aisha Outbound Calling Dashboard</span>
          </div>
          <div className="flex-1" />
          <button onClick={() => setShowNewCall(true)} className="flex items-center gap-2 bg-slate-900 hover:bg-slate-700 text-white font-semibold px-4 py-2.5 rounded-xl transition-colors text-sm">
            <Plus size={18} /> New Call
          </button>
        </header>

        <div className="flex-1 overflow-y-auto p-8 space-y-6">
          {/* Stats row */}
          <div className="grid grid-cols-3 gap-5">
            {stats.map((s, i) => (
              <div key={i} className="bg-white rounded-2xl p-5 shadow-sm border border-slate-100">
                <div className="flex items-center justify-between mb-3">
                  <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider">{s.label}</p>
                  {s.icon}
                </div>
                <p className="text-3xl font-bold text-slate-900 mb-1">{s.value}</p>
                {s.hasBar ? (
                  <div className="h-1.5 bg-slate-100 rounded-full overflow-hidden">
                    <div className="h-full bg-emerald-400 rounded-full transition-all duration-1000" style={{ width: `${s.barWidth || 0}%` }} />
                  </div>
                ) : (
                  <p className="text-xs text-emerald-600 font-medium">{s.sub}</p>
                )}
              </div>
            ))}
          </div>

          {/* Quick Contact Card */}
          <div className="bg-white rounded-2xl p-6 shadow-sm border border-slate-100 flex items-center justify-between">
            <div className="flex items-center gap-4">
              <div className="w-12 h-12 rounded-full bg-emerald-100 flex items-center justify-center text-emerald-600 font-bold text-lg flex-shrink-0">
                AM
              </div>
              <div>
                <p className="text-xs font-semibold text-emerald-500 uppercase tracking-wider mb-0.5">Ready for Outbound</p>
                <h3 className="text-lg font-bold text-slate-900">{DEMO_CONTACT.name}</h3>
                <p className="text-sm text-slate-500">{DEMO_CONTACT.phone} · {DEMO_CONTACT.policyType}</p>
              </div>
            </div>
            <button
              onClick={() => setQuickCallContact(DEMO_CONTACT)}
              className="flex items-center gap-2 bg-emerald-500 hover:bg-emerald-600 text-white font-bold px-6 py-3 rounded-xl transition-colors shadow-sm"
            >
              <Phone size={18} /> Quick Call
            </button>
          </div>

          {/* Call Log Table */}
          <div className="bg-white rounded-2xl shadow-sm border border-slate-100 overflow-hidden">
            <div className="flex items-center justify-between px-6 py-5 border-b border-slate-100">
              <h2 className="text-base font-bold text-slate-900">Recent Call Activity</h2>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full whitespace-nowrap">
              <thead>
                <tr className="border-b border-slate-100">
                  {["Call ID", "Customer Name", "Phone Number", "Policy Type", "DOB / Emirates ID", "Company / Trade Lic.", "Call Date", "Duration", "Service Rating", "Status", ""].map((h, i) => (
                    <th key={i} className="text-left text-[10px] font-bold text-slate-400 uppercase tracking-wider px-6 py-3">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {calls.map((call, i) => (
                  <tr key={call.id} onClick={() => setSelectedCall(call)} className="border-b border-slate-50 hover:bg-slate-50 transition-colors cursor-pointer">
                    <td className="px-6 py-4 text-sm font-semibold text-slate-700">{call.id}</td>
                    <td className="px-6 py-4">
                      <div className="flex items-center gap-2.5">
                        <Avatar name={call.customer_name} idx={i} />
                        <span className="text-sm font-semibold text-slate-800">{call.customer_name}</span>
                      </div>
                    </td>
                    <td className="px-6 py-4 text-sm text-slate-600">{call.phone}</td>
                    <td className="px-6 py-4">
                      <span className="text-xs font-semibold bg-blue-50 text-blue-700 px-2.5 py-1 rounded-lg">{call.policy_type}</span>
                    </td>
                    <td className="px-6 py-4 text-sm text-slate-600">
                      {call.policy_type?.toLowerCase() === "individual" ? (
                        call.date_of_birth || call.emirates_id ? `${call.date_of_birth || '-'} / ${call.emirates_id || '-'}` : "-"
                      ) : "-"}
                    </td>
                    <td className="px-6 py-4 text-sm text-slate-600">
                      {call.policy_type?.toLowerCase() === "corporate" ? (
                        call.company_name || call.trade_licence ? `${call.company_name || '-'} / ${call.trade_licence || '-'}` : "-"
                      ) : "-"}
                    </td>
                    <td className="px-6 py-4 text-sm text-slate-600">{call.date}</td>
                    <td className="px-6 py-4 text-sm text-slate-600">{call.duration}</td>
                    <td className="px-6 py-4 text-sm font-semibold text-slate-700">
                      {call.rating ? (
                        <div className="flex items-center gap-1">
                          <Star size={14} className="text-amber-400 fill-amber-400" />
                          {call.rating}
                        </div>
                      ) : "N/A"}
                    </td>
                    <td className="px-6 py-4">
                      <span className={`text-xs font-semibold px-3 py-1 rounded-lg ${STATUS_STYLES[call.status] || "bg-slate-100 text-slate-700"}`}>
                        {call.status}
                      </span>
                    </td>
                    <td className="px-6 py-4">
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          setQuickCallContact({
                            name: call.customer_name,
                            phone: call.phone,
                            policyType: (call.policy_type?.toLowerCase() === "corporate" ? "corporate" : "individual") as "individual" | "corporate",
                            dateOfBirth: call.date_of_birth || "",
                            emiratesId: call.emirates_id || "",
                            companyName: call.company_name || "",
                            tradeLicence: call.trade_licence || ""
                          });
                        }}
                        className="flex items-center gap-1 bg-emerald-50 text-emerald-600 hover:bg-emerald-500 hover:text-white px-3 py-1.5 rounded-lg text-xs font-bold transition-colors shadow-sm"
                        title="Quick Call"
                      >
                        <Phone size={14} /> Call
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            </div>
            <div className="flex items-center justify-between px-6 py-4 border-t border-slate-100">
              <p className="text-sm text-slate-400">Showing 1–{calls.length} of {calls.length} interactions</p>
              <div className="flex gap-2">
                <button className="w-7 h-7 rounded-lg border border-slate-200 flex items-center justify-center text-slate-400 hover:bg-slate-50">
                  <ChevronLeft size={16} />
                </button>
                <button className="w-7 h-7 rounded-lg border border-slate-200 flex items-center justify-center text-slate-400 hover:bg-slate-50">
                  <ChevronRight size={16} />
                </button>
              </div>
            </div>
          </div>
        </div>
      </main>

      {/* Modals */}
      {showNewCall && (
        <NewCallModal onClose={() => setShowNewCall(false)} onCallStart={(token) => { setLiveToken(token); }} />
      )}
      {liveToken && <LiveCallModal token={liveToken} onEnd={() => setLiveToken(null)} />}
      {selectedCall && <CallDetailsModal call={selectedCall} onClose={() => setSelectedCall(null)} />}
    </div>
    </>
  );
}

// ─── Call Details Modal ───────────────────────────────────────────────────────
function CallDetailsModal({ call, onClose }: { call: CallLog; onClose: () => void }) {
  return (
    <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-3xl w-full max-w-2xl max-h-[85vh] shadow-2xl flex flex-col overflow-hidden">
        {/* Header */}
        <div className="px-8 pt-8 pb-4 border-b border-slate-100 flex items-center justify-between flex-shrink-0">
          <div>
            <div className="flex items-center gap-3 mb-1">
              <h2 className="text-2xl font-bold text-slate-900">{call.customer_name}</h2>
              <span className={`text-xs font-semibold px-2.5 py-0.5 rounded-lg ${STATUS_STYLES[call.status] || "bg-slate-100 text-slate-700"}`}>
                {call.status}
              </span>
            </div>
            <p className="text-sm text-slate-500">Call ID: {call.id} • {call.date} • Duration: {call.duration}</p>
          </div>
          <button onClick={onClose} className="w-8 h-8 rounded-full bg-slate-100 hover:bg-slate-200 flex items-center justify-center text-slate-500 transition-colors">
            <X size={16} />
          </button>
        </div>

        {/* Content */}
        <div className="p-8 overflow-y-auto flex-1 space-y-8">
          
          {/* Audio Player */}
          <div>
            <h3 className="text-sm font-bold text-slate-900 uppercase tracking-wider mb-3 flex items-center gap-2">
              <Mic size={16} className="text-emerald-500" /> Audio Recording
            </h3>
            <div className="bg-slate-50 border border-slate-200 rounded-2xl p-6 flex flex-col items-center justify-center text-center">
              {call.recording_url ? (
                <div className="w-full max-w-md">
                  <p className="text-sm font-medium text-slate-700 mb-4">Playback Call Recording</p>
                  <audio controls className="w-full" src={call.recording_url.startsWith("http") ? call.recording_url : `${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}${call.recording_url}`}>
                    Your browser does not support the audio element.
                  </audio>
                </div>
              ) : (
                <>
                  <div className="w-12 h-12 bg-slate-200 rounded-full flex items-center justify-center mb-3">
                    <PhoneCall size={20} className="text-slate-400" />
                  </div>
                  <p className="text-sm font-medium text-slate-700 mb-1">Recording Not Available</p>
                  <p className="text-xs text-slate-500 max-w-sm">
                    No audio recording found for this call. Egress might not have been active.
                  </p>
                </>
              )}
            </div>
          </div>

          {/* Transcript */}
          <div>
            <h3 className="text-sm font-bold text-slate-900 uppercase tracking-wider mb-3 flex items-center gap-2">
              <Bot size={16} className="text-emerald-500" /> Call Transcript
            </h3>
            <div className="bg-slate-50 border border-slate-200 rounded-2xl p-6 text-sm text-slate-700 font-mono whitespace-pre-wrap leading-relaxed">
              {call.transcript || "No transcript available for this call."}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

// ─── Login Screen ────────────────────────────────────────────────────────────
function LoginScreen({ onLogin }: { onLogin: () => void }) {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");

  const handleLogin = (e: React.FormEvent) => {
    e.preventDefault();
    if (username === "admin" && password === "admin") {
      onLogin();
    } else {
      setError("Invalid username or password");
    }
  };

  return (
    <div className="min-h-screen bg-[#F4F5F7] font-sans flex items-center justify-center p-4">
      <div className="bg-white rounded-3xl p-10 w-full max-w-md shadow-2xl flex flex-col items-center relative">
        <div className="absolute top-4 right-6 text-[10px] font-bold text-slate-300">v1.2 (Crash Shield Active)</div>
        <div className="w-16 h-16 bg-emerald-100 rounded-full flex items-center justify-center mb-6">
          <Mic className="text-emerald-500" size={32} />
        </div>
        <h2 className="text-2xl font-bold text-slate-900 mb-2">Aisha CRM Login</h2>
        <p className="text-slate-500 text-sm mb-8 text-center">Enter your admin credentials to access the voice agent dashboard.</p>
        
        <form onSubmit={handleLogin} className="w-full space-y-4">
          <div>
            <label className="text-xs font-semibold text-slate-500 uppercase tracking-wider block mb-1.5">Username</label>
            <input 
              type="text" 
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              className="w-full border border-slate-200 rounded-xl px-4 py-3 text-slate-800 focus:outline-none focus:ring-2 focus:ring-emerald-400"
              placeholder="admin"
            />
          </div>
          <div>
            <label className="text-xs font-semibold text-slate-500 uppercase tracking-wider block mb-1.5">Password</label>
            <input 
              type="password" 
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full border border-slate-200 rounded-xl px-4 py-3 text-slate-800 focus:outline-none focus:ring-2 focus:ring-emerald-400"
              placeholder="••••••••"
            />
          </div>
          
          {error && <p className="text-sm text-rose-500 font-medium">{error}</p>}
          
          <button type="submit" className="w-full py-4 bg-slate-900 hover:bg-slate-700 text-white font-bold rounded-2xl transition-colors mt-4">
            Sign In
          </button>
        </form>
      </div>
    </div>
  );
}
