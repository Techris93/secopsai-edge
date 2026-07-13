"use client";

import { DatabaseZap, RefreshCw, Save } from "lucide-react";
import { FormEvent, useEffect, useState } from "react";
import {
  fetchDataLifecyclePolicy,
  runDataLifecycle,
  updateDataLifecyclePolicy
} from "@/lib/api";
import { timeAgo } from "@/lib/format";
import type { DataLifecyclePolicy } from "@/lib/types";

const fields: Array<{
  key: keyof Pick<
    DataLifecyclePolicy,
    | "observation_days"
    | "scan_history_days"
    | "notification_delivery_days"
    | "account_access_days"
    | "credential_history_days"
    | "report_days"
    | "audit_log_days"
  >;
  label: string;
  help: string;
  min: number;
  max: number;
}> = [
  { key: "observation_days", label: "Asset observations", help: "Normalized device history", min: 7, max: 3650 },
  { key: "scan_history_days", label: "Scan history", help: "Completed jobs and runs", min: 7, max: 3650 },
  { key: "notification_delivery_days", label: "Delivery history", help: "Completed notification attempts", min: 7, max: 730 },
  { key: "account_access_days", label: "Access tokens", help: "Expired invitation and reset records", min: 1, max: 365 },
  { key: "credential_history_days", label: "Credential history", help: "Expired enrollment and integration records", min: 7, max: 730 },
  { key: "report_days", label: "Reports", help: "Generated report records", min: 30, max: 3650 },
  { key: "audit_log_days", label: "Audit logs", help: "Operator and sensor activity", min: 90, max: 3650 }
];

export function DataLifecyclePanel() {
  const [policy, setPolicy] = useState<DataLifecyclePolicy | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function load() {
    setBusy(true);
    setMessage(null);
    try {
      setPolicy(await fetchDataLifecyclePolicy());
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Unable to load retention policy");
    } finally {
      setBusy(false);
    }
  }

  useEffect(() => { void load(); }, []);

  async function save(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!policy) return;
    setBusy(true);
    try {
      const updated = await updateDataLifecyclePolicy({
        observation_days: policy.observation_days,
        scan_history_days: policy.scan_history_days,
        notification_delivery_days: policy.notification_delivery_days,
        account_access_days: policy.account_access_days,
        credential_history_days: policy.credential_history_days,
        report_days: policy.report_days,
        audit_log_days: policy.audit_log_days
      });
      setPolicy(updated);
      setMessage("Retention policy saved");
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Unable to save retention policy");
    } finally {
      setBusy(false);
    }
  }

  async function runNow() {
    setBusy(true);
    try {
      const result = await runDataLifecycle();
      const removed = Object.values(result.deleted).reduce((total, count) => total + count, 0);
      await load();
      setMessage(`Cleanup complete: ${removed} expired records removed`);
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Unable to run retention cleanup");
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="min-w-0 rounded-lg border border-line bg-white p-4 shadow-panel xl:col-span-2">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div className="flex items-start gap-2">
          <DatabaseZap size={20} className="mt-0.5 text-sea" aria-hidden="true" />
          <div>
            <h2 className="text-lg font-semibold text-ink">Data Lifecycle</h2>
            <p className="mt-1 text-sm text-zinc-600">
              Retain evidence long enough for investigations, then remove expired operational history automatically.
            </p>
          </div>
        </div>
        <button className="ButtonSecondary" type="button" disabled={busy || !policy} onClick={() => void runNow()}>
          <RefreshCw size={16} className={busy ? "animate-spin" : ""} aria-hidden="true" />
          Run cleanup
        </button>
      </div>
      {policy ? (
        <form className="mt-4" onSubmit={save}>
          <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
            {fields.map((field) => (
              <label className="rounded-md border border-line p-3" key={field.key}>
                <span className="block text-sm font-semibold text-ink">{field.label}</span>
                <span className="mt-1 block text-xs text-zinc-500">{field.help}</span>
                <span className="mt-3 flex items-center gap-2">
                  <input
                    aria-label={`${field.label} retention days`}
                    className="focus-ring min-w-0 flex-1 rounded-md border border-line px-3 py-2 text-sm"
                    type="number"
                    min={field.min}
                    max={field.max}
                    value={policy[field.key]}
                    onChange={(event) => setPolicy({ ...policy, [field.key]: Number(event.target.value) })}
                  />
                  <span className="text-xs text-zinc-500">days</span>
                </span>
              </label>
            ))}
          </div>
          <div className="mt-4 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            <p className="text-xs text-zinc-500">
              {policy.last_run_at ? `Last cleanup ${timeAgo(policy.last_run_at)}` : "Cleanup has not run yet"}
            </p>
            <button className="ButtonPrimary" type="submit" disabled={busy}>
              <Save size={16} aria-hidden="true" />
              Save policy
            </button>
          </div>
        </form>
      ) : (
        <p className="mt-4 rounded-md bg-paper px-3 py-2 text-sm text-zinc-600">
          {busy ? "Loading retention policy..." : "Connect an owner or administrator session to manage retention."}
        </p>
      )}
      {message ? <p className="mt-3 rounded-md bg-paper px-3 py-2 text-sm text-ink" role="status">{message}</p> : null}
    </section>
  );
}
