import Link from "next/link";
import { AlertTriangle, FlaskConical, Settings } from "lucide-react";
import type { DashboardDataMode } from "@/lib/api";

export function DataStatePanel({ mode, error }: { mode: DashboardDataMode; error?: string }) {
  if (mode === "live") return null;

  if (mode === "demo") {
    return (
      <section className="mb-6 rounded-lg border border-sky-200 bg-sky-50 p-4 text-sky-950">
        <div className="flex items-start gap-3">
          <FlaskConical className="mt-0.5 shrink-0" size={20} aria-hidden="true" />
          <div>
            <h2 className="font-semibold">Demo data only</h2>
            <p className="mt-1 text-sm leading-6">
              This dashboard is showing sample telemetry because demo mode is enabled. Use live API data for customer
              pilots, scans, schedules, reports, and remediation decisions.
            </p>
            {error ? <p className="mt-2 font-mono text-xs opacity-80">{error}</p> : null}
          </div>
        </div>
      </section>
    );
  }

  return (
    <section className="mb-6 rounded-lg border border-amber-200 bg-amber-50 p-4 text-amber-950">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div className="flex items-start gap-3">
          <AlertTriangle className="mt-0.5 shrink-0" size={20} aria-hidden="true" />
          <div>
            <h2 className="font-semibold">API session required</h2>
            <p className="mt-1 text-sm leading-6">
              Connect the dashboard to the SecOpsAI Edge API before using live assets, findings, schedules, sensors, and
              reports.
            </p>
            {error ? <p className="mt-2 font-mono text-xs opacity-80">{error}</p> : null}
          </div>
        </div>
        <Link className="ButtonSecondary shrink-0 bg-white" href="/settings">
          <Settings size={16} aria-hidden="true" />
          Open Settings
        </Link>
      </div>
    </section>
  );
}
