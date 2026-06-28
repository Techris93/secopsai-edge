"use client";

import { CalendarClock, Play, Plus, Trash2 } from "lucide-react";
import { FormEvent, useEffect, useMemo, useState } from "react";
import { LiveState } from "@/components/LiveState";
import { PageHeader } from "@/components/PageHeader";
import {
  createScanSchedule,
  deleteScanSchedule,
  fetchDashboardData,
  runDueSchedules,
  updateScanSchedule
} from "@/lib/api";
import { timeAgo } from "@/lib/format";
import type { DashboardData, ScanSchedule } from "@/lib/types";

export default function SchedulesPage() {
  const [data, setData] = useState<DashboardData | null>(null);
  const [live, setLive] = useState(false);
  const [error, setError] = useState<string | undefined>();
  const [message, setMessage] = useState<string | null>(null);
  const [listSite, setListSite] = useState("all");
  const [form, setForm] = useState({
    name: "Daily network scan",
    target_cidr: "192.168.1.0/24",
    frequency: "daily",
    time_of_day: "09:00",
    timezone: Intl.DateTimeFormat().resolvedOptions().timeZone || "UTC",
    include_wifi: false,
    site_id: "",
    sensor_id: ""
  });

  async function load() {
    const result = await fetchDashboardData();
    setData(result.data);
    setLive(result.live);
    setError(result.error);
  }

  useEffect(() => {
    load();
  }, []);

  const sensorsForSite = useMemo(() => {
    if (!form.site_id) return data?.sensors ?? [];
    return (data?.sensors ?? []).filter((sensor) => sensor.site_id === form.site_id);
  }, [data, form.site_id]);
  const filteredSchedules = (data?.schedules ?? []).filter(
    (schedule) => listSite === "all" || schedule.site_id === listSite
  );

  async function onCreate(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    try {
      await createScanSchedule({
        ...form,
        site_id: form.site_id || undefined,
        sensor_id: form.sensor_id || undefined,
        enabled: true
      });
      setMessage("Schedule created");
      await load();
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "Unable to create schedule");
    }
  }

  async function onRunDue() {
    try {
      const response = await runDueSchedules();
      setMessage(`Queued ${response.queued} due scan job${response.queued === 1 ? "" : "s"}`);
      await load();
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "Unable to run scheduler");
    }
  }

  return (
    <>
      <PageHeader
        eyebrow="Automation"
        title="Scheduled Scans"
        description="Queue recurring LAN discovery jobs for registered sensors and sites."
        action={<LiveState live={live} error={error} />}
      />

      <div className="grid gap-6 xl:grid-cols-[0.9fr_1.1fr]">
        <section className="rounded-lg border border-line bg-white p-4 shadow-panel">
          <div className="flex items-center gap-2">
            <Plus size={20} className="text-sea" aria-hidden="true" />
            <h2 className="text-lg font-semibold text-ink">New Schedule</h2>
          </div>
          <form className="mt-4 grid gap-3" onSubmit={onCreate}>
            <TextInput label="Name" value={form.name} onChange={(value) => setForm({ ...form, name: value })} />
            <TextInput label="Target CIDR" value={form.target_cidr} onChange={(value) => setForm({ ...form, target_cidr: value })} />
            <div className="grid gap-3 sm:grid-cols-2">
              <label className="grid gap-1 text-sm font-medium text-ink">
                Site
                <select
                  className="focus-ring rounded-md border border-line bg-white px-3 py-2 text-sm"
                  value={form.site_id}
                  onChange={(event) => setForm({ ...form, site_id: event.target.value, sensor_id: "" })}
                >
                  <option value="">First available</option>
                  {(data?.sites ?? []).map((site) => (
                    <option key={site.id} value={site.id}>{site.name}</option>
                  ))}
                </select>
              </label>
              <label className="grid gap-1 text-sm font-medium text-ink">
                Sensor
                <select
                  className="focus-ring rounded-md border border-line bg-white px-3 py-2 text-sm"
                  value={form.sensor_id}
                  onChange={(event) => setForm({ ...form, sensor_id: event.target.value })}
                >
                  <option value="">First available</option>
                  {sensorsForSite.map((sensor) => (
                    <option key={sensor.id} value={sensor.id}>{sensor.name}</option>
                  ))}
                </select>
              </label>
            </div>
            <div className="grid gap-3 sm:grid-cols-3">
              <label className="grid gap-1 text-sm font-medium text-ink">
                Frequency
                <select
                  className="focus-ring rounded-md border border-line bg-white px-3 py-2 text-sm"
                  value={form.frequency}
                  onChange={(event) => setForm({ ...form, frequency: event.target.value })}
                >
                  <option value="daily">Daily</option>
                  <option value="weekly">Weekly</option>
                </select>
              </label>
              <TextInput label="Time" value={form.time_of_day} onChange={(value) => setForm({ ...form, time_of_day: value })} />
              <TextInput label="Timezone" value={form.timezone} onChange={(value) => setForm({ ...form, timezone: value })} />
            </div>
            <label className="flex items-center gap-2 text-sm font-medium text-ink">
              <input
                checked={form.include_wifi}
                className="h-4 w-4 rounded border-line text-sea"
                onChange={(event) => setForm({ ...form, include_wifi: event.target.checked })}
                type="checkbox"
              />
              Include Wi-Fi inventory
            </label>
            <button
              className="focus-ring inline-flex h-10 items-center justify-center gap-2 rounded-md bg-sea px-3 text-sm font-semibold text-white disabled:cursor-not-allowed disabled:bg-zinc-300"
              disabled={!live}
              type="submit"
            >
              <CalendarClock size={16} aria-hidden="true" />
              Create Schedule
            </button>
          </form>
          {message ? <p className="mt-3 rounded-md bg-paper px-3 py-2 text-sm text-ink">{message}</p> : null}
        </section>

        <section className="rounded-lg border border-line bg-white shadow-panel">
          <div className="flex items-center justify-between gap-3 border-b border-line px-4 py-3">
            <h2 className="text-lg font-semibold text-ink">Schedules</h2>
            <div className="flex flex-wrap gap-2">
              <select
                className="focus-ring h-10 rounded-md border border-line bg-white px-3 text-sm"
                value={listSite}
                onChange={(event) => setListSite(event.target.value)}
              >
                <option value="all">All sites</option>
                {(data?.sites ?? []).map((site) => (
                  <option key={site.id} value={site.id}>{site.name}</option>
                ))}
              </select>
              <button className="ButtonSecondary" disabled={!live} onClick={onRunDue} type="button">
                <Play size={16} aria-hidden="true" />
                Run Due
              </button>
            </div>
          </div>
          <div className="divide-y divide-line">
            {filteredSchedules.map((schedule) => (
              <ScheduleRow
                key={schedule.id}
                live={live}
                schedule={schedule}
                onChanged={load}
                onMessage={setMessage}
              />
            ))}
            {!filteredSchedules.length ? (
              <p className="p-4 text-sm text-zinc-600">No schedules configured.</p>
            ) : null}
          </div>
        </section>
      </div>
    </>
  );
}

