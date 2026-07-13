import { AlertTriangle, FlaskConical, Radio } from "lucide-react";
import type { DashboardDataMode } from "@/lib/api";

export function LiveState({
  live,
  mode,
  error
}: {
  live: boolean;
  mode?: DashboardDataMode;
  error?: string;
}) {
  const resolvedMode = mode ?? (live ? "live" : "blocked");
  const state = {
    live: {
      icon: Radio,
      label: "Live API data",
      className: "border-teal-200 bg-teal-50 text-sea"
    },
    demo: {
      icon: FlaskConical,
      label: "Demo data only",
      className: "border-sky-200 bg-sky-50 text-sky-800"
    },
    blocked: {
      icon: AlertTriangle,
      label: "API not connected",
      className: "border-amber-200 bg-amber-50 text-amber"
    }
  }[resolvedMode];
  const Icon = state.icon;

  return (
    <div
      className={`flex items-center gap-2 rounded-md border px-3 py-2 text-sm ${state.className}`}
      title={error}
    >
      <Icon size={16} aria-hidden="true" />
      <span>{state.label}</span>
      {error && resolvedMode !== "live" ? <span className="max-w-56 truncate text-xs opacity-80">{error}</span> : null}
    </div>
  );
}
