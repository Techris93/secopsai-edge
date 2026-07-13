"use client";

import { CheckCircle2, Clipboard, Download, GitBranch, KeyRound, LifeBuoy, ListTree, ShieldCheck, Terminal, Trash2 } from "lucide-react";
import type { ComponentType } from "react";
import { useEffect, useMemo, useState } from "react";
import { apiBaseUrl, createIntegrationToken, downloadCoreBundle, fetchAuthIdentity, listIntegrationTokens, revokeIntegrationToken } from "@/lib/api";
import type { IntegrationToken, IntegrationTokenSecret } from "@/lib/types";

const DEFAULT_EDGE_ROOT = process.env.NEXT_PUBLIC_EDGE_ROOT ?? "$HOME/secopsai-edge";
const DEFAULT_CORE_ROOT = process.env.NEXT_PUBLIC_CORE_ROOT ?? "$HOME/secopsai";
const EDGE_ROOT_KEY = "secopsai_edge_root";
const CORE_ROOT_KEY = "secopsai_core_root";

export function CoreIntegrationPanel() {
  const [busyAction, setBusyAction] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [edgeRoot, setEdgeRoot] = useState(DEFAULT_EDGE_ROOT);
  const [coreRoot, setCoreRoot] = useState(DEFAULT_CORE_ROOT);
  const [tokens, setTokens] = useState<IntegrationToken[]>([]);
  const [newToken, setNewToken] = useState<IntegrationTokenSecret | null>(null);
  const [canManageTokens, setCanManageTokens] = useState(false);

  useEffect(() => {
    setEdgeRoot(window.localStorage.getItem(EDGE_ROOT_KEY) || DEFAULT_EDGE_ROOT);
    setCoreRoot(window.localStorage.getItem(CORE_ROOT_KEY) || DEFAULT_CORE_ROOT);
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
        label: "Install Auto Sync",
        icon: GitBranch,
        command: `cd "${edgeRoot}"\nSECOPSAI_EDGE_CORE_TOKEN="$(python3 -c 'import getpass; print(getpass.getpass("Core export token: "))')"; export SECOPSAI_EDGE_CORE_TOKEN\n./scripts/edge core sync-service install --cloud --core-root "${coreRoot}" --interval 300\nunset SECOPSAI_EDGE_CORE_TOKEN\n./scripts/edge core sync-service start`
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
    [coreRoot, edgeRoot]
  );

  async function copyCommand(label: string, command: string) {
    setBusyAction(label);
    try {
      await navigator.clipboard.writeText(command);
      setMessage(`${label} copied`);
    } catch {
      setMessage("Clipboard unavailable");
    } finally {
      setBusyAction(null);
    }
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

  async function createToken() {
    setBusyAction("create-token");
    try {
      const created = await createIntegrationToken();
      setNewToken(created);
      setTokens((current) => [created, ...current.filter((item) => item.id !== created.id)]);
      setMessage("Core export token created. Copy it now; it will not be shown again.");
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Unable to create Core export token");
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
      setMessage("Core export token revoked");
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Unable to revoke Core export token");
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
              Workspace Core export tokens
            </h3>
            <p className="mt-1 text-xs leading-5 text-zinc-600">Revocable, 90-day credentials limited to normalized Core export.</p>
          </div>
          {canManageTokens ? <button
            type="button"
            onClick={createToken}
            disabled={busyAction !== null}
            className="focus-ring inline-flex h-9 items-center justify-center gap-2 rounded-md border border-line bg-white px-3 text-sm font-semibold text-ink hover:border-sea disabled:cursor-wait disabled:opacity-60"
          >
            <KeyRound size={15} aria-hidden={true} />
            Create token
          </button> : null}
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
                <p className="mt-1 text-xs text-zinc-600">
                  {token.state} · expires {new Date(token.expires_at).toLocaleDateString()}
                  {token.last_used_at ? ` · last used ${new Date(token.last_used_at).toLocaleString()}` : " · never used"}
                </p>
              </div>
              {token.state === "active" ? (
                <button
                  type="button"
                  aria-label={`Revoke ${token.name}`}
                  title={`Revoke ${token.name}`}
                  onClick={() => revokeToken(token.id)}
                  disabled={busyAction !== null}
                  className="focus-ring inline-flex h-9 w-9 items-center justify-center rounded-md border border-line text-red-700 hover:border-red-300 hover:bg-red-50 disabled:cursor-wait disabled:opacity-60"
                >
                  <Trash2 size={16} aria-hidden={true} />
                </button>
              ) : null}
            </div>
          ))}
        </div> : <p className="mt-3 text-sm text-zinc-600">Workspace owners and administrators manage integration credentials.</p>}
      </div>

      <div className="mt-4 grid grid-cols-1 gap-3 md:grid-cols-2">
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
