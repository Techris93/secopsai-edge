import { CheckCircle2, Circle, PlugZap } from "lucide-react";
import type { OnboardingStatus } from "@/lib/types";

const checklist = [
  ["api_connected", "API connected"],
  ["sites_created", "Site created"],
  ["sensor_registered", "Sensor registered"],
  ["worker_online", "Worker online"],
  ["first_scan_completed", "First scan complete"],
  ["first_report_generated", "First report generated"],
  ["schedule_configured", "Schedule configured"],
  ["notifications_configured", "Notifications configured"]
] as const;

export function OnboardingChecklist({ status }: { status: OnboardingStatus | null }) {
  const completed = status
    ? checklist.filter(([key]) => Boolean(status[key])).length
    : 0;

  return (
    <section className="rounded-lg border border-line bg-white p-4 shadow-panel">
      <div className="flex items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          <PlugZap size={20} className="text-sea" aria-hidden="true" />
          <h2 className="text-lg font-semibold text-ink">Pilot Readiness</h2>
        </div>
        <span className="rounded border border-line bg-paper px-2 py-1 text-xs font-semibold text-ink">
          {completed}/{checklist.length}
        </span>
      </div>
      <div className="mt-4 grid gap-2 sm:grid-cols-2">
        {checklist.map(([key, label]) => {
          const done = Boolean(status?.[key]);
          return (
            <div key={key} className="flex items-center gap-2 rounded-md bg-paper px-3 py-2 text-sm">
              {done ? (
                <CheckCircle2 size={16} className="text-sea" aria-hidden="true" />
              ) : (
                <Circle size={16} className="text-zinc-400" aria-hidden="true" />
              )}
              <span className={done ? "font-medium text-ink" : "text-zinc-600"}>{label}</span>
            </div>
          );
        })}
      </div>
    </section>
  );
}
