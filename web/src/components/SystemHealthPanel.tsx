"use client";

import { Activity, RefreshCw } from "lucide-react";
import { useEffect, useState } from "react";
import { fetchSystemStatus } from "@/lib/api";
import type { SystemStatus } from "@/lib/types";

export function SystemHealthPanel() {
  const [system, setSystem] = useState<SystemStatus | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function load() {
    setBusy(true);
    setError(null);
    try {
      setSystem(await fetchSystemStatus());
    } catch (reason) {
      setSystem(null);
      setError(reason instanceof Error ? reason.message : "Unable to read system health");
    } finally {
      setBusy(false);
    }
  }

  useEffect(() => { void load(); }, []);

  const rows = system ? [
    ["Environment", system.environment],
    ["Release", system.version],
    ["Commit", system.commit.slice(0, 12)],
    ["Database schema", `${system.schema_revision ?? "missing"}${system.schema_revision === system.expected_schema_revision ? " (current)" : " (upgrade required)"}`],
    ["AI provider", system.ai_provider],
    ["AI report guardrail", `${system.ai_max_findings_per_report} findings; ${system.ai_report_cooldown_seconds}s cooldown`]
  ] : [];

  return (
    <section className="min-w-0 rounded-lg border border-line bg-white p-4 shadow-panel">
      <div className="flex items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          <Activity size={20} className={system?.status === "ready" ? "text-sea" : "text-amber"} aria-hidden="true" />
          <h2 className="text-lg font-semibold text-ink">System Health</h2>
        </div>
        <button className="ButtonSecondary" type="button" disabled={busy} onClick={() => void load()}>
          <RefreshCw size={16} className={busy ? "animate-spin" : ""} aria-hidden="true" />
          Refresh
        </button>
      </div>
      {system ? (
        <>
          <p className={`mt-3 text-sm font-semibold ${system.status === "ready" ? "text-sea" : "text-amber"}`}>
            {system.status === "ready" ? "API and database ready" : "Deployment needs attention"}
          </p>
          <dl className="mt-3 divide-y divide-line text-sm">
            {rows.map(([label, value]) => (
              <div key={label} className="grid gap-1 py-2 sm:grid-cols-[9rem_minmax(0,1fr)]">
                <dt className="text-zinc-500">{label}</dt>
                <dd className="break-all font-mono text-ink">{value}</dd>
              </div>
            ))}
          </dl>
        </>
      ) : (
        <p className="mt-3 rounded-md bg-paper px-3 py-2 text-sm text-zinc-600">
          {error ?? "Connect an API session to inspect deployment health."}
        </p>
      )}
    </section>
  );
}
