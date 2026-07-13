"use client";

import { Clipboard, KeyRound, MailWarning, RotateCcw, ShieldCheck, ShieldOff, UserCog, UserPlus, X } from "lucide-react";
import { FormEvent, useEffect, useState } from "react";
import {
  changeDashboardPassword,
  beginDashboardMfa,
  createUserInvitation,
  disableDashboardMfa,
  enableDashboardMfa,
  fetchAuthIdentity,
  listAccountAccessDeliveries,
  listUserInvitations,
  listUsers,
  regenerateDashboardMfaRecoveryCodes,
  resetUserMfa,
  retryAccountAccessDelivery,
  revokeUserInvitation,
  updateUser
} from "@/lib/api";
import { copyText } from "@/lib/clipboard";
import type { AccountAccessDelivery, User, UserInvitation } from "@/lib/types";

export function AccountManagementPanel() {
  const [users, setUsers] = useState<User[]>([]);
  const [accessDeliveries, setAccessDeliveries] = useState<AccountAccessDelivery[]>([]);
  const [invitations, setInvitations] = useState<UserInvitation[]>([]);
  const [currentUser, setCurrentUser] = useState<User | null>(null);
  const [currentRole, setCurrentRole] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [invite, setInvite] = useState({ email: "", role: "viewer" });
  const [passwords, setPasswords] = useState({ current: "", next: "" });
  const [mfaCredentials, setMfaCredentials] = useState({ password: "", code: "" });
  const [mfaSetup, setMfaSetup] = useState<{ secret: string; provisioning_uri: string; expires_at: string } | null>(null);
  const [recoveryCodes, setRecoveryCodes] = useState<string[]>([]);

  async function load() {
    try {
      const identity = await fetchAuthIdentity();
      setCurrentUser(identity.user ?? null);
      setCurrentRole(identity.role);
      if (["owner", "admin"].includes(identity.role)) {
        const [loadedUsers, loadedDeliveries, loadedInvitations] = await Promise.all([
          listUsers(),
          listAccountAccessDeliveries(),
          listUserInvitations()
        ]);
        setUsers(loadedUsers);
        setAccessDeliveries(loadedDeliveries);
        setInvitations(loadedInvitations);
      } else {
        setUsers([]);
        setAccessDeliveries([]);
        setInvitations([]);
      }
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Unable to load users");
    }
  }

  useEffect(() => { void load(); }, []);
  const canManage = currentRole === "owner" || currentRole === "admin";

  async function addUser(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    try {
      await createUserInvitation(invite);
      setInvite({ email: "", role: "viewer" });
      setMessage("Invitation queued. The one-time link will be delivered by the account email worker.");
      await load();
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Unable to create user");
    } finally {
      setBusy(false);
    }
  }

  async function revokeInvitation(invitationId: string) {
    setBusy(true);
    try {
      await revokeUserInvitation(invitationId);
      setMessage("Invitation revoked.");
      await load();
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Unable to revoke invitation");
    } finally {
      setBusy(false);
    }
  }

  async function changePassword(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    try {
      await changeDashboardPassword(passwords.current, passwords.next);
      setMessage("Password changed. All sessions were revoked; reconnect above with the new password.");
      setPasswords({ current: "", next: "" });
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Unable to change password");
    } finally {
      setBusy(false);
    }
  }

  async function changeUser(user: User, payload: Partial<{ role: string; active: boolean; password: string }>) {
    setBusy(true);
    try {
      await updateUser(user.id, payload);
      setMessage("User security settings updated; existing sessions were revoked.");
      await load();
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Unable to update user");
    } finally {
      setBusy(false);
    }
  }

  async function resetMfaForUser(user: User) {
    if (!window.confirm(`Reset MFA for ${user.email}? Their current authenticator and recovery codes will stop working.`)) return;
    setBusy(true);
    try {
      await resetUserMfa(user.id);
      setMessage(`MFA reset for ${user.email}. Existing sessions were revoked.`);
      await load();
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Unable to reset MFA");
    } finally {
      setBusy(false);
    }
  }

  async function retryAccessDelivery(deliveryId: string) {
    setBusy(true);
    try {
      const delivery = await retryAccountAccessDelivery(deliveryId);
      setMessage(`Recovery email ${delivery.status}.`);
      await load();
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Unable to retry recovery email");
    } finally {
      setBusy(false);
    }
  }

  async function startMfaSetup() {
    if (!mfaCredentials.password) {
      setMessage("Enter your current password before starting MFA setup.");
      return;
    }
    setBusy(true);
    try {
      setMfaSetup(await beginDashboardMfa(mfaCredentials.password));
      setRecoveryCodes([]);
      setMessage("Add the secret to your authenticator, then enter its current code.");
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Unable to start MFA setup");
    } finally {
      setBusy(false);
    }
  }

  async function confirmMfaSetup() {
    setBusy(true);
    try {
      const codes = await enableDashboardMfa(mfaCredentials.code);
      setRecoveryCodes(codes);
      setMfaSetup(null);
      setMfaCredentials({ password: "", code: "" });
      setMessage("MFA enabled. Store the recovery codes now; they are shown only once. Reconnect after saving them.");
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Unable to enable MFA");
    } finally {
      setBusy(false);
    }
  }

  async function regenerateRecoveryCodes() {
    setBusy(true);
    try {
      const codes = await regenerateDashboardMfaRecoveryCodes(
        mfaCredentials.password,
        mfaCredentials.code
      );
      setRecoveryCodes(codes);
      setMfaCredentials({ password: "", code: "" });
      setMessage("Recovery codes replaced. Previous unused codes no longer work.");
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Unable to replace recovery codes");
    } finally {
      setBusy(false);
    }
  }

  async function turnOffMfa() {
    setBusy(true);
    try {
      await disableDashboardMfa(mfaCredentials.password, mfaCredentials.code);
      setRecoveryCodes([]);
      setMfaSetup(null);
      setMfaCredentials({ password: "", code: "" });
      setMessage("MFA disabled. Existing sessions were revoked; reconnect with your password.");
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Unable to disable MFA");
    } finally {
      setBusy(false);
    }
  }

  async function copyRecoveryCodes() {
    const copied = await copyText(recoveryCodes.join("\n"));
    setMessage(copied ? "Recovery codes copied." : "Clipboard access was blocked. Select the codes and store them securely.");
  }

  async function copyMfaSetup() {
    if (!mfaSetup) return;
    const copied = await copyText(mfaSetup.provisioning_uri);
    setMessage(copied ? "Authenticator setup URI copied." : "Clipboard access was blocked. Enter the displayed secret manually.");
  }

  return (
    <section className="min-w-0 rounded-lg border border-line bg-white p-4 shadow-panel xl:col-span-2">
      <div className="flex items-center gap-2">
        <UserCog size={20} className="text-sea" aria-hidden="true" />
        <h2 className="text-lg font-semibold text-ink">Users & Sessions</h2>
      </div>
      <p className="mt-2 text-sm text-zinc-600">Manage pilot access and revoke sessions when credentials or roles change.</p>

      {canManage ? <form className="mt-4 grid grid-cols-1 gap-3 md:grid-cols-[minmax(0,1fr)_9rem_auto]" onSubmit={addUser}>
        <input aria-label="Invitation email" className="focus-ring min-w-0 rounded-md border border-line px-3 py-2 text-sm" type="email" placeholder="user@example.com" value={invite.email} onChange={(event) => setInvite({ ...invite, email: event.target.value })} required />
        <select aria-label="Invitation role" className="focus-ring rounded-md border border-line px-3 py-2 text-sm" value={invite.role} onChange={(event) => setInvite({ ...invite, role: event.target.value })}>
          <option value="viewer">Viewer</option><option value="admin">Admin</option>{currentRole === "owner" ? <option value="owner">Owner</option> : null}
        </select>
        <button className="focus-ring inline-flex items-center justify-center gap-2 rounded-md bg-sea px-3 py-2 text-sm font-semibold text-white disabled:bg-zinc-300" disabled={busy} type="submit"><UserPlus size={16} aria-hidden="true" />Invite</button>
      </form> : <p className="mt-4 rounded-md border border-line bg-paper px-3 py-2 text-sm text-zinc-600">Viewer access is read-only. Workspace owners and administrators manage membership.</p>}

      {canManage && invitations.some((invitation) => invitation.state === "pending") ? (
        <div className="mt-4 border-t border-line pt-4">
          <h3 className="text-sm font-semibold text-ink">Pending invitations</h3>
          <div aria-label="Scrollable pending invitation table" className="focus-ring mt-2 overflow-x-auto" role="region" tabIndex={0}>
            <table className="w-full min-w-[620px] text-left text-sm">
              <thead className="text-xs uppercase text-zinc-600"><tr><th className="py-2 pr-3">Account</th><th className="py-2 pr-3">Role</th><th className="py-2 pr-3">Delivery</th><th className="py-2 pr-3">Expires</th><th className="py-2">Action</th></tr></thead>
              <tbody className="divide-y divide-line">
                {invitations.filter((invitation) => invitation.state === "pending").map((invitation) => (
                  <tr key={invitation.id}>
                    <td className="py-2 pr-3 font-medium text-ink">{invitation.email}</td>
                    <td className="py-2 pr-3 text-zinc-600">{invitation.role}</td>
                    <td className="py-2 pr-3 text-zinc-600">{invitation.delivery_status}</td>
                    <td className="py-2 pr-3 text-zinc-600">{new Date(invitation.expires_at).toLocaleString()}</td>
                    <td className="py-2"><button className="ButtonSecondary" disabled={busy} type="button" onClick={() => void revokeInvitation(invitation.id)}><X size={15} aria-hidden="true" />Revoke</button></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      ) : null}

      {canManage ? <div aria-label="Scrollable user and session table" className="focus-ring mt-4 overflow-x-auto rounded-md border border-line" role="region" tabIndex={0}>
        <table className="w-full min-w-[720px] text-left text-sm">
          <thead className="bg-paper text-xs uppercase text-zinc-600"><tr><th className="px-3 py-2">User</th><th className="px-3 py-2">Role</th><th className="px-3 py-2">State</th><th className="px-3 py-2">MFA</th><th className="px-3 py-2">Last login</th><th className="px-3 py-2">Actions</th></tr></thead>
          <tbody className="divide-y divide-line">
            {users.map((user) => <UserRow key={user.id} user={user} busy={busy} actorRole={currentRole} currentUserId={currentUser?.id ?? null} onChange={changeUser} onResetMfa={resetMfaForUser} />)}
            {!users.length ? <tr><td colSpan={6} className="px-3 py-4 text-zinc-600">Connect an administrator session to manage users.</td></tr> : null}
          </tbody>
        </table>
      </div> : null}

      {canManage ? (
        <div className="mt-5">
          <div className="flex items-center gap-2">
            <MailWarning size={17} className="text-amber" aria-hidden="true" />
            <h3 className="text-sm font-semibold text-ink">Account email delivery</h3>
          </div>
          <div aria-label="Scrollable account delivery table" className="focus-ring mt-3 overflow-x-auto rounded-md border border-line" role="region" tabIndex={0}>
            <table className="w-full min-w-[680px] text-left text-sm">
              <thead className="bg-paper text-xs uppercase text-zinc-600"><tr><th className="px-3 py-2">Account</th><th className="px-3 py-2">Purpose</th><th className="px-3 py-2">State</th><th className="px-3 py-2">Attempts</th><th className="px-3 py-2">Detail</th><th className="px-3 py-2">Action</th></tr></thead>
              <tbody className="divide-y divide-line">
                {accessDeliveries.slice(0, 10).map((delivery) => (
                  <tr key={delivery.id}>
                    <td className="px-3 py-3 font-medium text-ink">{delivery.email}</td>
                    <td className="px-3 py-3 text-zinc-600">{delivery.purpose.replaceAll("_", " ")}</td>
                    <td className="px-3 py-3">{delivery.status}</td>
                    <td className="px-3 py-3 text-zinc-600">{delivery.attempts}/{delivery.max_attempts}</td>
                    <td className="max-w-xs px-3 py-3 text-zinc-600">{delivery.detail ?? "Waiting for delivery"}</td>
                    <td className="px-3 py-3">
                      <button className="ButtonSecondary" type="button" disabled={busy || delivery.status === "delivered"} onClick={() => void retryAccessDelivery(delivery.id)}>
                        <RotateCcw size={15} aria-hidden="true" />Retry
                      </button>
                    </td>
                  </tr>
                ))}
                {!accessDeliveries.length ? <tr><td colSpan={6} className="px-3 py-4 text-zinc-600">No account emails have been queued.</td></tr> : null}
              </tbody>
            </table>
          </div>
        </div>
      ) : null}

      {currentUser ? (
        <div className="mt-5 border-t border-line pt-5">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <div className="flex items-center gap-2">
                <ShieldCheck size={17} className="text-sea" aria-hidden="true" />
                <h3 className="text-sm font-semibold text-ink">Multi-factor authentication</h3>
              </div>
              <p className="mt-1 text-sm text-zinc-600">
                {currentUser.mfa_enabled ? "Authenticator protection is enabled." : "Protect this operator account with an authenticator app."}
              </p>
            </div>
            <span className={currentUser.mfa_enabled ? "rounded border border-emerald-200 bg-emerald-50 px-2 py-1 text-xs font-medium text-emerald-800" : "rounded border border-line bg-paper px-2 py-1 text-xs font-medium text-zinc-600"}>
              {currentUser.mfa_enabled ? "Enabled" : "Not enabled"}
            </span>
          </div>

          <div className="mt-3 grid grid-cols-1 gap-3 md:grid-cols-2">
            <input
              aria-label="Current password for MFA"
              className="focus-ring min-w-0 rounded-md border border-line px-3 py-2 text-sm"
              type="password"
              autoComplete="current-password"
              placeholder="Current password"
              value={mfaCredentials.password}
              onChange={(event) => setMfaCredentials({ ...mfaCredentials, password: event.target.value })}
            />
            <input
              aria-label="MFA verification code"
              className="focus-ring min-w-0 rounded-md border border-line px-3 py-2 font-mono text-sm"
              autoComplete="one-time-code"
              placeholder="6-digit code or recovery code"
              value={mfaCredentials.code}
              onChange={(event) => setMfaCredentials({ ...mfaCredentials, code: event.target.value })}
            />
          </div>

          {mfaSetup ? (
            <div className="mt-4 border-l-2 border-sea pl-4">
              <p className="text-sm font-semibold text-ink">Authenticator setup secret</p>
              <code className="mt-2 block break-all text-sm text-zinc-700">{mfaSetup.secret}</code>
              <p className="mt-2 text-xs text-zinc-500">Setup expires {new Date(mfaSetup.expires_at).toLocaleString()}.</p>
              <div className="mt-3 flex flex-wrap gap-2">
                <button className="ButtonSecondary" disabled={busy} type="button" onClick={() => void copyMfaSetup()}>
                  <Clipboard size={15} aria-hidden="true" />Copy setup URI
                </button>
                <button className="ButtonSecondary" disabled={busy || mfaCredentials.code.trim().length < 6} type="button" onClick={() => void confirmMfaSetup()}>
                  <ShieldCheck size={16} aria-hidden="true" />Enable MFA
                </button>
              </div>
            </div>
          ) : null}

          <div className="mt-3 flex flex-wrap gap-2">
            {!currentUser.mfa_enabled && !mfaSetup && !recoveryCodes.length ? (
              <button className="ButtonSecondary" disabled={busy || !mfaCredentials.password} type="button" onClick={() => void startMfaSetup()}>
                <ShieldCheck size={16} aria-hidden="true" />Start setup
              </button>
            ) : null}
            {currentUser.mfa_enabled ? (
              <>
                <button className="ButtonSecondary" disabled={busy || !mfaCredentials.password || mfaCredentials.code.trim().length < 6} type="button" onClick={() => void regenerateRecoveryCodes()}>
                  <RotateCcw size={16} aria-hidden="true" />Replace recovery codes
                </button>
                <button className="ButtonSecondary" disabled={busy || !mfaCredentials.password || mfaCredentials.code.trim().length < 6} type="button" onClick={() => void turnOffMfa()}>
                  <ShieldOff size={16} aria-hidden="true" />Disable MFA
                </button>
              </>
            ) : null}
          </div>

          {recoveryCodes.length ? (
            <div className="mt-4 border-l-2 border-amber pl-4">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <p className="text-sm font-semibold text-ink">One-use recovery codes</p>
                <button className="ButtonSecondary" type="button" onClick={() => void copyRecoveryCodes()}>
                  <Clipboard size={15} aria-hidden="true" />Copy codes
                </button>
              </div>
              <div className="mt-3 grid grid-cols-2 gap-2 font-mono text-sm sm:grid-cols-5">
                {recoveryCodes.map((code) => <code key={code}>{code}</code>)}
              </div>
            </div>
          ) : null}
        </div>
      ) : null}

      {currentUser ? (
        <form className="mt-5 grid grid-cols-1 gap-3 md:grid-cols-[minmax(0,1fr)_minmax(0,1fr)_auto]" onSubmit={changePassword}>
          <input aria-label="Current account password" className="focus-ring min-w-0 rounded-md border border-line px-3 py-2 text-sm" type="password" placeholder="Current password" value={passwords.current} onChange={(event) => setPasswords({ ...passwords, current: event.target.value })} required />
          <input aria-label="New account password" className="focus-ring min-w-0 rounded-md border border-line px-3 py-2 text-sm" type="password" placeholder="New password (12+ characters)" minLength={12} value={passwords.next} onChange={(event) => setPasswords({ ...passwords, next: event.target.value })} required />
          <button className="ButtonSecondary" disabled={busy} type="submit"><KeyRound size={16} aria-hidden="true" />Change my password</button>
        </form>
      ) : null}
      {message ? <p className="mt-3 rounded-md bg-paper px-3 py-2 text-sm text-ink">{message}</p> : null}
    </section>
  );
}

function UserRow({ user, busy, actorRole, currentUserId, onChange, onResetMfa }: { user: User; busy: boolean; actorRole: string | null; currentUserId: string | null; onChange: (user: User, payload: Partial<{ role: string; active: boolean; password: string }>) => Promise<void>; onResetMfa: (user: User) => Promise<void> }) {
  return (
    <tr>
      <td className="px-3 py-3 font-medium text-ink">{user.email}</td>
      <td className="px-3 py-3"><select aria-label={`Role for ${user.email}`} className="focus-ring rounded border border-line px-2 py-1" value={user.role} disabled={busy || (user.role === "owner" && actorRole !== "owner")} onChange={(event) => void onChange(user, { role: event.target.value })}><option value="viewer">Viewer</option><option value="admin">Admin</option>{actorRole === "owner" ? <option value="owner">Owner</option> : null}</select></td>
      <td className="px-3 py-3">{user.active ? "Active" : "Disabled"}</td>
      <td className="px-3 py-3">{user.mfa_enabled ? "Enabled" : "Not enabled"}</td>
      <td className="px-3 py-3 text-zinc-600">{user.last_login_at ? new Date(user.last_login_at).toLocaleString() : "Never"}</td>
      <td className="px-3 py-3"><div className="flex flex-wrap gap-2"><button className="ButtonSecondary" type="button" disabled={busy} onClick={() => void onChange(user, { active: !user.active })}>{user.active ? "Disable" : "Enable"}</button>{actorRole === "owner" && user.mfa_enabled && user.id !== currentUserId ? <button className="ButtonSecondary" type="button" disabled={busy} onClick={() => void onResetMfa(user)}><ShieldOff size={15} aria-hidden="true" />Reset MFA</button> : null}</div></td>
    </tr>
  );
}
