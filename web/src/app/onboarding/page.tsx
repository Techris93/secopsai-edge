"use client";

import { Clipboard, Play, RadioTower, ServerCog } from "lucide-react";
import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { DataStatePanel } from "@/components/DataStatePanel";
import { LiveState } from "@/components/LiveState";
import { OnboardingChecklist } from "@/components/OnboardingChecklist";
import { PageHeader } from "@/components/PageHeader";
import { fetchDashboardData } from "@/lib/api";
import type { DashboardDataMode } from "@/lib/api";
import type { DashboardData } from "@/lib/types";

const EDGE_ROOT = process.env.NEXT_PUBLIC_EDGE_ROOT ?? "$HOME/.local/share/secopsai-edge";

export default function OnboardingPage() {
  const [data, setData] = useState<DashboardData | null>(null);
  const [live, setLive] = useState(false);
  const [mode, setMode] = useState<DashboardDataMode>("blocked");
  const [error, setError] = useState<string | undefined>();
  const [message, setMessage] = useState<string | null>(null);

  useEffect(() => {
    fetchDashboardData().then((result) => {
      setData(result.data);
      setLive(result.live);
      setMode(result.mode);
      setError(result.error);
    });
  }, []);

  const commands = useMemo(
    () => [
      {
        label: "Copy Worker Start",
        value: `cd ${EDGE_ROOT}\n./scripts/edge worker start`
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
        action={<LiveState live={live} mode={mode} error={error} />}
      />
      <DataStatePanel mode={mode} error={error} />

      <div className="grid gap-6 xl:grid-cols-[0.95fr_1.05fr]">
        <OnboardingChecklist status={data?.onboarding ?? null} />

        <section className="rounded-lg border border-line bg-white p-4 shadow-panel">
          <div className="flex items-center gap-2">
            <ServerCog size={20} className="text-sea" aria-hidden="true" />
            <h2 className="text-lg font-semibold text-ink">Sensor Commands</h2>
          </div>
          <p className="mt-2 text-sm leading-6 text-zinc-600">
            Create a site-scoped, one-time installer from Sites. No platform administrator token is shared with the sensor operator.
          </p>
          <Link
            href="/sites"
            className="focus-ring mt-4 inline-flex h-10 items-center gap-2 rounded-md bg-sea px-3 text-sm font-semibold text-white hover:bg-ink"
          >
            <RadioTower size={16} aria-hidden={true} />
            Open Sites and enroll sensor
          </Link>
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
