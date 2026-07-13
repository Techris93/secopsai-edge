"use client";

import { Search } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { DataStatePanel } from "@/components/DataStatePanel";
import { LiveState } from "@/components/LiveState";
import { PageHeader } from "@/components/PageHeader";
import { fetchAuditLogs } from "@/lib/api";
import { timeAgo, titleize } from "@/lib/format";
import type { DashboardDataMode } from "@/lib/api";
import type { AuditLog } from "@/lib/types";

export default function AuditPage() {
  const [logs, setLogs] = useState<AuditLog[]>([]);
  const [query, setQuery] = useState("");
  const [resourceType, setResourceType] = useState("all");
  const [mode, setMode] = useState<DashboardDataMode>("blocked");
  const [error, setError] = useState<string | undefined>();

  useEffect(() => {
    fetchAuditLogs({ limit: 250 })
      .then((rows) => {
        setLogs(rows);
        setMode("live");
      })
      .catch((loadError) => {
        setMode("blocked");
        setError(loadError instanceof Error ? loadError.message : "Unable to load audit history");
      });
  }, []);

  const resourceTypes = useMemo(
    () => Array.from(new Set(logs.map((log) => log.resource_type).filter(Boolean) as string[])).sort(),
    [logs]
  );
  const visibleLogs = logs.filter((log) => {
    const matchesType = resourceType === "all" || log.resource_type === resourceType;
    const haystack = `${log.action} ${log.resource_type ?? ""} ${log.resource_id ?? ""} ${JSON.stringify(log.details)}`.toLowerCase();
    return matchesType && haystack.includes(query.trim().toLowerCase());
  });

  return (
    <>
      <PageHeader
        eyebrow="Governance"
        title="Audit Log"
        description="Review operator, sensor, scan, finding, report, notification, and baseline changes."
        action={<LiveState live={mode === "live"} mode={mode} error={error} />}
      />
      <DataStatePanel mode={mode} error={error} />

      <section className="rounded-lg border border-line bg-white shadow-panel">
        <div className="flex flex-col gap-3 border-b border-line p-4 sm:flex-row">
          <label className="relative min-w-0 flex-1">
            <Search className="pointer-events-none absolute left-3 top-2.5 text-zinc-400" size={17} aria-hidden="true" />
            <span className="sr-only">Search audit events</span>
            <input
              className="focus-ring w-full rounded-md border border-line bg-white py-2 pl-10 pr-3 text-sm"
              onChange={(event) => setQuery(event.target.value)}
              placeholder="Search actions, resources, and details"
              value={query}
            />
          </label>
          <select
            aria-label="Filter by resource type"
            className="focus-ring rounded-md border border-line bg-white px-3 py-2 text-sm sm:w-56"
            onChange={(event) => setResourceType(event.target.value)}
            value={resourceType}
          >
            <option value="all">All resource types</option>
            {resourceTypes.map((type) => <option key={type} value={type}>{titleize(type)}</option>)}
          </select>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full min-w-[920px] text-left text-sm">
            <thead className="bg-paper text-xs uppercase text-zinc-600">
              <tr>
                <th className="px-4 py-3">Time</th>
                <th className="px-4 py-3">Action</th>
                <th className="px-4 py-3">Resource</th>
                <th className="px-4 py-3">Actor</th>
                <th className="px-4 py-3">Details</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-line">
              {visibleLogs.map((log) => (
                <tr key={log.id}>
                  <td className="whitespace-nowrap px-4 py-3 text-zinc-600" title={new Date(log.created_at).toLocaleString()}>{timeAgo(log.created_at)}</td>
                  <td className="px-4 py-3 font-semibold text-ink">{titleize(log.action)}</td>
                  <td className="px-4 py-3">
                    <span className="block text-zinc-700">{titleize(log.resource_type ?? "system")}</span>
                    <span className="block max-w-56 truncate font-mono text-xs text-zinc-500" title={log.resource_id ?? undefined}>{log.resource_id ?? "-"}</span>
                  </td>
                  <td className="px-4 py-3 font-mono text-xs text-zinc-600">{log.user_id ?? log.sensor_id ?? "system"}</td>
                  <td className="max-w-md px-4 py-3 font-mono text-xs text-zinc-600" title={JSON.stringify(log.details)}>{summarize(log.details)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        {!visibleLogs.length ? <p className="px-4 py-6 text-sm text-zinc-600">No audit events match these filters.</p> : null}
      </section>
    </>
  );
}

function summarize(details: Record<string, unknown>): string {
  const text = JSON.stringify(details);
  return text.length > 220 ? `${text.slice(0, 217)}...` : text;
}
