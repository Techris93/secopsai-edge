"use client";

import Link from "next/link";
import { Activity, Clock3, EthernetPort, History, Laptop, Server } from "lucide-react";
import { Suspense, useEffect, useMemo, useState } from "react";
import { useSearchParams } from "next/navigation";
import { PageHeader } from "@/components/PageHeader";
import { SeverityBadge } from "@/components/SeverityBadge";
import { getAsset } from "@/lib/api";
import { timeAgo, titleize } from "@/lib/format";
import type { AssetDetail, AssetTimelineEvent } from "@/lib/types";

export default function AssetDetailPage() {
  return (
    <Suspense fallback={<p className="text-sm text-zinc-600">Loading asset...</p>}>
      <AssetDetailView />
    </Suspense>
  );
}

function AssetDetailView() {
  const searchParams = useSearchParams();
  const assetId = searchParams.get("id");
  const [detail, setDetail] = useState<AssetDetail | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  useEffect(() => {
    async function load() {
      if (!assetId) {
        setMessage("Missing asset id");
        return;
      }
      try {
        setDetail(await getAsset(assetId));
      } catch (error) {
        setMessage(error instanceof Error ? error.message : "Unable to load asset");
      }
    }
    load();
  }, [assetId]);

  const openServices = useMemo(
    () => (detail?.asset.services ?? []).filter((service) => service.state === "open"),
    [detail]
  );

  return (
    <>
      <PageHeader
        eyebrow="Asset Detail"
        title={detail?.asset.hostname ?? detail?.asset.ip_address ?? "Asset"}
        description="Review identity, exposed services, related findings, and scan history for this network asset."
        action={detail ? <StatusPill status={detail.asset.status} /> : null}
      />

      {!detail ? (
        <section className="rounded-lg border border-line bg-white p-4 shadow-panel">
          <p className="text-sm text-zinc-600">{message ?? "Loading asset..."}</p>
        </section>
      ) : (
        <div className="grid gap-6 xl:grid-cols-[0.9fr_1.1fr]">
          <section className="rounded-lg border border-line bg-white p-4 shadow-panel">
            <div className="flex items-center gap-2">
              <Laptop size={20} className="text-sea" aria-hidden="true" />
              <h2 className="text-lg font-semibold text-ink">Identity</h2>
            </div>
            <dl className="mt-4 grid gap-3 sm:grid-cols-2">
              <Metric label="IP Address" value={detail.asset.ip_address} mono />
              <Metric label="MAC Address" value={detail.asset.mac_address ?? "Not observed"} mono />
              <Metric label="Hostname" value={detail.asset.hostname ?? "Unknown"} />
              <Metric label="Vendor" value={detail.asset.vendor ?? "Unknown"} />
              <Metric label="Device Type" value={detail.asset.device_type ?? "Unclassified"} />
              <Metric label="OS Guess" value={detail.asset.os_guess ?? "Unknown"} />
              <Metric label="First Seen" value={timeAgo(detail.asset.first_seen_at)} />
              <Metric label="Last Seen" value={timeAgo(detail.asset.last_seen_at)} />
            </dl>
          </section>

          <section className="rounded-lg border border-line bg-white p-4 shadow-panel">
            <div className="flex items-center gap-2">
              <EthernetPort size={20} className="text-sea" aria-hidden="true" />
              <h2 className="text-lg font-semibold text-ink">Exposed Services</h2>
            </div>
            <div className="mt-4 divide-y divide-line rounded-md border border-line">
              {openServices.map((service) => (
                <div key={service.id} className="grid gap-2 p-3 sm:grid-cols-[9rem_1fr_auto] sm:items-center">
                  <span className="font-mono text-sm font-semibold text-ink">
                    {service.protocol}/{service.port}
                  </span>
                  <span className="text-sm text-zinc-700">
                    {[service.name, service.product, service.version].filter(Boolean).join(" ") || "Unknown service"}
                  </span>
                  <span className="rounded border border-line bg-paper px-2 py-1 text-xs font-semibold uppercase text-ink">
                    {service.state}
                  </span>
                </div>
              ))}
              {!openServices.length ? <p className="p-3 text-sm text-zinc-600">No open services observed.</p> : null}
            </div>
          </section>

          <section className="rounded-lg border border-line bg-white p-4 shadow-panel">
            <div className="flex items-center gap-2">
              <Activity size={20} className="text-sea" aria-hidden="true" />
              <h2 className="text-lg font-semibold text-ink">Related Findings</h2>
            </div>
            <div className="mt-4 grid gap-3">
              {detail.findings.map((finding) => (
                <Link
                  key={finding.id}
                  className="focus-ring rounded-md border border-line bg-white p-3 transition hover:border-sea"
                  href={`/findings/detail?id=${encodeURIComponent(finding.id)}`}
                >
                  <div className="flex flex-wrap items-center gap-2">
                    <SeverityBadge severity={finding.severity} />
                    <span className="rounded border border-line bg-paper px-2 py-1 text-xs font-semibold">
                      {titleize(finding.type)}
                    </span>
                    <span className="text-xs text-zinc-500">{timeAgo(finding.created_at)}</span>
                  </div>
                  <h3 className="mt-3 font-semibold text-ink">{finding.title}</h3>
                  <p className="mt-1 text-sm leading-6 text-zinc-600">{finding.summary}</p>
                </Link>
              ))}
              {!detail.findings.length ? <p className="rounded-md bg-paper p-3 text-sm text-zinc-600">No findings linked to this asset.</p> : null}
            </div>
          </section>

          <section className="rounded-lg border border-line bg-white p-4 shadow-panel">
            <div className="flex items-center gap-2">
              <History size={20} className="text-sea" aria-hidden="true" />
              <h2 className="text-lg font-semibold text-ink">Change Timeline</h2>
            </div>
            <div className="mt-4 grid gap-3">
              {detail.timeline.map((event) => (
                <TimelineEvent key={event.id} event={event} />
              ))}
            </div>
          </section>

          <section className="rounded-lg border border-line bg-white p-4 shadow-panel xl:col-span-2">
            <div className="flex items-center gap-2">
              <Server size={20} className="text-sea" aria-hidden="true" />
              <h2 className="text-lg font-semibold text-ink">Recent Observations</h2>
            </div>
            <div className="mt-4 overflow-x-auto rounded-md border border-line">
              <table className="w-full min-w-[780px] text-left text-sm">
                <thead className="bg-paper text-xs uppercase text-zinc-600">
                  <tr>
                    <th className="px-3 py-2">Observed</th>
                    <th className="px-3 py-2">Hostname</th>
                    <th className="px-3 py-2">Vendor</th>
                    <th className="px-3 py-2">OS</th>
                    <th className="px-3 py-2">Source</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-line">
                  {detail.observations.map((observation) => (
                    <tr key={observation.id}>
                      <td className="px-3 py-2 text-zinc-600">{timeAgo(observation.observed_at)}</td>
                      <td className="px-3 py-2">{observation.hostname ?? "Unknown"}</td>
                      <td className="px-3 py-2">{observation.vendor ?? "Unknown"}</td>
                      <td className="px-3 py-2">{observation.os_guess ?? "Unknown"}</td>
                      <td className="px-3 py-2">{observation.raw_source ?? "sensor scan"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>
        </div>
      )}
    </>
  );
}

function Metric({ label, value, mono = false }: { label: string; value: string; mono?: boolean }) {
  return (
    <div className="rounded-md bg-paper p-3">
      <dt className="text-sm text-zinc-600">{label}</dt>
      <dd className={`mt-1 break-words text-sm font-semibold text-ink ${mono ? "font-mono" : ""}`}>{value}</dd>
    </div>
  );
}

function StatusPill({ status }: { status: string }) {
  return (
    <span className="rounded-md border border-line bg-paper px-3 py-2 text-sm font-semibold uppercase text-ink">
      {status}
    </span>
  );
}

function TimelineEvent({ event }: { event: AssetTimelineEvent }) {
  return (
    <article className="grid gap-3 rounded-md border border-line bg-white p-3 sm:grid-cols-[2rem_1fr_auto] sm:items-start">
      <span className="mt-1 inline-flex h-8 w-8 items-center justify-center rounded-md bg-paper text-sea">
        <Clock3 size={16} aria-hidden="true" />
      </span>
      <div>
        <div className="flex flex-wrap items-center gap-2">
          <SeverityBadge severity={event.severity} />
          <span className="rounded border border-line bg-paper px-2 py-1 text-xs font-semibold">
            {titleize(event.kind)}
          </span>
        </div>
        <h3 className="mt-2 font-semibold text-ink">{event.title}</h3>
        <p className="mt-1 text-sm leading-6 text-zinc-600">{event.summary}</p>
      </div>
      <time className="text-sm text-zinc-500">{timeAgo(event.occurred_at)}</time>
    </article>
  );
}
