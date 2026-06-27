"use client";

import { useMemo, useState } from "react";
import type { ComponentType } from "react";
import { AlertTriangle, CheckCircle2, Clipboard, FileText, Play, Radar, RotateCcw, Server, Wifi, XCircle } from "lucide-react";
import { cancelScanJob, createScanJob, generateReport, retryScanJob } from "@/lib/api";
import { timeAgo } from "@/lib/format";
import type { ScanJob, Sensor } from "@/lib/types";

type Props = {
  scanJobs: ScanJob[];
  sensors: Sensor[];
  onChanged: () => Promise<void> | void;
};

export function ScanActions({ scanJobs, sensors, onChanged }: Props) {
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

  const latestJobs = scanJobs.slice(0, 5);
  const primarySensor = sensors[0];
  const sensorOnline = primarySensor?.connection_state === "online";

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

  async function cancelJob(jobId: string) {
    setBusyAction(`cancel-${jobId}`);
    try {
      await cancelScanJob(jobId);
      setMessage("Scan job canceled");
      await onChanged();
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Unable to cancel job");
    } finally {
      setBusyAction(null);
    }
  }

  async function retryJob(jobId: string) {
    setBusyAction(`retry-${jobId}`);
    try {
      await retryScanJob(jobId);
      setMessage("Scan job retried");
      await onChanged();
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Unable to retry job");
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

      <div className={`mt-4 rounded-md border px-3 py-3 ${sensorOnline ? "border-emerald-200 bg-emerald-50" : "border-amber-200 bg-amber-50"}`}>
        <div className="flex items-center gap-2">
          <Server size={18} className={sensorOnline ? "text-emerald-700" : "text-amber-700"} aria-hidden="true" />
          <div>
            <p className="text-sm font-semibold text-ink">{primarySensor?.name ?? "No sensor registered"}</p>
            <p className={`text-xs font-semibold ${sensorOnline ? "text-emerald-800" : "text-amber-800"}`}>
              {sensorOnline ? "Sensor online" : "Sensor offline"}
            </p>
          </div>
        </div>
        <p className="mt-2 text-xs text-zinc-600">
          {primarySensor?.last_seen_at ? `Last seen ${timeAgo(primarySensor.last_seen_at)}` : "Start the local worker so dashboard-queued scans can run."}
        </p>
        {!sensorOnline ? (
          <p className="mt-2 rounded bg-white/70 px-2 py-1 font-mono text-xs text-ink">{commands.worker}</p>
        ) : null}
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
        <ActionButton icon={Clipboard} label="Copy Preview" onClick={() => copyCommand("Preview command", commands.preview)} disabled={busyAction !== null} />
        <ActionButton icon={Clipboard} label="Copy Cloud Scan" onClick={() => copyCommand("Cloud scan command", commands.scan)} disabled={busyAction !== null} />
        <ActionButton icon={Play} label="Queue Remote Scan" onClick={queueRemoteScan} disabled={busyAction !== null} tone="primary" />
        <ActionButton icon={FileText} label="Generate Report" onClick={runReport} disabled={busyAction !== null} />
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
              <JobRow key={job.id} job={job} busyAction={busyAction} onCancel={cancelJob} onRetry={retryJob} />
            ))}
          </div>
        ) : (
          <p className="mt-2 text-sm text-zinc-600">No remote jobs queued.</p>
        )}
      </div>
    </section>
  );
}

type JobRowProps = {
  job: ScanJob;
  busyAction: string | null;
  onCancel: (jobId: string) => void;
  onRetry: (jobId: string) => void;
};

function JobRow({ job, busyAction, onCancel, onRetry }: JobRowProps) {
  const assetsSeen = valueFromSummary(job.result_summary, "assets_seen");
  const findingsCreated = valueFromSummary(job.result_summary, "findings_created");
  const canCancel = !["completed", "failed", "canceled"].includes(job.status);
  const canRetry = ["failed", "canceled"].includes(job.status);
  const queuedTooLong = job.status === "queued" && Date.now() - new Date(job.created_at).getTime() > 3 * 60 * 1000;

  return (
    <div className="grid gap-3 px-3 py-3 text-sm">
      <div className="grid grid-cols-[1fr_auto] gap-3">
        <div>
          <p className="font-medium text-ink">{job.target_cidr}</p>
          <p className="text-xs text-zinc-500">Created {timeAgo(job.created_at)}</p>
        </div>
        <span className="self-start rounded-full bg-paper px-2 py-1 text-xs font-semibold capitalize text-zinc-700">
          {job.status.replace("_", " ")}
        </span>
      </div>
      <div className="grid gap-1 text-xs text-zinc-600 sm:grid-cols-2">
        {job.claimed_at ? <span>Claimed {timeAgo(job.claimed_at)}</span> : null}
        {job.started_at ? <span>Started {timeAgo(job.started_at)}</span> : null}
        {job.completed_at ? <span>Completed {timeAgo(job.completed_at)}</span> : null}
        {typeof assetsSeen !== "undefined" ? <span>Assets: {assetsSeen}</span> : null}
        {typeof findingsCreated !== "undefined" ? <span>Findings: {findingsCreated}</span> : null}
      </div>
      {queuedTooLong ? (
        <p className="flex items-center gap-1 rounded bg-amber-50 px-2 py-1 text-xs font-medium text-amber-800">
          <AlertTriangle size={14} aria-hidden="true" /> Worker may not be connected. Start ./scripts/edge worker --cloud.
        </p>
      ) : null}
      {job.error_message ? <p className="rounded bg-red-50 px-2 py-1 text-xs font-medium text-red-800">{job.error_message}</p> : null}
      {(canCancel || canRetry) ? (
        <div className="flex gap-2">
          {canCancel ? <MiniButton icon={XCircle} label="Cancel" onClick={() => onCancel(job.id)} disabled={busyAction !== null} /> : null}
          {canRetry ? <MiniButton icon={RotateCcw} label="Retry" onClick={() => onRetry(job.id)} disabled={busyAction !== null} /> : null}
        </div>
      ) : null}
    </div>
  );
}

function valueFromSummary(summary: Record<string, unknown>, key: string): string | number | undefined {
  const value = summary[key];
  return typeof value === "string" || typeof value === "number" ? value : undefined;
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

type MiniButtonProps = {
  icon: ComponentType<{ size?: number; "aria-hidden"?: boolean }>;
  label: string;
  onClick: () => void;
  disabled?: boolean;
};

function MiniButton({ icon: Icon, label, onClick, disabled }: MiniButtonProps) {
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled}
      className="inline-flex h-8 items-center gap-1 rounded-md border border-line bg-white px-2 text-xs font-semibold text-ink hover:border-sea hover:text-sea disabled:cursor-wait disabled:opacity-60"
    >
      <Icon size={14} aria-hidden={true} />
      {label}
    </button>
  );
}