function ScheduleRow({
  schedule,
  live,
  onChanged,
  onMessage
}: {
  schedule: ScanSchedule;
  live: boolean;
  onChanged: () => Promise<void>;
  onMessage: (value: string) => void;
}) {
  async function toggle() {
    try {
      await updateScanSchedule(schedule.id, { enabled: !schedule.enabled });
      onMessage(schedule.enabled ? "Schedule disabled" : "Schedule enabled");
      await onChanged();
    } catch (error) {
      onMessage(error instanceof Error ? error.message : "Unable to update schedule");
    }
  }

  async function remove() {
    try {
      await deleteScanSchedule(schedule.id);
      onMessage("Schedule deleted");
      await onChanged();
    } catch (error) {
      onMessage(error instanceof Error ? error.message : "Unable to delete schedule");
    }
  }

  return (
    <article className="p-4">
      <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
        <div>
          <div className="flex flex-wrap items-center gap-2">
            <h3 className="text-lg font-semibold text-ink">{schedule.name}</h3>
            <span className="rounded border border-line bg-paper px-2 py-1 text-xs font-semibold uppercase text-ink">
              {schedule.enabled ? "enabled" : "disabled"}
            </span>
          </div>
          <p className="mt-2 font-mono text-sm text-ink">{schedule.target_cidr}</p>
          <p className="mt-1 text-sm text-zinc-600">
            {schedule.frequency} at {schedule.time_of_day} {schedule.timezone}
          </p>
          <p className="mt-1 text-xs text-zinc-500">
            Next run {schedule.next_run_at ? timeAgo(schedule.next_run_at) : "not scheduled"}
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <button className="ButtonSecondary" disabled={!live} onClick={toggle} type="button">
            {schedule.enabled ? "Disable" : "Enable"}
          </button>
          <button className="ButtonDanger" disabled={!live} onClick={remove} type="button">
            <Trash2 size={16} aria-hidden="true" />
            Delete
          </button>
        </div>
      </div>
    </article>
  );
}

function TextInput({ label, value, onChange }: { label: string; value: string; onChange: (value: string) => void }) {
  return (
    <label className="grid gap-1 text-sm font-medium text-ink">
      {label}
      <input
        className="focus-ring rounded-md border border-line bg-white px-3 py-2 text-sm"
        value={value}
        onChange={(event) => onChange(event.target.value)}
      />
    </label>
  );
}
