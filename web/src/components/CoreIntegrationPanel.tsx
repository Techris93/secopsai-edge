"use client";

import { AlertTriangle, CheckCircle2, Clipboard, Download, GitBranch, KeyRound, LifeBuoy, ListTree, RefreshCw, ShieldCheck, Terminal, Trash2 } from "lucide-react";
import type { ComponentType } from "react";
import { useEffect, useMemo, useState } from "react";
import { apiBaseUrl, createIntegrationToken, downloadCoreBundle, fetchAuthIdentity, listIntegrationTokens, revokeIntegrationToken, rotateIntegrationToken } from "@/lib/api";
import { copyText } from "@/lib/clipboard";
import type { IntegrationToken, IntegrationTokenSecret } from "@/lib/types";

const DEFAULT_EDGE_ROOT = process.env.NEXT_PUBLIC_EDGE_ROOT ?? "$HOME/secopsai-edge";
const DEFAULT_CORE_ROOT = process.env.NEXT_PUBLIC_CORE_ROOT ?? "$HOME/secopsai";
const DEFAULT_CORE_API_URL = "https://secopsai-core-api.onrender.com";
const EDGE_ROOT_KEY = "secopsai_edge_root";
const CORE_ROOT_KEY = "secopsai_core_root";
const CORE_API_URL_KEY = "secopsai_core_api_url";

