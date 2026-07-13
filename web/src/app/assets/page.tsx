"use client";

import Link from "next/link";
import { Search, Server } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { DataStatePanel } from "@/components/DataStatePanel";
import { LiveState } from "@/components/LiveState";
import { PageHeader } from "@/components/PageHeader";
import { fetchDashboardData } from "@/lib/api";
import { timeAgo } from "@/lib/format";
import type { DashboardDataMode } from "@/lib/api";
import type { Asset, DashboardData } from "@/lib/types";

export default function AssetsPage() {
  const [data, setData] = useState<DashboardData | null>(null);
  const [live, setLive] = useState(false);
  const [mode, setMode] = useState<DashboardDataMode>("blocked");
  const [error, setError] = useState<string | undefined>();
  const [query, setQuery] = useState("");
  const [status, setStatus] = useState("all");
  const [vendor, setVendor] = useState("all");
  const [type, setType] = useState("all");
  const [os, setOs] = useState("all");
  const [service, setService] = useState("all");
  const [site, setSite] = useState("all");

  useEffect(() => {
    fetchDashboardData().then((result) => {
      setData(result.data);
      setLive(result.live);
      setMode(result.mode);
      setError(result.error);
    });
  }, []);

  const options = useMemo(() => buildFilterOptions(data?.assets ?? []), [data]);
  const assets = useMemo(
    () => filterAssets(data?.assets ?? [], { query, status, vendor, type, os, service, site }),
    [data, query, status, vendor, type, os, service, site]
  );

  return (
    <>
      <PageHeader
        eyebrow="Inventory"
        title="Assets"
        description="Search discovered devices by IP, hostname, vendor, device type, OS guess, and status."
        action={<LiveState live={live} mode={mode} error={error} />}
      />
      <DataStatePanel mode={mode} error={error} />

      <section className="rounded-lg border border-line bg-white shadow-panel">
        <div className="grid gap-3 border-b border-line p-4 xl:grid-cols-[1fr_repeat(6,9rem)]">
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
          <select
            aria-label="Site"
            className="focus-ring rounded-md border border-line bg-white px-3 py-2 text-sm"
            value={site}
            onChange={(event) => setSite(event.target.value)}
          >
            <option value="all">All sites</option>
            {(data?.sites ?? []).map((item) => (
              <option key={item.id} value={item.id}>{item.name}</option>
            ))}
          </select>
          <FilterSelect label="Vendor" value={vendor} values={options.vendors} onChange={setVendor} />
          <FilterSelect label="Type" value={type} values={options.types} onChange={setType} />
          <FilterSelect label="OS" value={os} values={options.oses} onChange={setOs} />
          <FilterSelect label="Service" value={service} values={options.services} onChange={setService} />
        </div>
        <div className="overflow-x-auto">
          <table className="w-full min-w-[1120px] text-left text-sm">
            <thead className="bg-paper text-xs uppercase text-zinc-600">
              <tr>
                <th className="px-4 py-3">Device</th>
                <th className="px-4 py-3">IP</th>
                <th className="px-4 py-3">Vendor</th>
                <th className="px-4 py-3">Type</th>
                <th className="px-4 py-3">OS</th>
                <th className="px-4 py-3">Status</th>
                <th className="px-4 py-3">Services</th>
                <th className="px-4 py-3">Last Seen</th>
                <th className="px-4 py-3">Action</th>
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
                  <td className="px-4 py-3">
                    <div className="flex max-w-56 flex-wrap gap-1">
                      {(asset.services ?? []).filter((svc) => svc.state === "open").slice(0, 4).map((svc) => (
                        <span key={svc.id} className="rounded border border-line bg-paper px-2 py-1 font-mono text-xs">
                          {svc.protocol}/{svc.port}
                        </span>
                      ))}
                      {!(asset.services ?? []).some((svc) => svc.state === "open") ? (
                        <span className="text-xs text-zinc-500">None</span>
                      ) : null}
                    </div>
                  </td>
                  <td className="px-4 py-3 text-zinc-600">{timeAgo(asset.last_seen_at)}</td>
                  <td className="px-4 py-3">
                    {live ? (
                      <Link className="ButtonSecondary" href={`/assets/detail?id=${encodeURIComponent(asset.id)}`}>
                        Detail
                      </Link>
                    ) : (
                      <span className="rounded border border-line bg-paper px-3 py-2 text-xs font-semibold text-zinc-500">
                        Detail
                      </span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </>
  );
}

type AssetFilters = {
  query: string;
  status: string;
  vendor: string;
  type: string;
  os: string;
  service: string;
  site: string;
};

function filterAssets(assets: Asset[], filters: AssetFilters): Asset[] {
  const normalizedQuery = filters.query.trim().toLowerCase();
  return assets.filter((asset) => {
    const statusMatch = filters.status === "all" || asset.status === filters.status;
    const vendorMatch = filters.vendor === "all" || (asset.vendor ?? "Unknown") === filters.vendor;
    const typeMatch = filters.type === "all" || (asset.device_type ?? "Unclassified") === filters.type;
    const osMatch = filters.os === "all" || (asset.os_guess ?? "Unknown") === filters.os;
    const serviceMatch =
      filters.service === "all" ||
      (asset.services ?? []).some((svc) => `${svc.protocol}/${svc.port}` === filters.service && svc.state === "open");
    const siteMatch = filters.site === "all" || asset.site_id === filters.site;
    const text = [
      asset.ip_address,
      asset.hostname,
      asset.vendor,
      asset.device_type,
      asset.os_guess,
      asset.mac_address,
      ...(asset.services ?? []).map((svc) => `${svc.protocol}/${svc.port} ${svc.name ?? ""}`)
    ]
      .filter(Boolean)
      .join(" ")
      .toLowerCase();
    return statusMatch && vendorMatch && typeMatch && osMatch && serviceMatch && siteMatch && (!normalizedQuery || text.includes(normalizedQuery));
  });
}

function buildFilterOptions(assets: Asset[]) {
  const vendors = new Set<string>();
  const types = new Set<string>();
  const oses = new Set<string>();
  const services = new Set<string>();
  for (const asset of assets) {
    vendors.add(asset.vendor ?? "Unknown");
    types.add(asset.device_type ?? "Unclassified");
    oses.add(asset.os_guess ?? "Unknown");
    for (const svc of asset.services ?? []) {
      if (svc.state === "open") services.add(`${svc.protocol}/${svc.port}`);
    }
  }
  return {
    vendors: [...vendors].sort(),
    types: [...types].sort(),
    oses: [...oses].sort(),
    services: [...services].sort((left, right) => Number(left.split("/")[1]) - Number(right.split("/")[1]))
  };
}

function FilterSelect({
  label,
  value,
  values,
  onChange
}: {
  label: string;
  value: string;
  values: string[];
  onChange: (value: string) => void;
}) {
  return (
    <select
      aria-label={label}
      className="focus-ring rounded-md border border-line bg-white px-3 py-2 text-sm"
      value={value}
      onChange={(event) => onChange(event.target.value)}
    >
      <option value="all">All {label.toLowerCase()}</option>
      {values.map((item) => (
        <option key={item} value={item}>{item}</option>
      ))}
    </select>
  );
}
