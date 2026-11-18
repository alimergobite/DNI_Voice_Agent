"use client";

import { useState, useRef } from "react";
import Link from "next/link";
import { 
  ArrowLeft, Download, Eye, EyeOff, Upload, 
  Sparkles, Check, Activity, ChevronRight, RefreshCw
} from "lucide-react";

export default function MedicoPage() {
  const [showOverlay, setShowOverlay] = useState(true);
  const [activeTab, setActiveTab] = useState("Documents");
  const [uploadedImage, setUploadedImage] = useState<string | null>(null);
  const [uploadedFileName, setUploadedFileName] = useState<string>("XR_cervical_spine_lateral.jpg");
  const [uploadedFileSize, setUploadedFileSize] = useState<string>("85 KB");
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [analysisProgress, setAnalysisProgress] = useState(84);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Handle custom X-ray upload
  const handleFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      const reader = new FileReader();
      reader.onload = (event) => {
        setUploadedImage(event.target?.result as string);
        setUploadedFileName(file.name);
        setUploadedFileSize(`${(file.size / 1024).toFixed(0)} KB`);
        setIsAnalyzing(true);
        setAnalysisProgress(30);
        setTimeout(() => setAnalysisProgress(65), 500);
        setTimeout(() => {
          setAnalysisProgress(92);
          setIsAnalyzing(false);
        }, 1100);
      };
      reader.readAsDataURL(file);
    }
  };

  const handleResetToDefault = () => {
    setUploadedImage(null);
    setUploadedFileName("XR_cervical_spine_lateral.jpg");
    setUploadedFileSize("85 KB");
    setAnalysisProgress(84);
    setIsAnalyzing(false);
  };

  return (
    <div className="min-h-screen bg-[#f8fafc] text-slate-800 flex flex-col font-sans">
      {/* Top Bar / Stepper Navigation */}
      <header className="bg-white border-b border-slate-200 sticky top-0 z-40">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 py-2.5 flex flex-wrap items-center justify-between gap-3 text-xs">
          {/* Stepper Workflow */}
          <div className="flex items-center gap-1.5 sm:gap-3 text-slate-500 overflow-x-auto py-1">
            <span className="flex items-center gap-1 font-medium text-slate-600">
              <span className="w-4 h-4 rounded-full bg-slate-100 flex items-center justify-center text-[10px]">1</span> Instruction received
            </span>
            <ChevronRight className="w-3.5 h-3.5 text-slate-300" />
            <span className="flex items-center gap-1 font-medium text-slate-600">
              <span className="w-4 h-4 rounded-full bg-slate-100 flex items-center justify-center text-[10px]">2</span> Expert matched
            </span>
            <ChevronRight className="w-3.5 h-3.5 text-slate-300" />
            <span className="flex items-center gap-1 font-semibold text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded-full border border-emerald-200">
              <span className="w-4 h-4 rounded-full bg-emerald-600 text-white flex items-center justify-center text-[10px]">3</span> Examination & report
            </span>
            <ChevronRight className="w-3.5 h-3.5 text-slate-300" />
            <span className="flex items-center gap-1 text-slate-400">
              <span className="w-4 h-4 rounded-full bg-slate-100 flex items-center justify-center text-[10px]">4</span> Quality review
            </span>
            <ChevronRight className="w-3.5 h-3.5 text-slate-300" />
            <span className="flex items-center gap-1 text-slate-400">
              <span className="w-4 h-4 rounded-full bg-slate-100 flex items-center justify-center text-[10px]">5</span> Report delivered
            </span>
          </div>

          {/* Quick link back to Aisha Voice CRM */}
          <Link 
            href="/"
            className="inline-flex items-center gap-1.5 bg-emerald-600 hover:bg-emerald-700 text-white px-3 py-1.5 rounded-lg text-xs font-semibold shadow-sm transition-all"
          >
            <Activity className="w-3.5 h-3.5" />
            Aisha Outbound CRM
          </Link>
        </div>

        {/* Claim / Medical Review Header */}
        <div className="border-t border-slate-100 bg-white">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 pt-3 pb-2 flex flex-col md:flex-row md:items-center justify-between gap-3">
            <div>
              <div className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider mb-0.5">Ashby Rowe Solicitors</div>
              <h1 className="text-xl sm:text-2xl font-bold text-slate-900 tracking-tight">AI records review</h1>
              <p className="text-xs text-slate-500 mt-0.5">
                Every medical document in the claim, read, summarised and cross-checked — each finding links back to the page it came from.
              </p>
            </div>

            <div className="flex items-center gap-2 flex-wrap">
              <span className="bg-emerald-100 text-emerald-800 font-mono text-[11px] font-semibold px-2.5 py-1 rounded-md border border-emerald-200">
                MR-2026-0418
              </span>
              <span className="bg-slate-100 text-slate-700 text-[11px] font-medium px-2.5 py-1 rounded-md border border-slate-200">
                G. Harper - Road traffic accident
              </span>
              <button 
                onClick={() => alert("Exporting analysis pack with verified radiology annotations...")}
                className="inline-flex items-center gap-1.5 bg-slate-900 hover:bg-slate-800 text-white text-xs font-medium px-3 py-1.5 rounded-md shadow-sm transition-colors"
              >
                <Download className="w-3.5 h-3.5" />
                Export analysis pack
              </button>
            </div>
          </div>

          {/* Tab Navigation */}
          <div className="max-w-7xl mx-auto px-4 sm:px-6 flex items-center gap-2 overflow-x-auto border-t border-slate-100 pt-2 pb-0.5 text-xs font-medium">
            {[
              { id: "Documents", label: "Documents", count: 9 },
              { id: "Chronology", label: "Chronology", count: 13 },
              { id: "Injuries", label: "Injuries", count: 4 },
              { id: "Flags", label: "Flags", count: 6 },
              { id: "Ask", label: "Ask the records" },
              { id: "Questions", label: "Expert questions" },
            ].map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-t-md transition-all whitespace-nowrap ${
                  activeTab === tab.id
                    ? "bg-slate-100 text-slate-900 font-semibold border-b-2 border-emerald-600"
                    : "text-slate-500 hover:text-slate-800 hover:bg-slate-50"
                }`}
              >
                {tab.label}
                {tab.count !== undefined && (
                  <span className={`text-[10px] px-1.5 py-0.2 rounded-full ${
                    activeTab === tab.id ? "bg-slate-200 text-slate-800" : "bg-slate-100 text-slate-500"
                  }`}>
                    {tab.count}
                  </span>
                )}
              </button>
            ))}
          </div>
        </div>
      </header>

      {/* Main Content Area */}
      <main className="max-w-5xl mx-auto w-full px-4 sm:px-6 py-6 flex flex-col gap-6">
        {/* Document Subheader / Viewer Actions */}
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 bg-white p-3.5 rounded-xl border border-slate-200 shadow-xs">
          <div className="flex items-center gap-2.5 flex-wrap">
            <button 
              onClick={() => alert("Returning to full documents index")}
              className="inline-flex items-center gap-1 text-slate-500 hover:text-slate-800 text-xs font-medium cursor-pointer"
            >
              <ArrowLeft className="w-3.5 h-3.5" />
              All documents
            </button>
            <span className="text-slate-300">|</span>
            <span className="bg-purple-100 text-purple-700 text-[10px] font-bold px-1.5 py-0.5 rounded tracking-wide">
              X-RAY
            </span>
            <span className="text-xs font-semibold text-slate-800 font-mono">
              {uploadedFileName}
            </span>
            <span className="text-[11px] text-slate-400">
              {uploadedFileSize} • 1 page
            </span>
          </div>

          <div className="flex items-center gap-2 flex-wrap">
            {/* Toggle Overlay Button */}
            <button
              onClick={() => setShowOverlay(!showOverlay)}
              className={`inline-flex items-center gap-1.5 text-xs font-medium px-3 py-1.5 rounded-lg border transition-all cursor-pointer ${
                showOverlay
                  ? "bg-purple-50 text-purple-700 border-purple-200 hover:bg-purple-100"
                  : "bg-slate-50 text-slate-600 border-slate-200 hover:bg-slate-100"
              }`}
            >
              {showOverlay ? <EyeOff className="w-3.5 h-3.5" /> : <Eye className="w-3.5 h-3.5" />}
              {showOverlay ? "Hide AI overlay" : "Show AI overlay"}
            </button>

            {/* Upload New Scan */}
            <input 
              type="file" 
              ref={fileInputRef} 
              onChange={handleFileUpload} 
              accept="image/*,.pdf" 
              className="hidden" 
            />
            <button
              onClick={() => fileInputRef.current?.click()}
              className="inline-flex items-center gap-1.5 text-xs font-medium bg-slate-100 hover:bg-slate-200 text-slate-700 px-3 py-1.5 rounded-lg border border-slate-200 transition-colors cursor-pointer"
            >
              <Upload className="w-3.5 h-3.5" />
              Upload X-Ray
            </button>

            {uploadedImage && (
              <button
                onClick={handleResetToDefault}
                className="inline-flex items-center gap-1 text-xs font-medium text-slate-500 hover:text-slate-700 px-2 py-1.5"
                title="Reset to demo Cervical Spine scan"
              >
                <RefreshCw className="w-3.5 h-3.5" />
                Reset
              </button>
            )}
          </div>
        </div>

        {/* X-Ray Radiograph Viewer Card */}
        <div className="bg-black rounded-2xl overflow-hidden border border-slate-800 shadow-xl relative flex flex-col items-center justify-center min-h-[460px] sm:min-h-[580px] p-4 select-none">
          {isAnalyzing && (
            <div className="absolute inset-0 bg-black/80 backdrop-blur-xs flex flex-col items-center justify-center z-30 text-white gap-3">
              <div className="w-10 h-10 border-3 border-purple-500 border-t-transparent rounded-full animate-spin"></div>
              <p className="text-sm font-semibold tracking-wide">Vision AI analyzing radiograph structures...</p>
              <span className="text-xs text-purple-300">Detecting fractures, disc spaces, and lordosis alignment</span>
            </div>
          )}

          {uploadedImage ? (
            /* Uploaded Image Mode */
            <div className="relative max-h-[560px] w-full flex items-center justify-center">
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img 
                src={uploadedImage} 
                alt="Uploaded X-Ray" 
                className="max-h-[540px] max-w-full object-contain rounded-lg"
              />
              {showOverlay && !isAnalyzing && (
                <div className="absolute inset-0 pointer-events-none flex items-center justify-center">
                  <div className="relative w-4/5 h-3/5 border-2 border-purple-400/80 rounded-md bg-purple-500/10">
                    <span className="absolute -top-7 left-2 bg-purple-600 text-white text-[11px] font-semibold px-2 py-0.5 rounded shadow">
                      Detected Region: Cortical / Disc Area
                    </span>
                  </div>
                </div>
              )}
            </div>
          ) : (
            /* Synthetic Cervical Spine X-Ray Vector Illustration (Matching Screenshot 2) */
            <div className="relative w-full max-w-lg aspect-[4/5] flex items-center justify-center">
              {/* Watermark Details */}
              <div className="absolute top-2 left-3 text-slate-400 font-mono font-bold text-2xl select-none">
                L
              </div>
              <div className="absolute top-2 right-3 text-slate-400 font-mono font-bold text-lg select-none">
                LAT
              </div>

              {/* Cervical Spine Radiograph Graphic */}
              <svg 
                viewBox="0 0 400 500" 
                className="w-full h-full max-h-[540px] drop-shadow-md"
                xmlns="http://www.w3.org/2000/svg"
              >
                <defs>
                  <radialGradient id="xrayGlow" cx="50%" cy="50%" r="60%">
                    <stop offset="0%" stopColor="#2a3342" stopOpacity="0.4" />
                    <stop offset="100%" stopColor="#0a0d14" stopOpacity="0.9" />
                  </radialGradient>
                  <filter id="softBlur">
                    <feGaussianBlur stdDeviation="1.5" />
                  </filter>
                </defs>

                {/* Soft radiology background haze */}
                <rect width="400" height="500" fill="url(#xrayGlow)" />

                {/* Skull Base / Occiput Radiopacity */}
                <path 
                  d="M 110,60 C 130,20 230,20 260,60 L 220,110 L 120,110 Z" 
                  fill="#7d889b" 
                  opacity="0.6" 
                  filter="url(#softBlur)" 
                />

                {/* Mandible Silhouette */}
                <path 
                  d="M 270,95 L 350,105 L 360,140 L 270,145 Z" 
                  fill="#616f84" 
                  opacity="0.45" 
                  filter="url(#softBlur)" 
                />

                {/* C1 (Atlas) */}
                <rect x="220" y="115" width="36" height="18" rx="4" fill="#a0aec0" opacity="0.85" />
                <path d="M 140,118 L 220,122" stroke="#718096" strokeWidth="6" strokeLinecap="round" opacity="0.5" />

                {/* C2 (Axis & Odontoid Process) */}
                <path d="M 228,138 L 234,120 L 246,120 L 250,138 Z" fill="#b0bccd" opacity="0.9" />
                <rect x="224" y="138" width="38" height="24" rx="4" fill="#b0bccd" opacity="0.9" />
                <path d="M 145,152 L 224,148" stroke="#718096" strokeWidth="8" strokeLinecap="round" opacity="0.5" />

                {/* C3 Vertebra */}
                <rect x="223" y="172" width="39" height="23" rx="3" fill="#cbd5e1" opacity="0.95" />
                <path d="M 148,188 L 223,182" stroke="#718096" strokeWidth="8" strokeLinecap="round" opacity="0.5" />

                {/* C4 Vertebra */}
                <rect x="223" y="205" width="40" height="24" rx="3" fill="#cbd5e1" opacity="0.95" />
                <path d="M 146,224 L 223,215" stroke="#718096" strokeWidth="8" strokeLinecap="round" opacity="0.5" />

                {/* C5 Vertebra */}
                <rect x="222" y="240" width="41" height="24" rx="3" fill="#d1d5db" opacity="0.95" />
                <path d="M 144,260 L 222,250" stroke="#718096" strokeWidth="8" strokeLinecap="round" opacity="0.5" />

                {/* C6 Vertebra (Notice Disc narrowing between C5 and C6) */}
                <rect x="221" y="271" width="42" height="25" rx="3" fill="#cbd5e1" opacity="0.95" />
                {/* Small anterior osteophyte spur */}
                <path d="M 263,271 L 268,274 L 263,277 Z" fill="#e2e8f0" opacity="0.95" />
                <path d="M 140,296 L 221,282" stroke="#718096" strokeWidth="8" strokeLinecap="round" opacity="0.5" />

                {/* C7 Vertebra */}
                <rect x="220" y="306" width="44" height="26" rx="3" fill="#b0bccd" opacity="0.9" />
                <path d="M 134,332 L 220,318" stroke="#718096" strokeWidth="8" strokeLinecap="round" opacity="0.5" />

                {/* Soft Tissue Contour Silhouette */}
                <path 
                  d="M 270,130 C 275,200 275,300 280,360" 
                  stroke="#475569" 
                  strokeWidth="2" 
                  strokeDasharray="4 4" 
                  fill="none" 
                  opacity="0.4" 
                />

                {/* AI Overlays (Toggled) */}
                {showOverlay && (
                  <g className="transition-all duration-300">
                    {/* Straightened Lordosis Indicator Bracket */}
                    <rect 
                      x="256" 
                      y="136" 
                      width="12" 
                      height="198" 
                      fill="none" 
                      stroke="#8b5cf6" 
                      strokeWidth="2" 
                      rx="2"
                      opacity="0.9"
                    />

                    {/* C5/6 Disc Space Narrowing Bounding Box */}
                    <rect 
                      x="214" 
                      y="261" 
                      width="52" 
                      height="14" 
                      fill="rgba(139, 92, 246, 0.2)" 
                      stroke="#8b5cf6" 
                      strokeWidth="2" 
                      rx="2"
                    />
                  </g>
                )}
              </svg>

              {/* Interactive Label Tags Placed over Graphic (Matching Screenshot 2) */}
              {showOverlay && (
                <>
                  {/* Tag 1: C5/6 narrowing + osteophytes */}
                  <div className="absolute top-[52%] left-[54%] transform -translate-y-1/2 bg-purple-600/95 hover:bg-purple-600 text-white font-medium text-[10px] sm:text-[11px] px-2 py-0.5 rounded shadow-lg backdrop-blur-xs flex items-center gap-1 border border-purple-400">
                    <span>C5/6 narrowing + osteophytes</span>
                  </div>

                  {/* Tag 2: Straightened lordosis */}
                  <div className="absolute top-[62%] left-[62%] transform -translate-y-1/2 bg-purple-600/95 hover:bg-purple-600 text-white font-medium text-[10px] sm:text-[11px] px-2 py-0.5 rounded shadow-lg backdrop-blur-xs flex items-center gap-1 border border-purple-400">
                    <span>Straightened lordosis</span>
                  </div>
                </>
              )}

              {/* Bottom Stamp / Synthetic demo notice */}
              <div className="absolute bottom-2 inset-x-0 text-center px-4">
                <span className="text-[10px] text-slate-500 font-mono tracking-wider block">
                  SYNTHETIC DEMO IMAGE
                </span>
                <span className="text-[9px] text-slate-600 font-mono tracking-tight">
                  KGH RADIOLOGY • HARPER, D • KG6473982 • 14/02/2026 09:05 • XR C-SPINE
                </span>
              </div>
            </div>
          )}
        </div>

        {/* AI Extraction Panel (Matching Screenshot 2 Bottom Card) */}
        <div className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden">
          {/* Card Header with Progress Indicator */}
          <div className="p-4 sm:p-5 bg-purple-50/70 border-b border-purple-100 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Sparkles className="w-4 h-4 text-purple-700" />
              <h2 className="text-sm sm:text-base font-bold text-purple-950">
                AI extraction
              </h2>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-24 sm:w-32 bg-purple-200 rounded-full h-2 overflow-hidden">
                <div 
                  className="bg-purple-600 h-2 rounded-full transition-all duration-700" 
                  style={{ width: `${analysisProgress}%` }}
                ></div>
              </div>
              <span className="text-xs font-bold text-purple-800">{analysisProgress}%</span>
            </div>
          </div>

          <div className="p-5 sm:p-6 space-y-6">
            {/* Metadata Grid */}
            <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-4 pb-5 border-b border-slate-100 text-xs">
              <div>
                <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block mb-1">
                  CLASSIFIED AS
                </span>
                <span className="font-semibold text-slate-900 block">
                  Radiograph — cervical spine, lateral
                </span>
              </div>

              <div>
                <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block mb-1">
                  DOCUMENT DATE
                </span>
                <span className="font-medium text-slate-800 block">
                  14 Feb 2026
                </span>
              </div>

              <div>
                <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block mb-1">
                  READ BY
                </span>
                <span className="font-medium text-slate-800 flex items-center gap-1">
                  <Activity className="w-3.5 h-3.5 text-purple-600" />
                  Image analysis
                </span>
              </div>

              <div>
                <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block mb-1">
                  AUTHOR / SOURCE
                </span>
                <span className="font-medium text-slate-800 block">
                  Imaging — Kirkgate Radiology, Kirkgate General Hospital
                </span>
              </div>
            </div>

            {/* Clinical Summary */}
            <div>
              <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block mb-1.5">
                SUMMARY
              </span>
              <p className="text-xs sm:text-sm text-slate-700 leading-relaxed bg-slate-50 p-3.5 rounded-xl border border-slate-100">
                <strong className="text-slate-900 font-semibold">No fracture or malalignment detected.</strong> The cervical lordosis is straightened. Disc-space narrowing at C5/6 with small anterior osteophytes suggests degenerative change that is likely to pre-date the accident. Matches the radiologist&apos;s report (document 5).
              </p>
            </div>

            {/* Detailed Image Observations */}
            <div>
              <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block mb-2">
                IMAGE OBSERVATIONS
              </span>
              <ul className="space-y-1.5 text-xs text-slate-700">
                {[
                  "No cortical break or step in alignment detected",
                  "Loss of normal lordosis (straightened)",
                  "C5/6 disc-space narrowing with anterior osteophytes",
                  "Prevertebral soft tissues not thickened"
                ].map((item, idx) => (
                  <li key={idx} className="flex items-start gap-2">
                    <span className="w-1.5 h-1.5 rounded-full bg-purple-600 mt-1.5 shrink-0"></span>
                    <span>{item}</span>
                  </li>
                ))}
              </ul>
            </div>

            {/* Entities Extracted */}
            <div>
              <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block mb-2">
                ENTITIES
              </span>
              <div className="flex flex-wrap gap-2">
                {[
                  "Straightened lordosis",
                  "C5/6 degenerative change (likely pre-existing)",
                  "XR C-spine lateral"
                ].map((tag, idx) => (
                  <span 
                    key={idx}
                    className="inline-flex items-center gap-1.5 bg-slate-100 hover:bg-slate-200 text-slate-700 text-xs px-2.5 py-1 rounded-md border border-slate-200 font-mono transition-colors"
                  >
                    <Check className="w-3 h-3 text-emerald-600" />
                    {tag}
                  </span>
                ))}
              </div>
            </div>

            {/* Clinical Evidence & Governance Disclaimer */}
            <div className="bg-purple-50/50 border border-purple-100 rounded-xl p-3.5 flex flex-col sm:flex-row sm:items-center justify-between gap-2">
              <div className="text-xs text-purple-950 font-medium">
                &ldquo;AI image observations are a triage aid. The verified radiology report governs.&rdquo;
              </div>
              <span className="text-[10px] font-bold bg-purple-200/80 text-purple-900 px-2 py-0.5 rounded uppercase tracking-wider shrink-0 w-fit">
                Model note
              </span>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}
