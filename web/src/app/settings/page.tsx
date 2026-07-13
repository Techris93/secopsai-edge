"use client";

import { Database, Radar, ShieldCheck, Terminal } from "lucide-react";
import { ApiConnectionPanel } from "@/components/ApiConnectionPanel";
import { AccountManagementPanel } from "@/components/AccountManagementPanel";
import { BaselinePanel } from "@/components/BaselinePanel";
import { CoreIntegrationPanel } from "@/components/CoreIntegrationPanel";
import { CopyCommand } from "@/components/CopyCommand";
import { NotificationPanel } from "@/components/NotificationPanel";
import { PageHeader } from "@/components/PageHeader";
import { SystemHealthPanel } from "@/components/SystemHealthPanel";

const envRows = [
  ["API URL", process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8000"],
  ["Dashboard Auth", "browser session token after Connect"],
  ["AI Provider", "AI_PROVIDER with mock fallback"],
  ["AI Cost Control", "AI_MAX_FINDINGS_PER_REPORT limits report payload size"],
  ["Splunk", "disabled until SPLUNK_HEC_ENABLED=true"]
];

export default function SettingsPage() {
  return (
    <>
      <PageHeader
        eyebrow="Sensor Operations"
        title="Sensor Settings"
        description="Use these operational defaults to run the MacBook MVP safely before packaging it as a Raspberry Pi appliance."
      />

      <div className="grid min-w-0 grid-cols-1 gap-6 xl:grid-cols-[minmax(0,0.8fr)_minmax(0,1.2fr)]">
        <ApiConnectionPanel />
        <SystemHealthPanel />

        <section className="min-w-0 rounded-lg border border-line bg-white p-4 shadow-panel">
          <div className="flex items-center gap-2">
            <ShieldCheck size={20} className="text-sea" aria-hidden="true" />
            <h2 className="text-lg font-semibold text-ink">Safety Controls</h2>
          </div>
          <ul className="mt-4 space-y-3 text-sm text-zinc-700">
            <li className="rounded-md bg-paper p-3">Private IPv4 CIDRs only by default.</li>
            <li className="rounded-md bg-paper p-3">Maximum 4096 addresses per scan.</li>
            <li className="rounded-md bg-paper p-3">Conservative Nmap timing and host timeouts.</li>
            <li className="rounded-md bg-paper p-3">Raw scan output is not sent to AI providers.</li>
          </ul>
        </section>

        <CoreIntegrationPanel />
        <AccountManagementPanel />
        <NotificationPanel />
        <BaselinePanel />

        <section className="rounded-lg border border-line bg-white p-4 shadow-panel xl:col-span-2">
          <div className="flex items-center gap-2">
            <Terminal size={20} className="text-sea" aria-hidden="true" />
            <h2 className="text-lg font-semibold text-ink">Local Commands</h2>
          </div>
          <div className="mt-4 space-y-3">
            <CopyCommand command="./scripts/edge dev" icon={Database} />
            <CopyCommand command="./scripts/edge status --cloud" icon={Radar} />
            <CopyCommand command="./scripts/edge preview 192.168.1.0/24" icon={ShieldCheck} />
            <CopyCommand command="./scripts/edge scan 192.168.1.0/24 --cloud" icon={Terminal} />
          </div>
        </section>
      </div>

      <section className="mt-6 w-full rounded-lg border border-line bg-white shadow-panel">
        <div className="border-b border-line px-4 py-3">
          <h2 className="text-lg font-semibold text-ink">Environment</h2>
        </div>
        <dl className="divide-y divide-line">
          {envRows.map(([label, value]) => (
            <div key={label} className="grid gap-2 px-4 py-3 text-sm sm:grid-cols-[12rem_1fr]">
              <dt className="font-medium text-zinc-600">{label}</dt>
              <dd className="font-mono text-ink">{value}</dd>
            </div>
          ))}
        </dl>
      </section>
    </>
  );
}
