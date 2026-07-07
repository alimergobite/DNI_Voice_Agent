"use client";
export default function Error({ error, reset }: { error: Error & { digest?: string }, reset: () => void }) {
  return (
    <div className="min-h-screen flex items-center justify-center bg-slate-50 p-4">
      <div className="bg-white p-8 rounded-2xl shadow-xl max-w-2xl w-full border border-red-100">
        <h2 className="text-red-500 font-bold text-2xl mb-4 flex items-center gap-2">
          ⚠️ Dashboard Crash
        </h2>
        <p className="text-slate-600 mb-6">
          The dashboard encountered an unexpected runtime error. Please screenshot this exact error and send it to the developer.
        </p>
        <div className="bg-slate-900 text-red-400 p-4 rounded-xl overflow-x-auto text-sm font-mono mb-6">
          <p className="font-bold mb-2">{error.name}: {error.message}</p>
          <pre className="text-slate-300 text-xs leading-relaxed">{error.stack}</pre>
        </div>
        <button 
          onClick={() => reset()} 
          className="bg-emerald-500 hover:bg-emerald-600 text-white font-bold px-6 py-3 rounded-xl transition-colors shadow-sm"
        >
          Try Again
        </button>
      </div>
    </div>
  );
}
