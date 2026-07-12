"use client";

import { Bell, RefreshCw, Send, Trash2 } from "lucide-react";
import { FormEvent, useEffect, useState } from "react";
import {
  createNotificationEndpoint,
  deleteNotificationEndpoint,
  fetchDashboardData,
  listNotificationDeliveries,
  retryNotificationDelivery,
  testNotificationEndpoint,
  updateNotificationEndpoint
} from "@/lib/api";
import type { DashboardData, NotificationDelivery, NotificationEndpoint } from "@/lib/types";

const events = [
  "scan_completed",
  "high_finding",
  "new_device",
  "risky_service",
  "scheduled_report_ready"
];

export function NotificationPanel() {
  const [data, setData] = useState<DashboardData | null>(null);
  const [deliveries, setDeliveries] = useState<NotificationDelivery[]>([]);
  const [message, setMessage] = useState<string | null>(null);
  const [form, setForm] = useState({
    name: "Pilot webhook",
    type: "webhook",
    target: "",
    site_id: "",
    events: ["high_finding", "new_device"],
    enabled: true
  });

  async function load() {
    const result = await fetchDashboardData();
    setData(result.data);
    if (result.mode !== "live") {
      setDeliveries([]);
      return;
    }
    try {
      setDeliveries(await listNotificationDeliveries());
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Unable to load delivery history");
    }
  }

  useEffect(() => {
    load();
  }, []);

  async function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    try {
      await createNotificationEndpoint({
        ...form,
        site_id: form.site_id || undefined
      });
      setForm({ ...form, target: "" });
      setMessage("Notification endpoint created");
      await load();
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Unable to create endpoint");
    }
  }

  function toggleEvent(eventName: string, checked: boolean) {
    const next = checked
      ? [...new Set([...form.events, eventName])]
      : form.events.filter((item) => item !== eventName);
    setForm({ ...form, events: next });
  }

  return (
    <section className="min-w-0 rounded-lg border border-line bg-white p-4 shadow-panel xl:col-span-2">
      <div className="flex items-center gap-2">
        <Bell size={20} className="text-sea" aria-hidden="true" />
        <h2 className="text-lg font-semibold text-ink">Notifications</h2>
      </div>

      <form className="mt-4 grid grid-cols-1 gap-3 lg:grid-cols-[minmax(0,1fr)_9rem_minmax(0,1fr)_12rem_auto]" onSubmit={onSubmit}>
        <input
          className="focus-ring rounded-md border border-line bg-white px-3 py-2 text-sm"
          value={form.name}
          onChange={(event) => setForm({ ...form, name: event.target.value })}
          placeholder="Endpoint name"
        />
        <select
          className="focus-ring rounded-md border border-line bg-white px-3 py-2 text-sm"
          value={form.type}
          onChange={(event) => setForm({ ...form, type: event.target.value })}
        >
          <option value="webhook">Webhook</option>
          <option value="email">Email</option>
          <option value="telegram">Telegram</option>
        </select>
        <input
          className="focus-ring rounded-md border border-line bg-white px-3 py-2 text-sm"
          value={form.target}
          onChange={(event) => setForm({ ...form, target: event.target.value })}
          placeholder="URL, email, or chat ID"
        />
        <select
          className="focus-ring rounded-md border border-line bg-white px-3 py-2 text-sm"
          value={form.site_id}
          onChange={(event) => setForm({ ...form, site_id: event.target.value })}
        >
          <option value="">All sites</option>
          {(data?.sites ?? []).map((site) => (
            <option key={site.id} value={site.id}>{site.name}</option>
          ))}
        </select>
        <button className="focus-ring inline-flex h-10 items-center justify-center gap-2 rounded-md bg-sea px-3 text-sm font-semibold text-white disabled:bg-zinc-300" disabled={!form.target.trim()} type="submit">
          <Send size={16} aria-hidden="true" />
          Add
        </button>
      </form>

      <div className="mt-3 flex flex-wrap gap-2">
        {events.map((eventName) => (
          <label key={eventName} className="flex items-center gap-2 rounded-md bg-paper px-3 py-2 text-xs font-medium text-ink">
            <input
              checked={form.events.includes(eventName)}
              className="h-4 w-4 rounded border-line text-sea"
              onChange={(event) => toggleEvent(eventName, event.target.checked)}
              type="checkbox"
            />
            {eventName}
          </label>
        ))}
      </div>

      <div className="mt-4 divide-y divide-line rounded-md border border-line">
        {(data?.notifications ?? []).map((endpoint) => (
          <NotificationRow key={endpoint.id} endpoint={endpoint} onChanged={load} onMessage={setMessage} />
        ))}
        {!(data?.notifications ?? []).length ? <p className="p-3 text-sm text-zinc-600">No notification endpoints configured.</p> : null}
      </div>
      <div className="mt-5 flex items-center justify-between gap-3">
        <div>
          <h3 className="text-sm font-semibold text-ink">Delivery history</h3>
          <p className="text-xs text-zinc-600">Signed webhook, email, and Telegram attempts are retained with bounded retry state.</p>
        </div>
        <button className="ButtonSecondary" onClick={load} type="button">
          <RefreshCw size={16} aria-hidden="true" />
          Refresh
        </button>
      </div>
      <div className="mt-3 overflow-x-auto rounded-md border border-line">
        <table className="min-w-full text-left text-sm">
          <thead className="bg-paper text-xs uppercase text-zinc-600">
            <tr>
              <th className="px-3 py-2">Event</th>
              <th className="px-3 py-2">Status</th>
              <th className="px-3 py-2">Attempts</th>
              <th className="px-3 py-2">Result</th>
              <th className="px-3 py-2"><span className="sr-only">Actions</span></th>
            </tr>
          </thead>
          <tbody className="divide-y divide-line">
            {deliveries.map((delivery) => (
              <DeliveryRow key={delivery.id} delivery={delivery} onChanged={load} onMessage={setMessage} />
            ))}
            {!deliveries.length ? (
              <tr><td className="px-3 py-4 text-zinc-600" colSpan={5}>No delivery attempts recorded yet.</td></tr>
            ) : null}
          </tbody>
        </table>
      </div>
      {message ? <p className="mt-3 rounded-md bg-paper px-3 py-2 text-sm text-ink">{message}</p> : null}
    </section>
  );
}

