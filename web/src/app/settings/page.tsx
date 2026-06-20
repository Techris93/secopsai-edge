import { Copy, Database, KeyRound, Radar, ShieldCheck, Terminal } from "lucide-react";
import { ApiConnectionPanel } from "@/components/ApiConnectionPanel";
import { PageHeader } from "@/components/PageHeader";

const envRows = [
  ["API URL", process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8000"],
  ["Dashboard Auth", "browser session token after Connect"],
  ["AI Provider", "mock or HTTP adapter via API environment"],
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

      <div className="grid gap-6 xl:grid-cols-[0.8fr_1.2fr]">
        <ApiConnectionPanel />

        <section className="rounded-lg border border-line bg-white p-4 shadow-panel">
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

        <section className="rounded-lg border border-line bg-white p-4 shadow-panel xl:col-span-2">
          <div className="flex items-center gap-2">
            <Terminal size={20} className="text-sea" aria-hidden="true" />
            <h2 className="text-lg font-semibold text-ink">Local Commands</h2>
          </div>
          <div className="mt-4 space-y-3">
            <Command text="docker compose -f infra/docker-compose.yml up -d" icon={Database} />
            <Command text="PYTHONPATH=api:agent uvicorn secopsai_api.main:app --reload --host 127.0.0.1 --port 8000" icon={Radar} />
            <Command text="PYTHONPATH=agent python -m secopsai_agent.cli preview 192.168.1.0/24" icon={ShieldCheck} />
            <Command text="PYTHONPATH=agent python -m secopsai_agent.cli submit 192.168.1.0/24 --sensor-id <id> --sensor-token <token>" icon={KeyRound} />
          </div>
        </section>
      </div>

      <section className="mt-6 rounded-lg border border-line bg-white shadow-panel">
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

function Command({ text, icon: Icon }: { text: string; icon: typeof Terminal }) {
  return (
    <div className="flex items-center gap-3 rounded-md bg-ink p-3 text-sm text-white">
      <Icon size={17} className="shrink-0 text-teal-200" aria-hidden="true" />
      <code className="min-w-0 flex-1 overflow-x-auto whitespace-nowrap">{text}</code>
      <Copy size={16} className="shrink-0 text-zinc-300" aria-hidden="true" />
    </div>
  );
}
