"use client";

import { Search, Server } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { LiveState } from "@/components/LiveState";
import { PageHeader } from "@/components/PageHeader";
import { fetchDashboardData } from "@/lib/api";
import { timeAgo } from "@/lib/format";
import type { Asset, DashboardData } from "@/lib/types";

export default function AssetsPage() {
  const [data, setData] = useState<DashboardData | null>(null);
  const [live, setLive] = useState(false);
  const [error, setError] = useState<string | undefined>();
  const [query, setQuery] = useState("");
  const [status, setStatus] = useState("all");

  useEffect(() => {
    fetchDashboardData().then((result) => {
      setData(result.data);
      setLive(result.live);
      setError(result.error);
    });
  }, []);

  const assets = useMemo(() => filterAssets(data?.assets ?? [], query, status), [data, query, status]);

  return (
    <>
      <PageHeader
        eyebrow="Inventory"
        title="Assets"
        description="Search discovered devices by IP, hostname, vendor, device type, OS guess, and status."
        action={<LiveState live={live} error={error} />}
      />

      <section className="rounded-lg border border-line bg-white shadow-panel">
        <div className="grid gap-3 border-b border-line p-4 md:grid-cols-[1fr_12rem]">
          <label className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-zinc-500" size={18} aria-hidden="true" />
            <input
              className="focus-ring w-full rounded-md border border-line bg-white py-2 pl-10 pr-3 text-sm"
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              placeholder="Search assets"
            />
          </label>
          <select
            className="focus-ring rounded-md border border-line bg-white px-3 py-2 text-sm"
            value={status}
            onChange={(event) => setStatus(event.target.value)}
          >
            <option value="all">All statuses</option>
            <option value="active">Active</option>
            <option value="missing">Missing</option>
          </select>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full min-w-[860px] text-left text-sm">
            <thead className="bg-paper text-xs uppercase text-zinc-600">
              <tr>
                <th className="px-4 py-3">Device</th>
                <th className="px-4 py-3">IP</th>
                <th className="px-4 py-3">Vendor</th>
                <th className="px-4 py-3">Type</th>
                <th className="px-4 py-3">OS</th>
                <th className="px-4 py-3">Status</th>
                <th className="px-4 py-3">Last Seen</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-line">
              {assets.map((asset) => (
                <tr key={asset.id}>
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-2">
                      <Server size={16} className="text-sea" aria-hidden="true" />
                      <span className="font-medium text-ink">{asset.hostname ?? "Unknown device"}</span>
                    </div>
                    <span className="mt-1 block text-xs text-zinc-500">{asset.mac_address ?? "No MAC observed"}</span>
                  </td>
                  <td className="px-4 py-3 font-mono text-sm">{asset.ip_address}</td>
                  <td className="px-4 py-3">{asset.vendor ?? "Unknown"}</td>
                  <td className="px-4 py-3">{asset.device_type ?? "Unclassified"}</td>
                  <td className="px-4 py-3">{asset.os_guess ?? "Unknown"}</td>
                  <td className="px-4 py-3">
                    <span className="rounded border border-line bg-paper px-2 py-1 text-xs font-medium uppercase">
                      {asset.status}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-zinc-600">{timeAgo(asset.last_seen_at)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </>
  );
}

function filterAssets(assets: Asset[], query: string, status: string): Asset[] {
  const normalizedQuery = query.trim().toLowerCase();
  return assets.filter((asset) => {
    const statusMatch = status === "all" || asset.status === status;
    const text = [
      asset.ip_address,
      asset.hostname,
      asset.vendor,
      asset.device_type,
      asset.os_guess,
      asset.mac_address
    ]
      .filter(Boolean)
      .join(" ")
      .toLowerCase();
    return statusMatch && (!normalizedQuery || text.includes(normalizedQuery));
  });
}