export function CoreIntegrationPanel() {
  const [busyAction, setBusyAction] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [edgeRoot, setEdgeRoot] = useState(DEFAULT_EDGE_ROOT);
  const [coreRoot, setCoreRoot] = useState(DEFAULT_CORE_ROOT);
  const [coreApiUrl, setCoreApiUrl] = useState(DEFAULT_CORE_API_URL);
  const [tokens, setTokens] = useState<IntegrationToken[]>([]);
  const [newToken, setNewToken] = useState<IntegrationTokenSecret | null>(null);
  const [canManageTokens, setCanManageTokens] = useState(false);

  useEffect(() => {
    setEdgeRoot(window.localStorage.getItem(EDGE_ROOT_KEY) || DEFAULT_EDGE_ROOT);
    setCoreRoot(window.localStorage.getItem(CORE_ROOT_KEY) || DEFAULT_CORE_ROOT);
    setCoreApiUrl(window.localStorage.getItem(CORE_API_URL_KEY) || DEFAULT_CORE_API_URL);
  }, []);

  useEffect(() => {
    let active = true;
    fetchAuthIdentity()
      .then(async (identity) => {
        const canManage = identity.role === "owner" || identity.role === "admin";
        if (active) setCanManageTokens(canManage);
        if (canManage) {
          const items = await listIntegrationTokens();
          if (active) setTokens(items);
        }
      })
      .catch(() => {
        // The connection panel owns unauthenticated recovery state.
      });
    return () => {
      active = false;
    };
  }, []);

  function updateRoot(key: string, value: string, setter: (next: string) => void) {
    setter(value);
    window.localStorage.setItem(key, value);
  }

  const commands = useMemo(
    () => {
      const bundlePath = `${edgeRoot}/edge-bundle.json`;
      return [
      {
        label: "Copy Export",
        icon: Download,
        command: `cd "${edgeRoot}"\nSECOPSAI_EDGE_CORE_TOKEN="$(python3 -c 'import getpass; print(getpass.getpass("Core export token: "))')"; export SECOPSAI_EDGE_CORE_TOKEN\n./scripts/edge core export --cloud --output edge-bundle.json\nunset SECOPSAI_EDGE_CORE_TOKEN`
      },
      {
        label: "Copy Import",
        icon: GitBranch,
        command: `cd "${coreRoot}"\n.venv/bin/python -m secopsai.cli edge import --bundle "${bundlePath}"`
      },
      {
        label: "Copy Assets",
        icon: ListTree,
        command: `cd "${coreRoot}"\n.venv/bin/python -m secopsai.cli graph assets`
      },
      {
        label: "Copy Changes",
        icon: ListTree,
        command: `cd "${coreRoot}"\n.venv/bin/python -m secopsai.cli graph changes`
      },
      {
        label: "Copy Triage",
        icon: ShieldCheck,
        command: `cd "${coreRoot}"\n.venv/bin/python -m secopsai.cli triage list --source secopsai_edge`
      },
      {
        label: "Copy API Sync",
        icon: GitBranch,
        command: `cd "${coreRoot}"\nSECOPSAI_EDGE_ACCESS_TOKEN="$(python3 -c 'import getpass; print(getpass.getpass("Core export token: "))')"; export SECOPSAI_EDGE_ACCESS_TOKEN\nSECOPSAI_EDGE_API_URL=${apiBaseUrl()} .venv/bin/python -m secopsai.cli edge sync\nunset SECOPSAI_EDGE_ACCESS_TOKEN`
      },
      {
        label: "Copy One-Step Sync",
        icon: GitBranch,
        command: `cd "${edgeRoot}"\nSECOPSAI_EDGE_CORE_TOKEN="$(python3 -c 'import getpass; print(getpass.getpass("Core export token: "))')"; export SECOPSAI_EDGE_CORE_TOKEN\n./scripts/edge core sync --cloud --core-root "${coreRoot}" --output edge-bundle.json\nunset SECOPSAI_EDGE_CORE_TOKEN`
      },
      {
        label: "Copy Hosted Push",
        icon: GitBranch,
        command: `cd "${edgeRoot}"\nSECOPSAI_EDGE_CORE_TOKEN="$(python3 -c 'import getpass; print(getpass.getpass("Edge Core export token: "))')"; export SECOPSAI_EDGE_CORE_TOKEN\nSECOPSAI_CORE_INGEST_TOKEN="$(python3 -c 'import getpass; print(getpass.getpass("Core ingest token: "))')"; export SECOPSAI_CORE_INGEST_TOKEN\n./scripts/edge core push --cloud --core-api-url "${coreApiUrl}" --output edge-bundle.json\nunset SECOPSAI_EDGE_CORE_TOKEN SECOPSAI_CORE_INGEST_TOKEN`
      },
      {
        label: "Install Auto Sync",
        icon: GitBranch,
        command: `cd "${edgeRoot}"\nSECOPSAI_EDGE_CORE_TOKEN="$(python3 -c 'import getpass; print(getpass.getpass("Core export token: "))')"; export SECOPSAI_EDGE_CORE_TOKEN\n./scripts/edge core sync-service install --cloud --core-root "${coreRoot}" --interval 300\nunset SECOPSAI_EDGE_CORE_TOKEN\n./scripts/edge core sync-service start`
      },
      {
        label: "Install Hosted Sync",
        icon: GitBranch,
        command: `cd "${edgeRoot}"\nSECOPSAI_EDGE_CORE_TOKEN="$(python3 -c 'import getpass; print(getpass.getpass("Edge Core export token: "))')"; export SECOPSAI_EDGE_CORE_TOKEN\nSECOPSAI_CORE_INGEST_TOKEN="$(python3 -c 'import getpass; print(getpass.getpass("Core ingest token: "))')"; export SECOPSAI_CORE_INGEST_TOKEN\n./scripts/edge core sync-service install --cloud --core-api-url "${coreApiUrl}" --interval 300\nunset SECOPSAI_EDGE_CORE_TOKEN SECOPSAI_CORE_INGEST_TOKEN\n./scripts/edge core sync-service start`
      },
      {
        label: "Run Sync Now",
        icon: GitBranch,
        command: `cd "${edgeRoot}"\n./scripts/edge core sync-service run-now`
      },
      {
        label: "Check Sync Status",
        icon: ListTree,
        command: `cd "${edgeRoot}"\n./scripts/edge core sync-service status`
      },
      {
        label: "View Sync Logs",
        icon: LifeBuoy,
        command: `cd "${edgeRoot}"\n./scripts/edge core sync-service logs`
      },
      {
        label: "Copy Edge Test",
        icon: Terminal,
        command: `cd "${edgeRoot}"\n./scripts/edge test`
      },
      {
        label: "Copy Core Test",
        icon: Terminal,
        command: `cd "${coreRoot}"\n.venv/bin/python -m pytest tests`
      },
      {
        label: "Copy Support Bundle",
        icon: LifeBuoy,
        command: `cd "${edgeRoot}"\n./scripts/edge support-bundle --cloud`
      }
      ];
    },
    [coreApiUrl, coreRoot, edgeRoot]
  );

  async function copyCommand(label: string, command: string) {
    setBusyAction(label);
    const copied = await copyText(command);
    setMessage(copied ? `${label} copied` : "Clipboard unavailable. Select and copy the command manually.");
    setBusyAction(null);
  }

  async function downloadBundle() {
    setBusyAction("download");
    try {
      const blob = await downloadCoreBundle();
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = "edge-bundle.json";
      anchor.click();
      URL.revokeObjectURL(url);
      setMessage("Core bundle downloaded");
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Unable to download bundle");
    } finally {
      setBusyAction(null);
    }
  }

  async function createToken(scope: "core:export" | "operations:read") {
    setBusyAction(`create-token:${scope}`);
    try {
      const isCore = scope === "core:export";
      const created = await createIntegrationToken(
        isCore ? "SecOpsAI Core sync" : "SecOpsAI operator dashboard",
        [scope]
      );
      setNewToken(created);
      setTokens((current) => [created, ...current.filter((item) => item.id !== created.id)]);
      setMessage("Integration token created. Copy it now; it will not be shown again.");
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Unable to create integration token");
    } finally {
      setBusyAction(null);
    }
  }

  async function revokeToken(tokenId: string) {
    setBusyAction(tokenId);
    try {
      const revoked = await revokeIntegrationToken(tokenId);
      setTokens((current) => current.map((item) => (item.id === revoked.id ? revoked : item)));
      if (newToken?.id === tokenId) setNewToken(null);
      setMessage("Integration token revoked");
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Unable to revoke integration token");
    } finally {
      setBusyAction(null);
    }
  }

  async function rotateToken(tokenId: string) {
    setBusyAction(`rotate:${tokenId}`);
    try {
      const replacement = await rotateIntegrationToken(tokenId);
      setNewToken(replacement);
      setTokens((current) => [replacement, ...current.filter((item) => item.id !== replacement.id)]);
      setMessage("Replacement created. Update the downstream service, verify it, then revoke the previous token.");
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Unable to rotate integration token");
    } finally {
      setBusyAction(null);
    }
  }

  return (
    <section className="min-w-0 rounded-lg border border-line bg-white p-4 shadow-panel xl:col-span-2">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex items-center gap-2">
          <GitBranch size={20} className="text-sea" aria-hidden={true} />
          <h2 className="text-lg font-semibold text-ink">SecOpsAI Core Integration</h2>
        </div>
        <button
          type="button"
          onClick={downloadBundle}
          disabled={busyAction !== null}
          className="focus-ring inline-flex h-10 items-center justify-center gap-2 rounded-md bg-sea px-3 text-sm font-semibold text-white transition hover:bg-ink disabled:cursor-wait disabled:opacity-60"
        >
          <Download size={16} aria-hidden={true} />
          Download Bundle
        </button>
      </div>
      <p className="mt-2 text-sm leading-6 text-zinc-600">
        Automatic sync runs independently from the scanner, imports only the normalized bundle, and keeps its own service logs.
      </p>

      <div className="mt-4 border-y border-line py-4">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <h3 className="flex items-center gap-2 text-sm font-semibold text-ink">
              <KeyRound size={16} className="text-sea" aria-hidden={true} />
              Workspace integration tokens
            </h3>
            <p className="mt-1 text-xs leading-5 text-zinc-600">Revocable, 90-day credentials with separate Core export and read-only operations scopes. Rotate when 14 days remain.</p>
          </div>
          {canManageTokens ? <div className="flex flex-wrap gap-2">
            <button
              type="button"
              onClick={() => void createToken("core:export")}
              disabled={busyAction !== null}
              className="focus-ring inline-flex h-9 items-center justify-center gap-2 rounded-md border border-line bg-white px-3 text-sm font-semibold text-ink hover:border-sea disabled:cursor-wait disabled:opacity-60"
            >
              <KeyRound size={15} aria-hidden={true} />
              Create Core token
            </button>
            <button
              type="button"
              onClick={() => void createToken("operations:read")}
              disabled={busyAction !== null}
              className="focus-ring inline-flex h-9 items-center justify-center gap-2 rounded-md border border-line bg-white px-3 text-sm font-semibold text-ink hover:border-sea disabled:cursor-wait disabled:opacity-60"
            >
              <KeyRound size={15} aria-hidden={true} />
              Create dashboard token
            </button>
          </div> : null}
        </div>

        {newToken ? (
          <div className="mt-3 rounded-md border border-amber-300 bg-amber-50 p-3">
            <p className="text-xs font-semibold uppercase text-amber-900">Shown once</p>
            <code className="mt-2 block break-all font-mono text-xs text-ink">{newToken.access_token}</code>
            <button
              type="button"
              onClick={() => copyCommand("Core export token", newToken.access_token)}
              className="focus-ring mt-3 inline-flex h-9 items-center gap-2 rounded-md bg-ink px-3 text-sm font-semibold text-white"
            >
              <Clipboard size={15} aria-hidden={true} />
              Copy token
            </button>
          </div>
        ) : null}

        {canManageTokens ? <div className="mt-3 divide-y divide-line border-y border-line">
          {tokens.length === 0 ? (
            <p className="py-3 text-sm text-zinc-600">No Core export tokens in this workspace.</p>
          ) : tokens.map((token) => (
            <div key={token.id} className="grid gap-2 py-3 text-sm sm:grid-cols-[minmax(0,1fr)_auto] sm:items-center">
              <div className="min-w-0">
                <p className="truncate font-semibold text-ink">{token.name}</p>
                <p className="mt-1 font-mono text-xs text-zinc-600">{token.scopes.join(", ")} · {token.id.slice(0, 8)}</p>
                <p className={`mt-1 text-xs ${token.rotation_recommended ? "font-semibold text-amber-800" : "text-zinc-600"}`}>
                  {token.state} · expires {new Date(token.expires_at).toLocaleDateString()}
                  {token.state === "active" ? ` · ${token.expires_in_days} day${token.expires_in_days === 1 ? "" : "s"} left` : ""}
                  {token.last_used_at ? ` · last used ${new Date(token.last_used_at).toLocaleString()}` : " · never used"}
                </p>
                <p className="mt-1 text-xs text-zinc-500">Created {new Date(token.created_at).toLocaleString()}</p>
                {token.rotation_recommended ? (
                  <p className="mt-1 flex items-center gap-1 text-xs font-semibold text-amber-800">
                    <AlertTriangle size={13} aria-hidden={true} /> Rotation recommended
                  </p>
                ) : null}
              </div>
              {token.state === "active" ? (
                <div className="flex items-center gap-2">
                  <button
                    type="button"
                    aria-label={`Rotate ${token.name} (${token.id.slice(0, 8)})`}
                    title={`Rotate ${token.name}`}
                    onClick={() => void rotateToken(token.id)}
                    disabled={busyAction !== null}
                    className="focus-ring inline-flex h-9 w-9 items-center justify-center rounded-md border border-line text-amber-800 hover:border-amber-300 hover:bg-amber-50 disabled:cursor-wait disabled:opacity-60"
                  >
                    <RefreshCw size={16} aria-hidden={true} />
                  </button>
                  <button
                    type="button"
                    aria-label={`Revoke ${token.name} (${token.id.slice(0, 8)})`}
                    title={`Revoke ${token.name}`}
                    onClick={() => revokeToken(token.id)}
                    disabled={busyAction !== null}
                    className="focus-ring inline-flex h-9 w-9 items-center justify-center rounded-md border border-line text-red-700 hover:border-red-300 hover:bg-red-50 disabled:cursor-wait disabled:opacity-60"
                  >
                    <Trash2 size={16} aria-hidden={true} />
                  </button>
                </div>
              ) : null}
            </div>
          ))}
        </div> : <p className="mt-3 text-sm text-zinc-600">Workspace owners and administrators manage integration credentials.</p>}
      </div>

      <div className="mt-4 grid grid-cols-1 gap-3 md:grid-cols-3">
        <label className="min-w-0 text-sm font-semibold text-ink">
          Edge install path
          <input
            className="focus-ring mt-2 w-full rounded-md border border-line bg-white px-3 py-2 font-mono text-sm font-normal"
            onChange={(event) => updateRoot(EDGE_ROOT_KEY, event.target.value, setEdgeRoot)}
            spellCheck={false}
            value={edgeRoot}
          />
        </label>
        <label className="min-w-0 text-sm font-semibold text-ink">
          Core install path
          <input
            className="focus-ring mt-2 w-full rounded-md border border-line bg-white px-3 py-2 font-mono text-sm font-normal"
            onChange={(event) => updateRoot(CORE_ROOT_KEY, event.target.value, setCoreRoot)}
            spellCheck={false}
            value={coreRoot}
          />
        </label>
        <label className="min-w-0 text-sm font-semibold text-ink">
          Core API URL
          <input
            className="focus-ring mt-2 w-full rounded-md border border-line bg-white px-3 py-2 font-mono text-sm font-normal"
            inputMode="url"
            onChange={(event) => updateRoot(CORE_API_URL_KEY, event.target.value, setCoreApiUrl)}
            spellCheck={false}
            value={coreApiUrl}
          />
        </label>
      </div>

      <div className="mt-4 grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-4">
        {commands.map((item) => (
          <CommandButton
            key={item.label}
            label={item.label}
            command={item.command}
            icon={item.icon}
            disabled={busyAction !== null}
            onCopy={copyCommand}
          />
        ))}
      </div>

      {message ? (
        <div className="mt-4 flex items-center gap-2 rounded-md bg-emerald-50 px-3 py-2 text-sm font-medium text-emerald-800">
          <CheckCircle2 size={16} aria-hidden={true} />
          {message}
        </div>
      ) : null}
    </section>
  );
}
type CommandButtonProps = {
  label: string;
  command: string;
  icon: ComponentType<{ size?: number; className?: string; "aria-hidden"?: boolean }>;
  disabled: boolean;
  onCopy: (label: string, command: string) => void;
};

function CommandButton({ label, command, icon: Icon, disabled, onCopy }: CommandButtonProps) {
  return (
    <button
      type="button"
      onClick={() => onCopy(label, command)}
      disabled={disabled}
      className="focus-ring grid min-h-32 min-w-0 grid-rows-[auto_1fr] rounded-md border border-line bg-paper p-3 text-left transition hover:border-sea hover:bg-white disabled:cursor-wait disabled:opacity-60"
    >
      <span className="flex items-center gap-2 text-sm font-semibold text-ink">
        <Icon size={16} className="text-sea" aria-hidden={true} />
        {label}
        <Clipboard size={14} className="ml-auto text-zinc-500" aria-hidden={true} />
      </span>
      <code className="mt-3 block overflow-hidden whitespace-pre-wrap break-words font-mono text-xs leading-5 text-zinc-700">
        {command}
      </code>
    </button>
  );
}
