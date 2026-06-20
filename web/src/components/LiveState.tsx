import { CloudOff, Radio } from "lucide-react";

export function LiveState({ live, error }: { live: boolean; error?: string }) {
  return (
    <div
      className={`flex items-center gap-2 rounded-md border px-3 py-2 text-sm ${
        live ? "border-teal-200 bg-teal-50 text-sea" : "border-amber-200 bg-amber-50 text-amber"
      }`}
    >
      {live ? <Radio size={16} aria-hidden="true" /> : <CloudOff size={16} aria-hidden="true" />}
      {live ? "Live API data" : `Demo fallback${error ? `: ${error}` : ""}`}
    </div>
  );
}
