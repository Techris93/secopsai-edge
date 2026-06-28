"use client";

import { Clipboard, Download, Printer } from "lucide-react";
import { Suspense, useEffect, useMemo, useState } from "react";
import { useSearchParams } from "next/navigation";
import { PageHeader } from "@/components/PageHeader";
import { SeverityBadge } from "@/components/SeverityBadge";
import { getReport } from "@/lib/api";
import { timeAgo } from "@/lib/format";
import type { Finding, Report } from "@/lib/types";

export default function ReportDetailPage() {
  return (
    <Suspense fallback={<p className="text-sm text-zinc-600">Loading report...</p>}>
      <ReportDetail />
    </Suspense>
  );
}

function ReportDetail() {
  const searchParams = useSearchParams();
  const reportId = searchParams.get("id");
  const [report, setReport] = useState<Report | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  useEffect(() => {
    if (!reportId) return;
    getReport(reportId)
      .then(setReport)
      .catch((error) => setMessage(error instanceof Error ? error.message : "Unable to load report"));
  }, [reportId]);

  const findings = useMemo(() => (report?.content.findings ?? []) as Finding[], [report]);

  async function copySummary() {
    if (!report) return;
    await navigator.clipboard.writeText(report.summary);
    setMessage("Executive summary copied");
  }

  function downloadHtml() {
    if (!report) return;
    const html = buildReportHtml(report);
    const blob = new Blob([html], { type: "text/html" });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = `${report.title.replace(/[^a-z0-9]+/gi, "-").toLowerCase()}.html`;
    anchor.click();
    URL.revokeObjectURL(url);
    setMessage("Report downloaded");
  }

  return (
    <>
      <PageHeader
        eyebrow="Report Export"
        title={report?.title ?? "Report Detail"}
        description="Review, print, copy, and download a shareable SecOpsAI Edge report."
        action={report ? <SeverityBadge severity={report.risk_level} /> : null}
      />

      {!report ? (
        <section className="rounded-lg border border-line bg-white p-4 shadow-panel">
          <p className="text-sm text-zinc-600">{message ?? "Loading report..."}</p>
        </section>
      ) : (
        <article className="rounded-lg border border-line bg-white p-5 shadow-panel print:border-0 print:shadow-none">
          <div className="flex flex-col gap-3 border-b border-line pb-4 md:flex-row md:items-start md:justify-between">
            <div>
              <p className="text-sm font-medium text-zinc-500">Generated {timeAgo(report.created_at)}</p>
              <h2 className="mt-2 text-2xl font-semibold text-ink">{report.title}</h2>
              <p className="mt-3 max-w-4xl text-sm leading-6 text-zinc-700">{report.summary}</p>
            </div>
            <div className="flex flex-wrap gap-2 print:hidden">
              <button className="ButtonSecondary" onClick={copySummary} type="button">
                <Clipboard size={16} aria-hidden="true" />
                Copy Summary
              </button>
              <button className="ButtonSecondary" onClick={downloadHtml} type="button">
                <Download size={16} aria-hidden="true" />
                Download HTML
              </button>
              <button className="ButtonSecondary" onClick={() => window.print()} type="button">
                <Printer size={16} aria-hidden="true" />
                Print
              </button>
            </div>
          </div>

          <section className="mt-5">
            <h3 className="text-lg font-semibold text-ink">Recommended Actions</h3>
            <div className="mt-3 grid gap-3 md:grid-cols-3">
              {(report.content.recommended_actions ?? []).map((action) => (
                <div key={action} className="rounded-md bg-paper p-3 text-sm leading-6 text-ink">
                  {action}
                </div>
              ))}
            </div>
          </section>

          <section className="mt-6">
            <h3 className="text-lg font-semibold text-ink">Findings</h3>
            <div className="mt-3 divide-y divide-line rounded-md border border-line">
              {findings.map((finding) => (
                <div key={`${finding.type}-${finding.title}-${finding.created_at}`} className="grid gap-3 p-3 md:grid-cols-[8rem_1fr]">
                  <SeverityBadge severity={finding.severity} />
                  <div>
                    <p className="font-semibold text-ink">{finding.title}</p>
                    <p className="mt-1 text-sm leading-6 text-zinc-600">{finding.summary}</p>
                  </div>
                </div>
              ))}
              {!findings.length ? <p className="p-3 text-sm text-zinc-600">No active findings were included.</p> : null}
            </div>
          </section>

          <section className="mt-6 grid gap-3 md:grid-cols-3">
            <Meta label="Provider" value={String(report.content.provider ?? "unknown")} />
            <Meta label="Model" value={String(report.content.model ?? "n/a")} />
            <Meta label="Risk" value={report.risk_level} />
          </section>
          {message ? <p className="mt-4 rounded-md bg-emerald-50 px-3 py-2 text-sm text-emerald-800 print:hidden">{message}</p> : null}
        </article>
      )}
    </>
  );
}

function Meta({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-md bg-paper p-3">
      <p className="text-sm text-zinc-600">{label}</p>
      <p className="mt-1 font-mono text-sm text-ink">{value}</p>
    </div>
  );
}

function buildReportHtml(report: Report): string {
  const findings = (report.content.findings ?? []) as Finding[];
  return `<!doctype html>
<html><head><meta charset="utf-8"><title>${escapeHtml(report.title)}</title>
<style>body{font-family:Inter,Arial,sans-serif;margin:40px;color:#1f2933}h1{margin-bottom:8px}.badge{display:inline-block;padding:4px 8px;border:1px solid #d9ded7;border-radius:4px}.card{border:1px solid #d9ded7;border-radius:8px;padding:14px;margin:12px 0}.muted{color:#52606d}</style>
</head><body>
<p class="badge">${escapeHtml(report.risk_level)}</p>
<h1>${escapeHtml(report.title)}</h1>
<p class="muted">Generated ${escapeHtml(new Date(report.created_at).toLocaleString())}</p>
<p>${escapeHtml(report.summary)}</p>
<h2>Recommended Actions</h2>
${(report.content.recommended_actions ?? []).map((action) => `<div class="card">${escapeHtml(action)}</div>`).join("")}
<h2>Findings</h2>
${findings.map((finding) => `<div class="card"><strong>${escapeHtml(finding.severity)}: ${escapeHtml(finding.title)}</strong><p>${escapeHtml(finding.summary)}</p></div>`).join("") || "<p>No active findings were included.</p>"}
</body></html>`;
}

function escapeHtml(value: string): string {
  return value.replace(/[&<>"']/g, (char) => {
    const entities: Record<string, string> = {
      "&": "&amp;",
      "<": "&lt;",
      ">": "&gt;",
      '"': "&quot;",
      "'": "&#039;"
    };
    return entities[char] ?? char;
  });
}
