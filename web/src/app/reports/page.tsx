"use client";

import { FilePlus2, FileText } from "lucide-react";
import { useEffect, useState } from "react";
import Link from "next/link";
import { DataStatePanel } from "@/components/DataStatePanel";
import { LiveState } from "@/components/LiveState";
import { PageHeader } from "@/components/PageHeader";
import { SeverityBadge } from "@/components/SeverityBadge";
import { fetchDashboardData, generateSiteReport } from "@/lib/api";
import { timeAgo } from "@/lib/format";
import type { DashboardDataMode } from "@/lib/api";
import type { DashboardData, Report } from "@/lib/types";

export default function ReportsPage() {
  const [data, setData] = useState<DashboardData | null>(null);
  const [live, setLive] = useState(false);
  const [mode, setMode] = useState<DashboardDataMode>("blocked");
  const [error, setError] = useState<string | undefined>();
  const [busy, setBusy] = useState(false);
  const [site, setSite] = useState("all");

  useEffect(() => {
    fetchDashboardData().then((result) => {
      setData(result.data);
      setLive(result.live);
      setMode(result.mode);
      setError(result.error);
    });
  }, []);

  async function onGenerateReport() {
    setBusy(true);
    try {
      const report = await generateSiteReport(site === "all" ? undefined : site);
      setData((current) =>
        current ? { ...current, reports: [report, ...current.reports] } : current
      );
    } finally {
      setBusy(false);
    }
  }

  const reports = (data?.reports ?? []).filter((report) => site === "all" || report.site_id === site);

  return (
    <>
      <PageHeader
        eyebrow="AI Reporting"
        title="Reports"
        description="Generate executive and technical summaries from normalized findings while raw scan data remains local."
        action={
          <div className="flex flex-col gap-2 sm:flex-row sm:items-center">
            <LiveState live={live} mode={mode} error={error} />
            <select
              aria-label="Report site"
              className="focus-ring rounded-md border border-line bg-white px-3 py-2 text-sm"
              value={site}
              onChange={(event) => setSite(event.target.value)}
            >
              <option value="all">All sites</option>
              {(data?.sites ?? []).map((item) => (
                <option key={item.id} value={item.id}>{item.name}</option>
              ))}
            </select>
            <button
              className="focus-ring inline-flex items-center justify-center gap-2 rounded-md bg-sea px-3 py-2 text-sm font-medium text-white disabled:cursor-not-allowed disabled:bg-zinc-300"
              disabled={!live || busy}
              onClick={onGenerateReport}
              title={live ? "Generate AI report" : "Connect the API to generate reports"}
            >
              <FilePlus2 size={16} aria-hidden="true" />
              {busy ? "Generating" : "Generate"}
            </button>
          </div>
        }
      />
      <DataStatePanel mode={mode} error={error} />

      <div className="grid gap-4">
        {reports.map((report) => (
          <ReportCard key={report.id} report={report} />
        ))}
        {data && !reports.length ? (
          <section className="rounded-lg border border-line bg-white px-4 py-8 text-center shadow-panel">
            <h2 className="text-base font-semibold text-ink">No reports yet</h2>
            <p className="mt-1 text-sm text-zinc-600">Generate a report after the first authorized scan completes.</p>
          </section>
        ) : null}
      </div>
    </>
  );
}

function ReportCard({ report }: { report: Report }) {
  return (
    <article className="rounded-lg border border-line bg-white p-4 shadow-panel">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <div className="flex items-center gap-2">
            <FileText size={18} className="text-sea" aria-hidden="true" />
            <h2 className="text-xl font-semibold text-ink">{report.title}</h2>
          </div>
          <p className="mt-2 text-sm text-zinc-500">{timeAgo(report.created_at)}</p>
        </div>
        <SeverityBadge severity={report.risk_level} />
      </div>
      <p className="mt-4 text-sm leading-6 text-zinc-600">{report.summary}</p>
      <Link
        className="focus-ring mt-4 inline-flex h-10 items-center justify-center gap-2 rounded-md border border-line bg-white px-3 text-sm font-semibold text-ink transition hover:border-sea hover:text-sea"
        href={`/reports/detail?id=${encodeURIComponent(report.id)}`}
      >
        Open Report
      </Link>
      <div className="mt-4 grid gap-3 md:grid-cols-3">
        {(report.content.recommended_actions ?? []).map((action) => (
          <div key={action} className="rounded-md bg-paper p-3 text-sm leading-6 text-ink">
            {action}
          </div>
        ))}
      </div>
    </article>
  );
}
