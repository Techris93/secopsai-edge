"use client";

import { Router, ShieldCheck, Wifi } from "lucide-react";
import { useEffect, useState } from "react";
import { DataStatePanel } from "@/components/DataStatePanel";
import { LiveState } from "@/components/LiveState";
import { PageHeader } from "@/components/PageHeader";
import { createWifiBaseline, fetchDashboardData } from "@/lib/api";
import { timeAgo } from "@/lib/format";
import type { DashboardDataMode } from "@/lib/api";
import type { DashboardData } from "@/lib/types";

export default function WifiPage() {
  const [data, setData] = useState<DashboardData | null>(null);
  const [live, setLive] = useState(false);
  const [mode, setMode] = useState<DashboardDataMode>("blocked");
  const [error, setError] = useState<string | undefined>();
  const [site, setSite] = useState("all");
  const [message, setMessage] = useState<string | null>(null);
  const [busyId, setBusyId] = useState<string | null>(null);

  async function load() {
    const result = await fetchDashboardData();
    setData(result.data);
    setLive(result.live);
    setMode(result.mode);
    setError(result.error);
  }

  useEffect(() => {
    void load();
  }, []);

  const networks = (data?.wifiNetworks ?? []).filter((network) => site === "all" || network.site_id === site);

  async function trustBssid(networkId: string) {
    setBusyId(networkId);
    try {
      await createWifiBaseline(networkId, "Approved access point for this site");
      await load();
      setMessage("Access point trusted. Duplicate-SSID alerts for this BSSID are now acknowledged; weak encryption remains visible.");
    } catch (approvalError) {
      setMessage(approvalError instanceof Error ? approvalError.message : "Unable to trust access point");
    } finally {
      setBusyId(null);
    }
  }

  return (
    <>
      <PageHeader
        eyebrow="Wireless"
        title="Wi-Fi Networks"
        description="Track SSIDs, BSSIDs, channels, signal strength, encryption, and rogue access point indicators."
        action={<LiveState live={live} mode={mode} error={error} />}
      />
      <DataStatePanel mode={mode} error={error} />
      {message ? <p className="mb-4 rounded-md border border-line bg-paper px-4 py-3 text-sm text-zinc-700">{message}</p> : null}

      <div className="mb-4 flex justify-end">
        <select
          aria-label="Wi-Fi site"
          className="focus-ring w-full rounded-md border border-line bg-white px-3 py-2 text-sm sm:w-56"
          value={site}
          onChange={(event) => setSite(event.target.value)}
        >
          <option value="all">All sites</option>
          {(data?.sites ?? []).map((item) => (
            <option key={item.id} value={item.id}>{item.name}</option>
          ))}
        </select>
      </div>

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
        {networks.map((network) => {
          const weak = (network.encryption ?? "").toLowerCase().includes("open");
          const trusted = (data?.baselines ?? []).some(
            (rule) => rule.kind === "wifi" && rule.status === "active" && rule.matcher.bssid === network.bssid
          );
          return (
            <section key={network.id} className="rounded-lg border border-line bg-white p-4 shadow-panel">
              <div className="flex items-start justify-between gap-3">
                <div>
                  <h2 className="text-lg font-semibold text-ink">{network.ssid}</h2>
                  <p className="mt-1 font-mono text-xs text-zinc-500">{network.bssid ?? "No BSSID"}</p>
                </div>
                <span className={`rounded-md p-2 ${weak ? "bg-red-50 text-danger" : "bg-teal-50 text-sea"}`}>
                  {weak ? <Router size={20} aria-hidden="true" /> : <Wifi size={20} aria-hidden="true" />}
                </span>
              </div>
              <dl className="mt-4 grid grid-cols-2 gap-3 text-sm">
                <div className="rounded-md bg-paper p-3">
                  <dt className="text-zinc-500">Encryption</dt>
                  <dd className="mt-1 font-medium text-ink">{network.encryption ?? "Unknown"}</dd>
                </div>
                <div className="rounded-md bg-paper p-3">
                  <dt className="text-zinc-500">Channel</dt>
                  <dd className="mt-1 font-medium text-ink">{network.channel ?? "Unknown"}</dd>
                </div>
                <div className="rounded-md bg-paper p-3">
                  <dt className="text-zinc-500">Signal</dt>
                  <dd className="mt-1 font-medium text-ink">
                    {network.signal == null ? "Unknown" : `${network.signal} dBm`}
                  </dd>
                </div>
                <div className="rounded-md bg-paper p-3">
                  <dt className="text-zinc-500">Last Seen</dt>
                  <dd className="mt-1 font-medium text-ink">{timeAgo(network.last_seen_at)}</dd>
                </div>
                <div className="col-span-2 rounded-md bg-paper p-3">
                  <dt className="text-zinc-500">Collection Source</dt>
                  <dd className="mt-1 break-all font-mono text-xs font-medium text-ink">
                    {network.source ?? "unknown"}
                  </dd>
                </div>
              </dl>
              <button
                className="ButtonSecondary mt-4 w-full"
                disabled={!live || !network.bssid || trusted || busyId === network.id}
                onClick={() => void trustBssid(network.id)}
                title="Trust this exact BSSID without suppressing weak-encryption findings"
                type="button"
              >
                <ShieldCheck size={16} aria-hidden="true" />
                {trusted ? "Trusted BSSID" : busyId === network.id ? "Saving..." : "Trust BSSID"}
              </button>
            </section>
          );
        })}
        {data && !networks.length ? (
          <section className="rounded-lg border border-line bg-white px-4 py-8 text-center shadow-panel md:col-span-2 xl:col-span-3">
            <h2 className="text-base font-semibold text-ink">No Wi-Fi networks observed</h2>
            <p className="mt-1 text-sm text-zinc-600">Enable Wi-Fi inventory on a compatible local sensor and run an authorized scan.</p>
          </section>
        ) : null}
      </div>
    </>
  );
}
