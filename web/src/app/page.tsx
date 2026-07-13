"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { AlertTriangle, FileText, RefreshCw, Server, ShieldAlert, Wifi } from "lucide-react";
import { DataStatePanel } from "@/components/DataStatePanel";
import { LiveState } from "@/components/LiveState";
import { OnboardingChecklist } from "@/components/OnboardingChecklist";
import { PageHeader } from "@/components/PageHeader";
import { ScanActions } from "@/components/ScanActions";
import { SeverityBadge } from "@/components/SeverityBadge";
import { StatCard } from "@/components/StatCard";
import { fetchDashboardData } from "@/lib/api";
import { timeAgo } from "@/lib/format";
import type { DashboardDataMode } from "@/lib/api";
import type { DashboardData } from "@/lib/types";

export default function OverviewPage() {
  const [data, setData] = useState<DashboardData | null>(null);
  const [live, setLive] = useState(false);
  const [mode, setMode] = useState<DashboardDataMode>("blocked");
  const [error, setError] = useState<string | undefined>();

  const loadDashboardData = useCallback(async () => {
    const result = await fetchDashboardData();
    setData(result.data);
    setLive(result.live);
    setMode(result.mode);
    setError(result.error);
  }, []);

  useEffect(() => {
    loadDashboardData();
  }, [loadDashboardData]);

  const summary = useMemo(() => {
    const findings = data?.findings ?? [];
    return {
      activeAssets: data?.assets.filter((asset) => asset.status === "active").length ?? 0,
      wifiCount: data?.wifiNetworks.length ?? 0,
      highRisk: findings.filter((finding) => ["critical", "high"].includes(finding.severity)).length,
      openFindings: findings.filter((finding) => finding.status === "open").length
    };
  }, [data]);

  const latestFindings = data?.findings.slice(0, 5) ?? [];
  const latestReport = data?.reports[0];

  return (
    <>
      <PageHeader
        eyebrow="SecOpsAI Console"
        title="Wireless Intelligence & Asset Discovery"
        description="Track local assets, risky exposed services, Wi-Fi changes, and AI-generated security summaries from your MacBook sensor."
        action={<LiveState live={live} mode={mode} error={error} />}
      />
      <DataStatePanel mode={mode} error={error} />

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <StatCard label="Assets" value={summary.activeAssets} detail="Currently active inventory" icon={Server} />
        <StatCard label="Wi-Fi Networks" value={summary.wifiCount} detail="Observed SSIDs and BSSIDs" icon={Wifi} tone="ink" />
        <StatCard label="Priority Risks" value={summary.highRisk} detail="High or critical findings" icon={AlertTriangle} tone="danger" />
        <StatCard label="Open Findings" value={summary.openFindings} detail="Waiting for review" icon={ShieldAlert} tone="amber" />
      </div>

      <div className="mt-6 grid items-start gap-6 xl:grid-cols-[1.15fr_0.85fr]">
        <div className="grid gap-6">
          <section className="rounded-lg border border-line bg-white shadow-panel">
            <div className="flex items-center justify-between border-b border-line px-4 py-3">
              <h2 className="text-lg font-semibold text-ink">Recent Findings</h2>
              <RefreshCw size={18} className="text-zinc-500" aria-hidden="true" />
            </div>
            <div className="divide-y divide-line">
              {latestFindings.map((finding) => (
                <article key={finding.id} className="grid gap-3 px-4 py-4 sm:grid-cols-[8rem_1fr_auto] sm:items-center">
                  <SeverityBadge severity={finding.severity} />
                  <div>
                    <h3 className="font-medium text-ink">{finding.title}</h3>
                    <p className="mt-1 text-sm leading-6 text-zinc-600">{finding.summary}</p>
                  </div>
                  <span className="text-sm text-zinc-500">{timeAgo(finding.created_at)}</span>
                </article>
              ))}
            </div>
          </section>

          <section className="rounded-lg border border-line bg-white p-4 shadow-panel">
            <div className="flex items-center gap-2">
              <FileText size={20} className="text-sea" aria-hidden="true" />
              <h2 className="text-lg font-semibold text-ink">AI Insight</h2>
            </div>
            {latestReport ? (
              <div className="mt-4">
                <SeverityBadge severity={latestReport.risk_level} />
                <h3 className="mt-4 text-xl font-semibold text-ink">{latestReport.title}</h3>
                <p className="mt-3 text-sm leading-6 text-zinc-600">{latestReport.summary}</p>
                <ul className="mt-4 space-y-2">
                  {(latestReport.content.recommended_actions ?? []).slice(0, 3).map((action) => (
                    <li key={action} className="rounded-md bg-paper px-3 py-2 text-sm text-ink">
                      {action}
                    </li>
                  ))}
                </ul>
              </div>
            ) : (
              <p className="mt-4 text-sm text-zinc-600">Generate a report after ingesting scan findings.</p>
            )}
          </section>
        </div>

        <div className="grid gap-6">
          <OnboardingChecklist status={data?.onboarding ?? null} />
          <ScanActions scanJobs={data?.scanJobs ?? []} sensors={data?.sensors ?? []} onChanged={loadDashboardData} />
        </div>
      </div>
    </>
  );
}
