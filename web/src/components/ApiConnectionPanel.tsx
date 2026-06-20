"use client";

import { CheckCircle2, KeyRound, LogOut, PlugZap } from "lucide-react";
import { FormEvent, useEffect, useState } from "react";
import {
  apiBaseUrl,
  clearDashboardSession,
  hasDashboardSession,
  loginDashboard
} from "@/lib/api";

export function ApiConnectionPanel() {
  const [adminToken, setAdminToken] = useState("");
  const [connected, setConnected] = useState(false);
  const [status, setStatus] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    setConnected(hasDashboardSession());
  }, []);

  async function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    setStatus(null);
    try {
      await loginDashboard(adminToken);
      setAdminToken("");
      setConnected(true);
      setStatus("Connected. Refresh dashboard pages to load live API data.");
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "Unable to connect");
    } finally {
      setBusy(false);
    }
  }

  function disconnect() {
    clearDashboardSession();
    setConnected(false);
    setStatus("Disconnected from the API session.");
  }

  return (
    <section className="rounded-lg border border-line bg-white p-4 shadow-panel">
      <div className="flex items-center gap-2">
        <PlugZap size={20} className="text-sea" aria-hidden="true" />
        <h2 className="text-lg font-semibold text-ink">API Connection</h2>
      </div>
      <p className="mt-2 text-sm leading-6 text-zinc-600">
        Connect this static dashboard to the SecOpsAI Edge API without exposing an admin token in
        the hosted JavaScript bundle.
      </p>

      <dl className="mt-4 grid gap-2 text-sm sm:grid-cols-[8rem_1fr]">
        <dt className="font-medium text-zinc-600">API URL</dt>
        <dd className="font-mono text-ink">{apiBaseUrl()}</dd>
        <dt className="font-medium text-zinc-600">Session</dt>
        <dd className={connected ? "font-medium text-sea" : "font-medium text-amber"}>
          {connected ? "Connected" : "Not connected"}
        </dd>
      </dl>

      <form className="mt-4 grid gap-3 sm:grid-cols-[1fr_auto]" onSubmit={onSubmit}>
        <label className="relative">
          <KeyRound
            className="absolute left-3 top-1/2 -translate-y-1/2 text-zinc-500"
            size={18}
            aria-hidden="true"
          />
          <input
            className="focus-ring w-full rounded-md border border-line bg-white py-2 pl-10 pr-3 text-sm"
            value={adminToken}
            onChange={(event) => setAdminToken(event.target.value)}
            placeholder="Enter API admin token"
            type="password"
            autoComplete="current-password"
          />
        </label>
        <button
          className="focus-ring inline-flex items-center justify-center gap-2 rounded-md bg-sea px-3 py-2 text-sm font-medium text-white disabled:cursor-not-allowed disabled:bg-zinc-300"
          disabled={busy || adminToken.length === 0}
          type="submit"
        >
          <CheckCircle2 size={16} aria-hidden="true" />
          {busy ? "Connecting" : "Connect"}
        </button>
      </form>

      <button
        className="focus-ring mt-3 inline-flex items-center gap-2 rounded-md border border-line bg-white px-3 py-2 text-sm font-medium text-ink disabled:cursor-not-allowed disabled:text-zinc-400"
        disabled={!connected}
        onClick={disconnect}
        type="button"
      >
        <LogOut size={16} aria-hidden="true" />
        Disconnect
      </button>

      {status ? <p className="mt-3 text-sm text-zinc-600">{status}</p> : null}
    </section>
  );
}
