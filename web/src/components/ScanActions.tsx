"use client";

import { useMemo, useState } from "react";
import type { ComponentType } from "react";
import { CheckCircle2, Clipboard, FileText, Play, Radar, Wifi } from "lucide-react";
import { createScanJob, generateReport } from "@/lib/api";
import { timeAgo } from "@/lib/format";
import type { ScanJob } from "@/lib/types";

type Props = {
  scanJobs: ScanJob[];
  onChanged: () => Promise<void> | void;
};

export function ScanActions({ scanJobs, onChanged }: Props) {
  const [targetCidr, setTargetCidr] = useState("192.168.1.0/24");
  const [includeWifi, setIncludeWifi] = useState(false);
  const [busyAction, setBusyAction] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  const commands = useMemo(
    () => ({
      preview: `./scripts/edge preview ${targetCidr}`,
      scan: `./scripts/edge scan ${targetCidr} --cloud`,
      worker: "./scripts/edge worker --cloud"
    }),
    [targetCidr]
  );

  const latestJobs = scanJobs.slice(0, 3);

  async function copyCommand(label: string, command: string) {
    setBusyAction(label);
    try {
      await navigator.clipboard.writeText(command);
      setMessage(`${label} copied`);
    } catch {
      setMessage("Clipboard unavailable");
    } finally {
      setBusyAction(null);
    }
  }

  async function queueRemoteScan() {
    setBusyAction("queue");
    try {
      const job = await createScanJob(targetCidr, includeWifi);
      setMessage(`Queued ${job.target_cidr}`);
      await onChanged();
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Unable to queue scan");
    } finally {
      setBusyAction(null);
    }
  }

  async function runReport() {
    setBusyAction("report");
    try {
      await generateReport();
      setMessage("Report generated");
      await onChanged();
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Unable to generate report");
    } finally {
      setBusyAction(null);
    }
  }

  return (
    <section className="rounded-lg border border-line bg-white p-4 shadow-panel">
      <div className="flex items-center gap-2">
        <Radar size={20} className="text-sea" aria-hidden="true" />
        <h2 className="text-lg font-semibold text-ink">Scan Actions</h2>
      </div>

      <div className="mt-4 grid gap-3">
        <label className="grid gap-1 text-sm font-medium text-ink">
          Target CIDR
          <input
            value={targetCidr}
            onChange={(event) => setTargetCidr(event.target.value)}
            className="h-10 rounded-md border border-line bg-paper px-3 text-sm font-normal text-ink outline-none ring-sea/20 transition focus:border-sea focus:ring-4"
            inputMode="text"
            spellCheck={false}
          />
        </label>

        <label className="flex items-center gap-2 text-sm font-medium text-ink">
          <input
            type="checkbox"
            checked={includeWifi}
            onChange={(event) => setIncludeWifi(event.target.checked)}
            className="h-4 w-4 rounded border-line text-sea"
          />
          <Wifi size={16} aria-hidden="true" />
          Include Wi-Fi inventory
        </label>
      </div>

      <div className="mt-4 grid gap-2 sm:grid-cols-2">
        <ActionButton
          icon={Clipboard}
          label="Copy Preview"
          onClick={() => copyCommand("Preview command", commands.preview)}
          disabled={busyAction !== null}
        />
        <ActionButton
          icon={Clipboard}
          label="Copy Cloud Scan"
          onClick={() => copyCommand("Cloud scan command", commands.scan)}
          disabled={busyAction !== null}
        />
        <ActionButton
          icon={Play}
          label="Queue Remote Scan"
          onClick={queueRemoteScan}
          disabled={busyAction !== null}
          tone="primary"
        />
        <ActionButton
          icon={FileText}
          label="Generate Report"
          onClick={runReport}
          disabled={busyAction !== null}
        />
      </div>

      <button
        type="button"
        onClick={() => copyCommand("Worker command", commands.worker)}
        className="mt-3 flex h-10 w-full items-center justify-center gap-2 rounded-md border border-line bg-paper px-3 text-sm font-semibold text-ink transition hover:border-sea hover:text-sea disabled:cursor-wait disabled:opacity-60"
        disabled={busyAction !== null}
      >
        <Clipboard size={16} aria-hidden="true" />
        Copy Worker Command
      </button>

      {message ? (
        <div className="mt-3 flex items-center gap-2 rounded-md bg-emerald-50 px-3 py-2 text-sm font-medium text-emerald-800">
          <CheckCircle2 size={16} aria-hidden="true" />
          {message}
        </div>
      ) : null}

      <div className="mt-4 border-t border-line pt-4">
        <h3 className="text-sm font-semibold text-ink">Remote Jobs</h3>
        {latestJobs.length ? (
          <div className="mt-2 divide-y divide-line rounded-md border border-line">
            {latestJobs.map((job) => (
              <div key={job.id} className="grid grid-cols-[1fr_auto] gap-3 px-3 py-2 text-sm">
                <div>
                  <p className="font-medium text-ink">{job.target_cidr}</p>
                  <p className="text-xs text-zinc-500">{timeAgo(job.created_at)}</p>
                </div>
                <span className="self-center rounded-full bg-paper px-2 py-1 text-xs font-semibold capitalize text-zinc-700">
                  {job.status.replace("_", " ")}
                </span>
              </div>
            ))}
          </div>
        ) : (
          <p className="mt-2 text-sm text-zinc-600">No remote jobs queued.</p>
        )}
      </div>
    </section>
  );
}

type ActionButtonProps = {
  icon: ComponentType<{ size?: number; "aria-hidden"?: boolean }>;
  label: string;
  onClick: () => void;
  disabled?: boolean;
  tone?: "default" | "primary";
};

function ActionButton({ icon: Icon, label, onClick, disabled, tone = "default" }: ActionButtonProps) {
  const className =
    tone === "primary"
      ? "flex h-10 items-center justify-center gap-2 rounded-md bg-sea px-3 text-sm font-semibold text-white transition hover:bg-ink disabled:cursor-wait disabled:opacity-60"
      : "flex h-10 items-center justify-center gap-2 rounded-md border border-line bg-white px-3 text-sm font-semibold text-ink transition hover:border-sea hover:text-sea disabled:cursor-wait disabled:opacity-60";

  return (
    <button type="button" onClick={onClick} disabled={disabled} className={className}>
      <Icon size={16} aria-hidden={true} />
      {label}
    </button>
  );
}
