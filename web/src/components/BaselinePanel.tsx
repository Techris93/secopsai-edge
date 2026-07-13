"use client";

import { ShieldCheck, Trash2 } from "lucide-react";
import { useEffect, useState } from "react";
import { disableBaseline, fetchBaselines } from "@/lib/api";
import { titleize } from "@/lib/format";
import type { BaselineRule } from "@/lib/types";

export function BaselinePanel() {
  const [rules, setRules] = useState<BaselineRule[]>([]);
  const [message, setMessage] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [busyId, setBusyId] = useState<string | null>(null);

  async function load() {
    setLoading(true);
    try {
      setRules(await fetchBaselines());
      setMessage(null);
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Unable to load approved baselines");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void load();
  }, []);

  async function remove(rule: BaselineRule) {
    setBusyId(rule.id);
    try {
      await disableBaseline(rule.id);
      setRules((current) => current.filter((item) => item.id !== rule.id));
      setMessage("Baseline disabled. Findings acknowledged only by this rule were reopened.");
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Unable to disable baseline");
    } finally {
      setBusyId(null);
    }
  }

  return (
    <section className="rounded-lg border border-line bg-white shadow-panel xl:col-span-2">
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-line px-4 py-3">
        <div className="flex items-center gap-2">
          <ShieldCheck size={20} className="text-sea" aria-hidden="true" />
          <div>
            <h2 className="text-lg font-semibold text-ink">Approved Baselines</h2>
            <p className="mt-1 text-sm text-zinc-600">Known assets, accepted services, and trusted access points.</p>
          </div>
        </div>
        <span className="rounded border border-line bg-paper px-2 py-1 text-xs font-semibold text-zinc-700">
          {rules.length} active
        </span>
      </div>

      {message ? <p className="border-b border-line bg-paper px-4 py-3 text-sm text-zinc-700">{message}</p> : null}

      <div aria-label="Scrollable baseline table" className="focus-ring overflow-x-auto" role="region" tabIndex={0}>
        <table className="w-full min-w-[760px] text-left text-sm">
          <thead className="bg-paper text-xs uppercase text-zinc-600">
            <tr>
              <th className="px-4 py-3">Type</th>
              <th className="px-4 py-3">Identity</th>
              <th className="px-4 py-3">Suppressed findings</th>
              <th className="px-4 py-3">Reason</th>
              <th className="px-4 py-3 text-right">Action</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-line">
            {rules.map((rule) => (
              <tr key={rule.id}>
                <td className="px-4 py-3 font-semibold text-ink">{titleize(rule.kind)}</td>
                <td className="px-4 py-3 font-mono text-xs text-zinc-700">{describeMatcher(rule.matcher)}</td>
                <td className="px-4 py-3 text-zinc-700">{rule.finding_types.map(titleize).join(", ")}</td>
                <td className="max-w-sm px-4 py-3 text-zinc-600">{rule.reason ?? "Approved by operator"}</td>
                <td className="px-4 py-3 text-right">
                  <button
                    className="ButtonDanger"
                    disabled={busyId === rule.id}
                    onClick={() => void remove(rule)}
                    title="Disable this baseline and reopen its acknowledged findings"
                    type="button"
                  >
                    <Trash2 size={16} aria-hidden="true" />
                    {busyId === rule.id ? "Disabling..." : "Disable"}
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {!loading && !rules.length ? (
        <p className="px-4 py-5 text-sm text-zinc-600">No approved baselines yet. Approve them from Asset or Wi-Fi detail views.</p>
      ) : null}
      {loading ? <p className="px-4 py-5 text-sm text-zinc-600">Loading approved baselines...</p> : null}
    </section>
  );
}

function describeMatcher(matcher: BaselineRule["matcher"]): string {
  const preferred = ["ip_address", "mac_address", "bssid", "asset_id", "service_id", "wifi_network_id", "port", "protocol"];
  const entries = preferred
    .filter((key) => matcher[key] !== undefined && matcher[key] !== null)
    .map((key) => `${key}=${String(matcher[key])}`);
  return entries.join("  ") || "Scoped entity";
}
