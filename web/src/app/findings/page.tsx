"use client";

import { CheckCircle2, Search, ShieldAlert } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { LiveState } from "@/components/LiveState";
import { PageHeader } from "@/components/PageHeader";
import { SeverityBadge } from "@/components/SeverityBadge";
import { fetchDashboardData, updateFindingStatus } from "@/lib/api";
import { timeAgo, titleize } from "@/lib/format";
import type { DashboardData, Finding } from "@/lib/types";

export default function FindingsPage() {
  const [data, setData] = useState<DashboardData | null>(null);
  const [live, setLive] = useState(false);
  const [error, setError] = useState<string | undefined>();
  const [query, setQuery] = useState("");
  const [severity, setSeverity] = useState("all");

  useEffect(() => {
    fetchDashboardData().then((result) => {
      setData(result.data);
      setLive(result.live);
      setError(result.error);
    });
  }, []);

  const findings = useMemo(
    () => filterFindings(data?.findings ?? [], query, severity),
    [data, query, severity]
  );

  async function resolveFinding(finding: Finding) {
    if (!live) return;
    const updated = await updateFindingStatus(finding.id, "resolved");
    setData((current) =>
      current
        ? {
            ...current,
            findings: current.findings.map((item) => (item.id === updated.id ? updated : item))
          }
        : current
    );
  }

  return (
    <>
      <PageHeader
        eyebrow="Detection"
        title="Findings"
        description="Review asset changes, risky services, wireless anomalies, and AI-ready evidence."
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
              placeholder="Search findings"
            />
          </label>
          <select
            className="focus-ring rounded-md border border-line bg-white px-3 py-2 text-sm"
            value={severity}
            onChange={(event) => setSeverity(event.target.value)}
          >
            <option value="all">All severities</option>
            <option value="critical">Critical</option>
            <option value="high">High</option>
            <option value="medium">Medium</option>
            <option value="low">Low</option>
          </select>
        </div>

        <div className="divide-y divide-line">
          {findings.map((finding) => (
            <article key={finding.id} className="grid gap-4 p-4 xl:grid-cols-[8rem_1fr_auto] xl:items-start">
              <SeverityBadge severity={finding.severity} />
              <div>
                <div className="flex flex-wrap items-center gap-2">
                  <ShieldAlert size={18} className="text-sea" aria-hidden="true" />
                  <h2 className="text-lg font-semibold text-ink">{finding.title}</h2>
                  <span className="rounded border border-line bg-paper px-2 py-1 text-xs font-medium">
                    {titleize(finding.type)}
                  </span>
                  <span className="rounded border border-line bg-paper px-2 py-1 text-xs font-medium">
                    {finding.status}
                  </span>
                </div>
                <p className="mt-2 text-sm leading-6 text-zinc-600">{finding.summary}</p>
                <pre className="mt-3 overflow-x-auto rounded-md bg-ink p-3 text-xs text-white">
                  {JSON.stringify(finding.evidence, null, 2)}
                </pre>
              </div>
              <div className="flex items-center gap-3 xl:flex-col xl:items-end">
                <span className="text-sm text-zinc-500">{timeAgo(finding.created_at)}</span>
                <button
                  className="focus-ring inline-flex items-center gap-2 rounded-md bg-sea px-3 py-2 text-sm font-medium text-white disabled:cursor-not-allowed disabled:bg-zinc-300"
                  disabled={!live || finding.status === "resolved"}
                  onClick={() => resolveFinding(finding)}
                  title={live ? "Mark finding resolved" : "Connect the API to update status"}
                >
                  <CheckCircle2 size={16} aria-hidden="true" />
                  Resolve
                </button>
              </div>
            </article>
          ))}
        </div>
      </section>
    </>
  );
}

function filterFindings(findings: Finding[], query: string, severity: string): Finding[] {
  const normalizedQuery = query.trim().toLowerCase();
  return findings.filter((finding) => {
    const severityMatch = severity === "all" || finding.severity === severity;
    const text = [finding.title, finding.summary, finding.type, finding.status]
      .join(" ")
      .toLowerCase();
    return severityMatch && (!normalizedQuery || text.includes(normalizedQuery));
  });
}
