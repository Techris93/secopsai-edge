"use client";

import { Clipboard, Play, ServerCog } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { LiveState } from "@/components/LiveState";
import { OnboardingChecklist } from "@/components/OnboardingChecklist";
import { PageHeader } from "@/components/PageHeader";
import { apiBaseUrl, fetchDashboardData } from "@/lib/api";
import type { DashboardData } from "@/lib/types";

const EDGE_ROOT = "/Users/chrixchange/Documents/Codex/2026-06-15/i-want-to-build-this-make";

export default function OnboardingPage() {
  const [data, setData] = useState<DashboardData | null>(null);
  const [live, setLive] = useState(false);
  const [error, setError] = useState<string | undefined>();
  const [message, setMessage] = useState<string | null>(null);

  useEffect(() => {
    fetchDashboardData().then((result) => {
      setData(result.data);
      setLive(result.live);
      setError(result.error);
    });
  }, []);

  const commands = useMemo(
    () => [
      {
        label: "Copy Installer",
        value: `cd ${EDGE_ROOT}\n./scripts/install-secopsai-edge.sh --cloud --api-url ${apiBaseUrl()} --admin-token <admin-token> --site-name "Main Office" --sensor-name "MacBook Sensor"`
      },
      {
        label: "Copy Onboard",
        value: `cd ${EDGE_ROOT}\n./scripts/edge onboard --cloud --api-url ${apiBaseUrl()} --install-service --start-service`
      },
      {
        label: "Copy Worker Status",
        value: `cd ${EDGE_ROOT}\n./scripts/edge worker status`
      },
      {
        label: "Copy Worker Logs",
        value: `cd ${EDGE_ROOT}\n./scripts/edge worker logs`
      }
    ],
    []
  );

  async function copyCommand(label: string, value: string) {
    try {
      await navigator.clipboard.writeText(value);
      setMessage(`${label} copied`);
    } catch {
      setMessage("Clipboard unavailable");
    }
  }

  return (
    <>
      <PageHeader
        eyebrow="Pilot Setup"
        title="Onboarding"
        description="Track the steps that make this deployment usable as a real sensor-backed SecOpsAI pilot."
        action={<LiveState live={live} error={error} />}
      />

      <div className="grid gap-6 xl:grid-cols-[0.95fr_1.05fr]">
        <OnboardingChecklist status={data?.onboarding ?? null} />

        <section className="rounded-lg border border-line bg-white p-4 shadow-panel">
          <div className="flex items-center gap-2">
            <ServerCog size={20} className="text-sea" aria-hidden="true" />
            <h2 className="text-lg font-semibold text-ink">Sensor Commands</h2>
          </div>
          <div className="mt-4 grid gap-3">
            {commands.map((command) => (
              <button
                key={command.label}
                className="focus-ring grid min-h-20 rounded-md border border-line bg-paper p-3 text-left transition hover:border-sea hover:bg-white"
                onClick={() => copyCommand(command.label, command.value)}
                type="button"
              >
                <span className="flex items-center gap-2 text-sm font-semibold text-ink">
                  <Clipboard size={16} className="text-sea" aria-hidden="true" />
                  {command.label}
                </span>
                <code className="mt-2 whitespace-pre-wrap break-words font-mono text-xs leading-5 text-zinc-700">
                  {command.value}
                </code>
              </button>
            ))}
          </div>
          {message ? (
            <p className="mt-3 rounded-md bg-emerald-50 px-3 py-2 text-sm font-medium text-emerald-800">
              {message}
            </p>
          ) : null}
        </section>

        <section className="rounded-lg border border-line bg-white p-4 shadow-panel xl:col-span-2">
          <div className="flex items-center gap-2">
            <Play size={20} className="text-sea" aria-hidden="true" />
            <h2 className="text-lg font-semibold text-ink">Current Pilot State</h2>
          </div>
          <div className="mt-4 grid gap-3 md:grid-cols-4">
            <Metric label="Sites" value={data?.sites.length ?? 0} />
            <Metric label="Sensors" value={data?.sensors.length ?? 0} />
            <Metric label="Schedules" value={data?.schedules.length ?? 0} />
            <Metric label="Notifications" value={data?.notifications.length ?? 0} />
          </div>
        </section>
      </div>
    </>
  );
}

function Metric({ label, value }: { label: string; value: number }) {
  return (
    <div className="rounded-md bg-paper p-3">
      <p className="text-sm text-zinc-600">{label}</p>
      <p className="mt-1 text-2xl font-semibold text-ink">{value}</p>
    </div>
  );
}
