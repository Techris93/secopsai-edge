"use client";

import { CheckCircle2, KeyRound, LogOut, Mail, PlugZap, ShieldCheck, UserCheck } from "lucide-react";
import { FormEvent, useEffect, useState } from "react";
import {
  apiBaseUrl,
  clearDashboardSession,
  fetchAuthIdentity,
  hasDashboardSession,
  loginDashboard,
  loginDashboardUser,
  logoutDashboard,
  requestDashboardPasswordReset,
  confirmDashboardPasswordReset,
  acceptUserInvitation,
  verifyDashboardMfa
} from "@/lib/api";

export function ApiConnectionPanel() {
  const [adminToken, setAdminToken] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [connected, setConnected] = useState(false);
  const [identity, setIdentity] = useState<string | null>(null);
  const [status, setStatus] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [recoveryToken, setRecoveryToken] = useState("");
  const [recoveryPasswords, setRecoveryPasswords] = useState({ next: "", confirm: "" });
  const [invitationToken, setInvitationToken] = useState("");
  const [invitationPasswords, setInvitationPasswords] = useState({ next: "", confirm: "" });
  const [mfaChallenge, setMfaChallenge] = useState("");
  const [mfaCode, setMfaCode] = useState("");

  useEffect(() => {
    const fragment = new URLSearchParams(window.location.hash.replace(/^#/, ""));
    const token = fragment.get("reset_token") ?? "";
    if (token) {
      setRecoveryToken(token);
    }
    const invitation = fragment.get("invitation_token") ?? "";
    if (invitation) setInvitationToken(invitation);
    if (token || invitation) {
      window.history.replaceState(null, "", `${window.location.pathname}${window.location.search}`);
    }
    const syncSession = () => {
      const session = hasDashboardSession();
      setConnected(session);
      if (session) {
        fetchAuthIdentity()
          .then((payload) => setIdentity(payload.user?.email ?? payload.subject))
          .catch(() => setIdentity(null));
      } else {
        setIdentity(null);
      }
    };
    syncSession();
    window.addEventListener("secopsai-session-changed", syncSession);
    return () => window.removeEventListener("secopsai-session-changed", syncSession);
  }, []);

  async function requestReset() {
    if (!email.trim()) {
      setStatus("Enter your operator email before requesting a reset link.");
      return;
    }
    setBusy(true);
    setStatus(null);
    try {
      await requestDashboardPasswordReset(email.trim());
      setStatus("If the account exists, a one-time reset link will arrive after the next delivery run.");
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "Unable to request password reset");
    } finally {
      setBusy(false);
    }
  }

  async function confirmReset(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (recoveryPasswords.next.length < 12) {
      setStatus("Use at least 12 characters for the new password.");
      return;
    }
    if (recoveryPasswords.next !== recoveryPasswords.confirm) {
      setStatus("The password confirmation does not match.");
      return;
    }
    setBusy(true);
    setStatus(null);
    try {
      await confirmDashboardPasswordReset(recoveryToken, recoveryPasswords.next);
      setRecoveryToken("");
      setRecoveryPasswords({ next: "", confirm: "" });
      setConnected(false);
      setIdentity(null);
      setStatus("Password reset complete. Connect with your email and new password.");
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "Unable to reset password");
    } finally {
      setBusy(false);
    }
  }

  async function confirmInvitation(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (invitationPasswords.next.length < 12) {
      setStatus("Use at least 12 characters for the account password.");
      return;
    }
    if (invitationPasswords.next !== invitationPasswords.confirm) {
      setStatus("The password confirmation does not match.");
      return;
    }
    setBusy(true);
    setStatus(null);
    try {
      await acceptUserInvitation(invitationToken, invitationPasswords.next);
      setInvitationToken("");
      setInvitationPasswords({ next: "", confirm: "" });
      setStatus("Invitation accepted. Connect with your email and password.");
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "Unable to accept invitation");
    } finally {
      setBusy(false);
    }
  }

  async function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    setStatus(null);
    try {
      const result = await loginDashboardUser(email, password);
      setPassword("");
      if (result.mfaRequired && result.mfaChallenge) {
        setMfaChallenge(result.mfaChallenge);
        setIdentity(result.user?.email ?? email);
        setStatus("Enter the code from your authenticator app or a recovery code.");
        return;
      }
      setConnected(true);
      setIdentity(result.user?.email ?? email);
      setStatus("Connected. Refresh dashboard pages to load live API data.");
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "Unable to connect");
    } finally {
      setBusy(false);
    }
  }

  async function confirmMfa(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    setStatus(null);
    try {
      const user = await verifyDashboardMfa(mfaChallenge, mfaCode);
      setMfaChallenge("");
      setMfaCode("");
      setConnected(true);
      setIdentity(user?.email ?? identity ?? email);
      setStatus("Multi-factor authentication verified. Live API access is connected.");
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "Unable to verify authentication code");
    } finally {
      setBusy(false);
    }
  }

  async function onLegacySubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    setStatus(null);
    try {
      await loginDashboard(adminToken);
      setAdminToken("");
      setConnected(true);
      setIdentity("admin-token");
      setStatus("Connected with legacy admin token session.");
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "Unable to connect");
    } finally {
      setBusy(false);
    }
  }

  async function disconnect() {
    setBusy(true);
    try {
      await logoutDashboard();
    } catch {
      clearDashboardSession();
    } finally {
      setBusy(false);
      setConnected(false);
      setIdentity(null);
      setMfaChallenge("");
      setMfaCode("");
      setStatus("Disconnected from the API session.");
    }
  }

  return (
    <section className="min-w-0 rounded-lg border border-line bg-white p-4 shadow-panel">
      <div className="flex items-center gap-2">
        <PlugZap size={20} className="text-sea" aria-hidden="true" />
        <h2 className="text-lg font-semibold text-ink">API Connection</h2>
      </div>
      <p className="mt-2 text-sm leading-6 text-zinc-600">
        Connect this static dashboard to the SecOpsAI Edge API with a dashboard user session. Keep
        the admin token path for scripts, cron, and emergency recovery.
      </p>

      <dl className="mt-4 grid grid-cols-1 gap-2 text-sm sm:grid-cols-[8rem_minmax(0,1fr)]">
        <dt className="font-medium text-zinc-600">API URL</dt>
        <dd className="break-all font-mono text-ink">{apiBaseUrl()}</dd>
        <dt className="font-medium text-zinc-600">Session</dt>
        <dd className={connected ? "font-medium text-sea" : "font-medium text-amber"}>
          {connected ? `Connected${identity ? ` as ${identity}` : ""}` : "Not connected"}
        </dd>
      </dl>

      {recoveryToken ? (
        <form className="mt-4 rounded-md border border-sea/30 bg-sea/5 p-3" onSubmit={confirmReset}>
          <div className="flex items-center gap-2 text-sm font-semibold text-ink">
            <ShieldCheck size={17} className="text-sea" aria-hidden="true" />
            Complete password reset
          </div>
          <div className="mt-3 grid grid-cols-1 gap-3 sm:grid-cols-2">
            <input
              className="focus-ring min-w-0 rounded-md border border-line bg-white px-3 py-2 text-sm"
              type="password"
              autoComplete="new-password"
              minLength={12}
              placeholder="New password (12+ characters)"
              value={recoveryPasswords.next}
              onChange={(event) => setRecoveryPasswords({ ...recoveryPasswords, next: event.target.value })}
              required
            />
            <input
              className="focus-ring min-w-0 rounded-md border border-line bg-white px-3 py-2 text-sm"
              type="password"
              autoComplete="new-password"
              minLength={12}
              placeholder="Confirm new password"
              value={recoveryPasswords.confirm}
              onChange={(event) => setRecoveryPasswords({ ...recoveryPasswords, confirm: event.target.value })}
              required
            />
          </div>
          <button className="ButtonSecondary mt-3" disabled={busy} type="submit">
            <KeyRound size={16} aria-hidden="true" />Reset password
          </button>
        </form>
      ) : null}

      {invitationToken ? (
        <form className="mt-4 rounded-md border border-sea/30 bg-sea/5 p-3" onSubmit={confirmInvitation}>
          <div className="flex items-center gap-2 text-sm font-semibold text-ink">
            <UserCheck size={17} className="text-sea" aria-hidden="true" />
            Accept workspace invitation
          </div>
          <p className="mt-2 text-sm text-zinc-600">
            New operators choose a password. Existing operators confirm their current password.
          </p>
          <div className="mt-3 grid grid-cols-1 gap-3 sm:grid-cols-2">
            <input
              className="focus-ring min-w-0 rounded-md border border-line bg-white px-3 py-2 text-sm"
              type="password"
              autoComplete="new-password"
              minLength={12}
              placeholder="Account password (12+ characters)"
              value={invitationPasswords.next}
              onChange={(event) => setInvitationPasswords({ ...invitationPasswords, next: event.target.value })}
              required
            />
            <input
              className="focus-ring min-w-0 rounded-md border border-line bg-white px-3 py-2 text-sm"
              type="password"
              autoComplete="new-password"
              minLength={12}
              placeholder="Confirm account password"
              value={invitationPasswords.confirm}
              onChange={(event) => setInvitationPasswords({ ...invitationPasswords, confirm: event.target.value })}
              required
            />
          </div>
          <button className="ButtonSecondary mt-3" disabled={busy} type="submit">
            <UserCheck size={16} aria-hidden="true" />Accept invitation
          </button>
        </form>
      ) : null}

      {mfaChallenge ? (
        <form className="mt-4 rounded-md border border-sea/30 bg-sea/5 p-3" onSubmit={confirmMfa}>
          <div className="flex items-center gap-2 text-sm font-semibold text-ink">
            <ShieldCheck size={17} className="text-sea" aria-hidden="true" />
            Verify multi-factor authentication
          </div>
          <div className="mt-3 flex flex-col gap-3 sm:flex-row">
            <input
              className="focus-ring min-w-0 flex-1 rounded-md border border-line bg-white px-3 py-2 font-mono text-sm"
              value={mfaCode}
              onChange={(event) => setMfaCode(event.target.value)}
              placeholder="6-digit code or recovery code"
              autoComplete="one-time-code"
              required
            />
            <button className="ButtonSecondary" disabled={busy || mfaCode.trim().length < 6} type="submit">
              <ShieldCheck size={16} aria-hidden="true" />Verify
            </button>
          </div>
        </form>
      ) : null}

      <form className="mt-4 grid grid-cols-1 gap-3 sm:grid-cols-[minmax(0,1fr)_auto]" onSubmit={onSubmit}>
        <div className="grid min-w-0 grid-cols-1 gap-3 sm:grid-cols-2">
          <input
            className="focus-ring min-w-0 w-full rounded-md border border-line bg-white px-3 py-2 text-sm"
            value={email}
            onChange={(event) => setEmail(event.target.value)}
            placeholder="admin@example.com"
            type="email"
            autoComplete="username"
          />
          <label className="relative">
            <KeyRound
              className="absolute left-3 top-1/2 -translate-y-1/2 text-zinc-500"
              size={18}
              aria-hidden="true"
            />
            <input
              className="focus-ring w-full rounded-md border border-line bg-white py-2 pl-10 pr-3 text-sm"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              placeholder="Password"
              type="password"
              autoComplete="current-password"
            />
          </label>
        </div>
        <button
          className="focus-ring inline-flex w-full items-center justify-center gap-2 rounded-md bg-sea px-3 py-2 text-sm font-medium text-white disabled:cursor-not-allowed disabled:bg-zinc-300 sm:w-auto"
          disabled={busy || email.trim().length === 0 || password.length === 0}
          type="submit"
        >
          <CheckCircle2 size={16} aria-hidden="true" />
          {busy ? "Connecting" : "Connect"}
        </button>
      </form>

      <button
        className="focus-ring mt-3 inline-flex items-center gap-2 text-sm font-medium text-sea disabled:cursor-not-allowed disabled:text-zinc-400"
        disabled={busy || email.trim().length === 0}
        onClick={() => void requestReset()}
        type="button"
      >
        <Mail size={16} aria-hidden="true" />
        Send password reset
      </button>

      <details className="mt-4 rounded-md border border-line bg-paper p-3">
        <summary className="cursor-pointer text-sm font-semibold text-ink">Legacy admin token recovery</summary>
        <p className="mt-2 text-sm leading-6 text-zinc-600">
          Use this only for local development, automation recovery, or bootstrap flows. Do not expose
          the admin token in browser environment variables.
        </p>
        <form className="mt-3 grid grid-cols-1 gap-3 sm:grid-cols-[minmax(0,1fr)_auto]" onSubmit={onLegacySubmit}>
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
              autoComplete="off"
            />
          </label>
          <button
            className="ButtonSecondary"
            disabled={busy || adminToken.length === 0}
            type="submit"
          >
            Connect Token
          </button>
        </form>
      </details>

      <button
        className="focus-ring mt-3 inline-flex items-center gap-2 rounded-md border border-line bg-white px-3 py-2 text-sm font-medium text-ink disabled:cursor-not-allowed disabled:text-zinc-400"
        disabled={!connected}
        onClick={() => void disconnect()}
        type="button"
      >
        <LogOut size={16} aria-hidden="true" />
        Disconnect
      </button>

      {status ? <p className="mt-3 text-sm text-zinc-600" role="status">{status}</p> : null}
    </section>
  );
}
