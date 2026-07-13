"use client";

import { KeyRound, MailWarning, RotateCcw, UserCog, UserPlus } from "lucide-react";
import { FormEvent, useEffect, useState } from "react";
import {
  changeDashboardPassword,
  createUser,
  fetchAuthIdentity,
  listAccountAccessDeliveries,
  listUsers,
  retryAccountAccessDelivery,
  updateUser
} from "@/lib/api";
import type { AccountAccessDelivery, User } from "@/lib/types";

export function AccountManagementPanel() {
  const [users, setUsers] = useState<User[]>([]);
  const [accessDeliveries, setAccessDeliveries] = useState<AccountAccessDelivery[]>([]);
  const [currentUser, setCurrentUser] = useState<User | null>(null);
  const [currentRole, setCurrentRole] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [invite, setInvite] = useState({ email: "", password: "", role: "viewer" });
  const [passwords, setPasswords] = useState({ current: "", next: "" });

  async function load() {
    try {
      const identity = await fetchAuthIdentity();
      setCurrentUser(identity.user ?? null);
      setCurrentRole(identity.role);
      if (["owner", "admin"].includes(identity.role)) {
        const [loadedUsers, loadedDeliveries] = await Promise.all([
          listUsers(),
          listAccountAccessDeliveries()
        ]);
        setUsers(loadedUsers);
        setAccessDeliveries(loadedDeliveries);
      } else {
        setUsers([]);
        setAccessDeliveries([]);
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
      await createUser(invite);
      setInvite({ email: "", password: "", role: "viewer" });
      setMessage("User created. Share the temporary password through a secure channel.");
      await load();
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Unable to create user");
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

  return (
    <section className="min-w-0 rounded-lg border border-line bg-white p-4 shadow-panel xl:col-span-2">
      <div className="flex items-center gap-2">
        <UserCog size={20} className="text-sea" aria-hidden="true" />
        <h2 className="text-lg font-semibold text-ink">Users & Sessions</h2>
      </div>
      <p className="mt-2 text-sm text-zinc-600">Manage pilot access and revoke sessions when credentials or roles change.</p>

      {canManage ? <form className="mt-4 grid grid-cols-1 gap-3 md:grid-cols-[minmax(0,1fr)_minmax(0,1fr)_9rem_auto]" onSubmit={addUser}>
        <input className="focus-ring min-w-0 rounded-md border border-line px-3 py-2 text-sm" type="email" placeholder="user@example.com" value={invite.email} onChange={(event) => setInvite({ ...invite, email: event.target.value })} required />
        <input className="focus-ring min-w-0 rounded-md border border-line px-3 py-2 text-sm" type="password" placeholder="Temporary password" minLength={12} value={invite.password} onChange={(event) => setInvite({ ...invite, password: event.target.value })} required />
        <select className="focus-ring rounded-md border border-line px-3 py-2 text-sm" value={invite.role} onChange={(event) => setInvite({ ...invite, role: event.target.value })}>
          <option value="viewer">Viewer</option><option value="admin">Admin</option>{currentRole === "owner" ? <option value="owner">Owner</option> : null}
        </select>
        <button className="focus-ring inline-flex items-center justify-center gap-2 rounded-md bg-sea px-3 py-2 text-sm font-semibold text-white disabled:bg-zinc-300" disabled={busy} type="submit"><UserPlus size={16} aria-hidden="true" />Add user</button>
      </form> : <p className="mt-4 rounded-md border border-line bg-paper px-3 py-2 text-sm text-zinc-600">Viewer access is read-only. Workspace owners and administrators manage membership.</p>}

      {canManage ? <div className="mt-4 overflow-x-auto rounded-md border border-line">
        <table className="w-full min-w-[720px] text-left text-sm">
          <thead className="bg-paper text-xs uppercase text-zinc-600"><tr><th className="px-3 py-2">User</th><th className="px-3 py-2">Role</th><th className="px-3 py-2">State</th><th className="px-3 py-2">Last login</th><th className="px-3 py-2">Actions</th></tr></thead>
          <tbody className="divide-y divide-line">
            {users.map((user) => <UserRow key={user.id} user={user} busy={busy} actorRole={currentRole} onChange={changeUser} />)}
            {!users.length ? <tr><td colSpan={5} className="px-3 py-4 text-zinc-600">Connect an administrator session to manage users.</td></tr> : null}
          </tbody>
        </table>
      </div> : null}

      {canManage ? (
        <div className="mt-5">
          <div className="flex items-center gap-2">
            <MailWarning size={17} className="text-amber" aria-hidden="true" />
            <h3 className="text-sm font-semibold text-ink">Account email delivery</h3>
          </div>
          <div className="mt-3 overflow-x-auto rounded-md border border-line">
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
        <form className="mt-5 grid grid-cols-1 gap-3 md:grid-cols-[minmax(0,1fr)_minmax(0,1fr)_auto]" onSubmit={changePassword}>
          <input className="focus-ring min-w-0 rounded-md border border-line px-3 py-2 text-sm" type="password" placeholder="Current password" value={passwords.current} onChange={(event) => setPasswords({ ...passwords, current: event.target.value })} required />
          <input className="focus-ring min-w-0 rounded-md border border-line px-3 py-2 text-sm" type="password" placeholder="New password (12+ characters)" minLength={12} value={passwords.next} onChange={(event) => setPasswords({ ...passwords, next: event.target.value })} required />
          <button className="ButtonSecondary" disabled={busy} type="submit"><KeyRound size={16} aria-hidden="true" />Change my password</button>
        </form>
      ) : null}
      {message ? <p className="mt-3 rounded-md bg-paper px-3 py-2 text-sm text-ink">{message}</p> : null}
    </section>
  );
}

function UserRow({ user, busy, actorRole, onChange }: { user: User; busy: boolean; actorRole: string | null; onChange: (user: User, payload: Partial<{ role: string; active: boolean; password: string }>) => Promise<void> }) {
  const [resetPassword, setResetPassword] = useState("");
  return (
    <tr>
      <td className="px-3 py-3 font-medium text-ink">{user.email}</td>
      <td className="px-3 py-3"><select className="focus-ring rounded border border-line px-2 py-1" value={user.role} disabled={busy || (user.role === "owner" && actorRole !== "owner")} onChange={(event) => void onChange(user, { role: event.target.value })}><option value="viewer">Viewer</option><option value="admin">Admin</option>{actorRole === "owner" ? <option value="owner">Owner</option> : null}</select></td>
      <td className="px-3 py-3">{user.active ? "Active" : "Disabled"}</td>
      <td className="px-3 py-3 text-zinc-600">{user.last_login_at ? new Date(user.last_login_at).toLocaleString() : "Never"}</td>
      <td className="px-3 py-3"><div className="flex items-center gap-2"><input className="focus-ring w-40 rounded border border-line px-2 py-1" type="password" minLength={12} placeholder="Reset password" value={resetPassword} onChange={(event) => setResetPassword(event.target.value)} /><button className="ButtonSecondary" type="button" disabled={busy || resetPassword.length < 12} onClick={() => { void onChange(user, { password: resetPassword }); setResetPassword(""); }}>Reset</button><button className="ButtonSecondary" type="button" disabled={busy} onClick={() => void onChange(user, { active: !user.active })}>{user.active ? "Disable" : "Enable"}</button></div></td>
    </tr>
  );
}
