"use client";

import { Check, Copy, TriangleAlert, type LucideIcon } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { copyText } from "@/lib/clipboard";

type CopyState = "idle" | "copied" | "failed";

export function CopyCommand({ command, icon: Icon }: { command: string; icon: LucideIcon }) {
  const [copyState, setCopyState] = useState<CopyState>("idle");
  const resetTimer = useRef<number | null>(null);

  useEffect(
    () => () => {
      if (resetTimer.current !== null) window.clearTimeout(resetTimer.current);
    },
    []
  );

  async function copy() {
    const copied = await copyText(command);
    setCopyState(copied ? "copied" : "failed");
    if (resetTimer.current !== null) window.clearTimeout(resetTimer.current);
    resetTimer.current = window.setTimeout(() => setCopyState("idle"), 1800);
  }

  const statusLabel = copyState === "copied" ? "Copied" : copyState === "failed" ? "Copy failed" : "Copy command";

  return (
    <button
      className="focus-ring flex w-full items-center gap-3 rounded-md bg-ink p-3 text-left text-sm text-white transition hover:bg-zinc-800"
      onClick={() => void copy()}
      title={statusLabel}
      type="button"
    >
      <Icon size={17} className="shrink-0 text-teal-200" aria-hidden="true" />
      <code className="min-w-0 flex-1 overflow-x-auto whitespace-nowrap">{command}</code>
      {copyState === "copied" ? <Check size={16} className="shrink-0 text-teal-200" aria-hidden="true" /> : null}
      {copyState === "failed" ? <TriangleAlert size={16} className="shrink-0 text-rose-300" aria-hidden="true" /> : null}
      {copyState === "idle" ? <Copy size={16} className="shrink-0 text-zinc-300" aria-hidden="true" /> : null}
      <span className="sr-only" aria-live="polite">{statusLabel}</span>
    </button>
  );
}
