"use client";

import { Check, Copy, type LucideIcon } from "lucide-react";
import { useState } from "react";

export function CopyCommand({ command, icon: Icon }: { command: string; icon: LucideIcon }) {
  const [copied, setCopied] = useState(false);

  async function copy() {
    try {
      await navigator.clipboard.writeText(command);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 1800);
    } catch {
      setCopied(false);
    }
  }

  return (
    <button
      className="focus-ring flex w-full items-center gap-3 rounded-md bg-ink p-3 text-left text-sm text-white transition hover:bg-zinc-800"
      onClick={() => void copy()}
      title="Copy command"
      type="button"
    >
      <Icon size={17} className="shrink-0 text-teal-200" aria-hidden="true" />
      <code className="min-w-0 flex-1 overflow-x-auto whitespace-nowrap">{command}</code>
      {copied ? <Check size={16} className="shrink-0 text-teal-200" aria-hidden="true" /> : <Copy size={16} className="shrink-0 text-zinc-300" aria-hidden="true" />}
      <span className="sr-only">{copied ? "Copied" : "Copy command"}</span>
    </button>
  );
}
