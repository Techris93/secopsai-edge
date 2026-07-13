"use client";

import { Building2, Plus, X } from "lucide-react";
import { FormEvent, useEffect, useState } from "react";
import { createOrganization, fetchAuthIdentity, switchWorkspace } from "@/lib/api";
import type { AuthIdentity } from "@/lib/types";

export function WorkspaceSwitcher({ compact = false }: { compact?: boolean }) {
  const [identity, setIdentity] = useState<AuthIdentity | null>(null);
  const [creating, setCreating] = useState(false);
  const [name, setName] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchAuthIdentity().then(setIdentity).catch(() => setIdentity(null));
  }, []);

  if (!identity) return null;

  async function changeWorkspace(organizationId: string) {
    if (organizationId === identity?.organization_id) return;
    setBusy(true);
    setError(null);
    try {
      await switchWorkspace(organizationId);
      window.location.reload();
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Unable to switch workspace");
      setBusy(false);
    }
  }

  async function addWorkspace(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const organization = await createOrganization(name);
      await switchWorkspace(organization.id);
      window.location.reload();
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Unable to create workspace");
      setBusy(false);
    }
  }

  return (
    <div className={compact ? "min-w-0 flex-1" : "mt-5 border-y border-line py-4"}>
      <div className="flex items-center gap-2">
        {!compact ? <Building2 size={16} className="text-sea" aria-hidden="true" /> : null}
        <label className={compact ? "sr-only" : "text-xs font-semibold uppercase text-zinc-500"} htmlFor={`workspace-${compact ? "mobile" : "desktop"}`}>
          Workspace
        </label>
      </div>
      <div className={compact ? "flex items-center gap-2" : "mt-2 flex items-center gap-2"}>
        <select
          id={`workspace-${compact ? "mobile" : "desktop"}`}
          className="focus-ring min-w-0 flex-1 rounded-md border border-line bg-white px-2 py-2 text-sm font-medium text-ink disabled:bg-zinc-100"
          value={identity.organization_id}
          disabled={busy}
          onChange={(event) => void changeWorkspace(event.target.value)}
          aria-label="Active workspace"
        >
          {identity.organizations.map((organization) => (
            <option key={organization.id} value={organization.id}>{organization.name}</option>
          ))}
        </select>
        {identity.role === "owner" && !compact ? (
          <button className="focus-ring grid h-9 w-9 shrink-0 place-items-center rounded-md border border-line text-zinc-600 hover:bg-paper" type="button" title="Create workspace" aria-label="Create workspace" onClick={() => setCreating((value) => !value)}>
            {creating ? <X size={16} aria-hidden="true" /> : <Plus size={16} aria-hidden="true" />}
          </button>
        ) : null}
      </div>
      {!compact ? <p className="mt-1 text-xs text-zinc-500">{identity.role}</p> : null}
      {creating ? (
        <form className="mt-3 space-y-2" onSubmit={addWorkspace}>
          <input className="focus-ring w-full rounded-md border border-line px-2 py-2 text-sm" value={name} onChange={(event) => setName(event.target.value)} maxLength={160} placeholder="Customer or workspace name" required autoFocus />
          <button className="focus-ring w-full rounded-md bg-sea px-3 py-2 text-sm font-semibold text-white disabled:bg-zinc-300" type="submit" disabled={busy || !name.trim()}>Create workspace</button>
        </form>
      ) : null}
      {error ? <p className="mt-2 text-xs text-red-700" role="alert">{error}</p> : null}
    </div>
  );
}