function DeliveryRow({
  delivery,
  onChanged,
  onMessage
}: {
  delivery: NotificationDelivery;
  onChanged: () => Promise<void>;
  onMessage: (value: string) => void;
}) {
  async function retry() {
    try {
      const updated = await retryNotificationDelivery(delivery.id);
      onMessage(`Delivery ${updated.status}`);
      await onChanged();
    } catch (error) {
      onMessage(error instanceof Error ? error.message : "Unable to retry delivery");
    }
  }

  return (
    <tr>
      <td className="whitespace-nowrap px-3 py-3 font-medium text-ink">{delivery.event_type}</td>
      <td className="px-3 py-3"><span className="rounded border border-line bg-paper px-2 py-1 text-xs font-semibold uppercase">{delivery.status}</span></td>
      <td className="whitespace-nowrap px-3 py-3 text-zinc-700">{delivery.attempts}/{delivery.max_attempts}</td>
      <td className="max-w-md px-3 py-3 text-xs text-zinc-600">{delivery.response_detail ?? "Waiting for delivery"}</td>
      <td className="px-3 py-3 text-right">
        {delivery.status === "failed" ? (
          <button className="ButtonSecondary" onClick={retry} type="button">
            <RefreshCw size={16} aria-hidden="true" />
            Retry
          </button>
        ) : null}
      </td>
    </tr>
  );
}

function NotificationRow({
  endpoint,
  onChanged,
  onMessage
}: {
  endpoint: NotificationEndpoint;
  onChanged: () => Promise<void>;
  onMessage: (value: string) => void;
}) {
  async function toggle() {
    try {
      await updateNotificationEndpoint(endpoint.id, { enabled: !endpoint.enabled });
      onMessage(endpoint.enabled ? "Endpoint disabled" : "Endpoint enabled");
      await onChanged();
    } catch (error) {
      onMessage(error instanceof Error ? error.message : "Unable to update endpoint");
    }
  }

  async function test() {
    try {
      const response = await testNotificationEndpoint(endpoint.id);
      onMessage(response.detail);
      await onChanged();
    } catch (error) {
      onMessage(error instanceof Error ? error.message : "Unable to test endpoint");
    }
  }

  async function remove() {
    try {
      await deleteNotificationEndpoint(endpoint.id);
      onMessage("Endpoint deleted");
      await onChanged();
    } catch (error) {
      onMessage(error instanceof Error ? error.message : "Unable to delete endpoint");
    }
  }

  return (
    <div className="grid gap-3 p-3 lg:grid-cols-[1fr_auto] lg:items-center">
      <div>
        <div className="flex flex-wrap items-center gap-2">
          <p className="font-semibold text-ink">{endpoint.name}</p>
          <span className="rounded border border-line bg-paper px-2 py-1 text-xs font-semibold uppercase">
            {endpoint.type}
          </span>
          <span className="rounded border border-line bg-paper px-2 py-1 text-xs font-semibold uppercase">
            {endpoint.enabled ? "enabled" : "disabled"}
          </span>
        </div>
        <p className="mt-1 break-all font-mono text-xs text-zinc-600">{endpoint.target}</p>
        {endpoint.last_error ? <p className="mt-1 text-xs text-danger">{endpoint.last_error}</p> : null}
      </div>
      <div className="flex flex-wrap gap-2">
        <button className="ButtonSecondary" onClick={toggle} type="button">
          {endpoint.enabled ? "Disable" : "Enable"}
        </button>
        <button className="ButtonSecondary" onClick={test} type="button">
          <Send size={16} aria-hidden="true" />
          Test
        </button>
        <button className="ButtonDanger" onClick={remove} type="button">
          <Trash2 size={16} aria-hidden="true" />
          Delete
        </button>
      </div>
    </div>
  );
}
