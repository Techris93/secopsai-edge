"use client";

import { CheckCircle2, Clipboard, Download, GitBranch, ListTree, ShieldCheck, Terminal } from "lucide-react";
import type { ComponentType } from "react";
import { useMemo, useState } from "react";
import { apiBaseUrl, downloadCoreBundle } from "@/lib/api";

const EDGE_ROOT = "/Users/chrixchange/Documents/Codex/2026-06-15/i-want-to-build-this-make";
const CORE_ROOT = "/Users/chrixchange/secopsai";
const BUNDLE_PATH = `${EDGE_ROOT}/edge-bundle.json`;

export function CoreIntegrationPanel() {
  const [busyAction, setBusyAction] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  const commands = useMemo(
    () => [
      {
        label: "Copy Export",
        icon: Download,
        command: `cd ${EDGE_ROOT}\n./scripts/edge core export --cloud --output edge-bundle.json`
      },
      {
        label: "Copy Import",
        icon: GitBranch,
        command: `cd ${CORE_ROOT}\n.venv/bin/python -m secopsai.cli edge import --bundle ${BUNDLE_PATH}`
      },
      {
        label: "Copy Assets",
        icon: ListTree,
        command: `cd ${CORE_ROOT}\n.venv/bin/python -m secopsai.cli graph assets`
      },
      {
        label: "Copy Changes",
        icon: ListTree,
        command: `cd ${CORE_ROOT}\n.venv/bin/python -m secopsai.cli graph changes`
      },
      {
        label: "Copy Triage",
        icon: ShieldCheck,
        command: `cd ${CORE_ROOT}\n.venv/bin/python -m secopsai.cli triage list --source secopsai_edge`
      },
      {
        label: "Copy API Sync",
        icon: GitBranch,
        command: `cd ${CORE_ROOT}\nSECOPSAI_EDGE_API_URL=${apiBaseUrl()} \\\nSECOPSAI_EDGE_ADMIN_TOKEN=<your-admin-token> \\\n.venv/bin/python -m secopsai.cli edge sync`
      },
      {
        label: "Copy Edge Test",
        icon: Terminal,
        command: `cd ${EDGE_ROOT}\n./scripts/edge test`
      },
      {
        label: "Copy Core Test",
        icon: Terminal,
        command: `cd ${CORE_ROOT}\n.venv/bin/python -m pytest tests`
      }
    ],
    []
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

  return (
    <section className="rounded-lg border border-line bg-white p-4 shadow-panel xl:col-span-2">
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

      <div className="mt-4 grid gap-3 md:grid-cols-2 xl:grid-cols-4">
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
      className="focus-ring grid min-h-32 grid-rows-[auto_1fr] rounded-md border border-line bg-paper p-3 text-left transition hover:border-sea hover:bg-white disabled:cursor-wait disabled:opacity-60"
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
