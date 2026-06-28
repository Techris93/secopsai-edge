"use client";

import { CheckCircle2, ClipboardCheck, MessageSquarePlus, Play } from "lucide-react";
import { FormEvent, Suspense, useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import { PageHeader } from "@/components/PageHeader";
import { SeverityBadge } from "@/components/SeverityBadge";
import { createFindingNote, getFinding, updateFindingStatus, verifyFinding } from "@/lib/api";
import { timeAgo, titleize } from "@/lib/format";
import type { FindingDetail } from "@/lib/types";

export default function FindingDetailPage() {
  return (
    <Suspense fallback={<p className="text-sm text-zinc-600">Loading finding...</p>}>
      <FindingDetailView />
    </Suspense>
  );
}

function FindingDetailView() {
  const searchParams = useSearchParams();
  const findingId = searchParams.get("id");
  const [finding, setFinding] = useState<FindingDetail | null>(null);
  const [note, setNote] = useState("");
  const [message, setMessage] = useState<string | null>(null);

  async function load() {
    if (!findingId) return;
    try {
      setFinding(await getFinding(findingId));
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Unable to load finding");
    }
  }

  useEffect(() => {
    load();
  }, [findingId]);

  async function setStatus(status: string) {
    if (!finding) return;
    const updated = await updateFindingStatus(finding.id, status);
    setFinding({ ...finding, ...updated });
    setMessage(`Finding marked ${status}`);
  }

  async function addNote(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!finding || !note.trim()) return;
    const created = await createFindingNote(finding.id, note.trim());
    setFinding({ ...finding, notes: [...finding.notes, created] });
    setNote("");
    setMessage("Note added");
  }

  async function queueVerification() {
    if (!finding) return;
    const job = await verifyFinding(finding.id);
    setMessage(`Verification scan queued for ${job.target_cidr}`);
  }

  return (
    <>
      <PageHeader
        eyebrow="Finding Detail"
        title={finding?.title ?? "Finding"}
        description="Triage evidence, document remediation notes, and queue verification scans."
        action={finding ? <SeverityBadge severity={finding.severity} /> : null}
      />

      {!finding ? (
        <section className="rounded-lg border border-line bg-white p-4 shadow-panel">
          <p className="text-sm text-zinc-600">{message ?? "Loading finding..."}</p>
        </section>
      ) : (
        <div className="grid gap-6 xl:grid-cols-[1fr_0.8fr]">
          <section className="rounded-lg border border-line bg-white p-4 shadow-panel">
            <div className="flex flex-wrap items-center gap-2">
              <span className="rounded border border-line bg-paper px-2 py-1 text-xs font-semibold">
                {titleize(finding.type)}
              </span>
              <span className="rounded border border-line bg-paper px-2 py-1 text-xs font-semibold">
                {finding.status}
              </span>
              <span className="text-sm text-zinc-500">First seen {timeAgo(finding.created_at)}</span>
            </div>
            <p className="mt-4 text-sm leading-6 text-zinc-700">{finding.summary}</p>

            <h2 className="mt-6 text-lg font-semibold text-ink">Evidence</h2>
            <pre className="mt-3 overflow-x-auto rounded-md bg-ink p-3 text-xs text-white">
              {JSON.stringify(finding.evidence, null, 2)}
            </pre>

            <h2 className="mt-6 text-lg font-semibold text-ink">MITRE ATT&CK</h2>
            <div className="mt-3 grid gap-2">
              {finding.mitre_attack.map((item) => (
                <div key={`${item.id}-${item.name}`} className="rounded-md bg-paper p-3 text-sm">
                  <span className="font-mono text-ink">{String(item.id)}</span>
                  <span className="ml-2 text-zinc-700">{String(item.name)}</span>
                </div>
              ))}
              {!finding.mitre_attack.length ? <p className="rounded-md bg-paper p-3 text-sm text-zinc-600">No mapping attached.</p> : null}
            </div>
          </section>

          <aside className="grid gap-6">
            <section className="rounded-lg border border-line bg-white p-4 shadow-panel">
              <div className="flex items-center gap-2">
                <ClipboardCheck size={20} className="text-sea" aria-hidden="true" />
                <h2 className="text-lg font-semibold text-ink">Workflow</h2>
              </div>
              <div className="mt-4 grid gap-2">
                <button className="ButtonSecondary" onClick={() => setStatus("acknowledged")} type="button">
                  Acknowledge
                </button>
                <button className="ButtonSecondary" onClick={() => setStatus("resolved")} type="button">
                  <CheckCircle2 size={16} aria-hidden="true" />
                  Mark Resolved
                </button>
                <button className="ButtonSecondary" onClick={() => setStatus("false_positive")} type="button">
                  False Positive
                </button>
                <button className="ButtonSecondary" disabled={!finding.asset_id} onClick={queueVerification} type="button">
                  <Play size={16} aria-hidden="true" />
                  Verify Fixed
                </button>
              </div>
            </section>

            <section className="rounded-lg border border-line bg-white p-4 shadow-panel">
              <div className="flex items-center gap-2">
                <MessageSquarePlus size={20} className="text-sea" aria-hidden="true" />
                <h2 className="text-lg font-semibold text-ink">Notes</h2>
              </div>
              <form className="mt-4 grid gap-3" onSubmit={addNote}>
                <textarea
                  className="focus-ring min-h-28 rounded-md border border-line bg-white px-3 py-2 text-sm"
                  value={note}
                  onChange={(event) => setNote(event.target.value)}
                  placeholder="Add remediation or ownership notes"
                />
                <button className="focus-ring inline-flex h-10 items-center justify-center gap-2 rounded-md bg-sea px-3 text-sm font-semibold text-white disabled:bg-zinc-300" disabled={!note.trim()} type="submit">
                  Add Note
                </button>
              </form>
              <div className="mt-4 grid gap-3">
                {finding.notes.map((item) => (
                  <div key={item.id} className="rounded-md bg-paper p-3">
                    <p className="text-sm leading-6 text-ink">{item.body}</p>
                    <p className="mt-2 text-xs text-zinc-500">{item.author} · {timeAgo(item.created_at)}</p>
                  </div>
                ))}
                {!finding.notes.length ? <p className="text-sm text-zinc-600">No notes yet.</p> : null}
              </div>
            </section>

            {message ? <p className="rounded-md bg-emerald-50 px-3 py-2 text-sm text-emerald-800">{message}</p> : null}
          </aside>
        </div>
      )}
    </>
  );
}
