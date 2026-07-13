"use client";

import { KeyRound, MapPinned, Pencil, Plus, PowerOff, RotateCw, Save } from "lucide-react";
import { FormEvent, useEffect, useMemo, useState } from "react";
import { DataStatePanel } from "@/components/DataStatePanel";
import { LiveState } from "@/components/LiveState";
import { PageHeader } from "@/components/PageHeader";
import {
  createSite,
  disableSensor,
  enableSensor,
  fetchDashboardData,
  rotateSensorToken,
  updateSensor,
  updateSite
} from "@/lib/api";
import { timeAgo } from "@/lib/format";
import type { DashboardDataMode } from "@/lib/api";
import type { DashboardData, Sensor, Site } from "@/lib/types";

export default function SitesPage() {
  const [data, setData] = useState<DashboardData | null>(null);
  const [live, setLive] = useState(false);
  const [mode, setMode] = useState<DashboardDataMode>("blocked");
  const [error, setError] = useState<string | undefined>();
  const [siteName, setSiteName] = useState("");
  const [message, setMessage] = useState<string | null>(null);
  const [rotatedToken, setRotatedToken] = useState<{ sensorId: string; token: string } | null>(null);

  async function load() {
    const result = await fetchDashboardData();
    setData(result.data);
    setLive(result.live);
    setMode(result.mode);
    setError(result.error);
  }

  useEffect(() => {
    load();
  }, []);

  async function onCreateSite(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!siteName.trim()) return;
    try {
      await createSite(siteName.trim());
      setSiteName("");
      setMessage("Site created");
      await load();
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "Unable to create site");
    }
  }

  const sites = data?.sites ?? [];
  const sensorsBySite = useMemo(() => {
    const grouped = new Map<string, Sensor[]>();
    for (const sensor of data?.sensors ?? []) {
      grouped.set(sensor.site_id, [...(grouped.get(sensor.site_id) ?? []), sensor]);
    }
    return grouped;
  }, [data]);

  return (
    <>
      <PageHeader
        eyebrow="Customers"
        title="Sites"
        description="Manage customer locations, sensors, and recovery actions from one operator view."
        action={<LiveState live={live} mode={mode} error={error} />}
      />
      <DataStatePanel mode={mode} error={error} />

      <div className="grid gap-6 xl:grid-cols-[0.8fr_1.2fr]">
        <section className="rounded-lg border border-line bg-white p-4 shadow-panel">
          <div className="flex items-center gap-2">
            <Plus size={20} className="text-sea" aria-hidden="true" />
            <h2 className="text-lg font-semibold text-ink">Create Site</h2>
          </div>
          <form className="mt-4 grid gap-3 sm:grid-cols-[1fr_auto]" onSubmit={onCreateSite}>
            <input
              className="focus-ring rounded-md border border-line bg-white px-3 py-2 text-sm"
              value={siteName}
              onChange={(event) => setSiteName(event.target.value)}
              placeholder="Customer or office name"
            />
            <button
              className="focus-ring inline-flex items-center justify-center gap-2 rounded-md bg-sea px-3 py-2 text-sm font-semibold text-white disabled:cursor-not-allowed disabled:bg-zinc-300"
              disabled={!live || !siteName.trim()}
              type="submit"
            >
              <Save size={16} aria-hidden="true" />
              Save
            </button>
          </form>
          {message ? <p className="mt-3 rounded-md bg-paper px-3 py-2 text-sm text-ink">{message}</p> : null}

          {rotatedToken ? (
            <div className="mt-4 rounded-md border border-amber-200 bg-amber-50 p-3">
              <p className="text-sm font-semibold text-ink">New sensor token</p>
              <code className="mt-2 block break-all rounded bg-white p-2 font-mono text-xs text-ink">{rotatedToken.token}</code>
              <p className="mt-2 text-xs text-amber-800">Update the local sensor credentials before restarting the worker.</p>
            </div>
          ) : null}
        </section>

        <section className="rounded-lg border border-line bg-white shadow-panel">
          <div className="border-b border-line px-4 py-3">
            <h2 className="text-lg font-semibold text-ink">Site Inventory</h2>
          </div>
          <div className="divide-y divide-line">
            {sites.map((site) => (
              <SiteRow
                key={site.id}
                live={live}
                site={site}
                sensors={sensorsBySite.get(site.id) ?? []}
                onChanged={load}
                onMessage={setMessage}
                onToken={setRotatedToken}
              />
            ))}
          </div>
        </section>
      </div>
    </>
  );
}

function SiteRow({
  site,
  sensors,
  live,
  onChanged,
  onMessage,
  onToken
}: {
  site: Site;
  sensors: Sensor[];
  live: boolean;
  onChanged: () => Promise<void>;
  onMessage: (value: string) => void;
  onToken: (value: { sensorId: string; token: string } | null) => void;
}) {
  const [editing, setEditing] = useState(false);
  const [name, setName] = useState(site.name);

  async function saveSite() {
    try {
      await updateSite(site.id, name);
      setEditing(false);
      onMessage("Site updated");
      await onChanged();
    } catch (error) {
      onMessage(error instanceof Error ? error.message : "Unable to update site");
    }
  }

  return (
    <article className="p-4">
      <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
        <div className="min-w-0">
          <div className="flex items-center gap-2">
            <MapPinned size={18} className="text-sea" aria-hidden="true" />
            {editing ? (
              <input
                className="focus-ring rounded-md border border-line bg-white px-2 py-1 text-sm font-semibold"
                value={name}
                onChange={(event) => setName(event.target.value)}
              />
            ) : (
              <h3 className="text-lg font-semibold text-ink">{site.name}</h3>
            )}
          </div>
          <p className="mt-1 text-sm text-zinc-500">Created {timeAgo(site.created_at)}</p>
        </div>
        <div className="flex flex-wrap gap-2">
          {editing ? (
            <button className="ButtonSecondary" disabled={!live} onClick={saveSite} type="button">
              <Save size={16} aria-hidden="true" />
              Save
            </button>
          ) : (
            <button className="ButtonSecondary" disabled={!live} onClick={() => setEditing(true)} type="button">
              <Pencil size={16} aria-hidden="true" />
              Edit
            </button>
          )}
        </div>
      </div>
      <div className="mt-4 grid gap-3">
        {sensors.map((sensor) => (
          <SensorRow
            key={sensor.id}
            live={live}
            sensor={sensor}
            onChanged={onChanged}
            onMessage={onMessage}
            onToken={onToken}
          />
        ))}
        {!sensors.length ? <p className="rounded-md bg-paper p-3 text-sm text-zinc-600">No sensors registered for this site.</p> : null}
      </div>
    </article>
  );
}

function SensorRow({
  sensor,
  live,
  onChanged,
  onMessage,
  onToken
}: {
  sensor: Sensor;
  live: boolean;
  onChanged: () => Promise<void>;
  onMessage: (value: string) => void;
  onToken: (value: { sensorId: string; token: string } | null) => void;
}) {
  const [name, setName] = useState(sensor.name);

  async function rename() {
    try {
      await updateSensor(sensor.id, { name });
      onMessage("Sensor renamed");
      await onChanged();
    } catch (error) {
      onMessage(error instanceof Error ? error.message : "Unable to rename sensor");
    }
  }

  async function rotate() {
    try {
      const response = await rotateSensorToken(sensor.id);
      onToken({ sensorId: response.sensor_id, token: response.sensor_token });
      onMessage("Sensor token rotated");
      await onChanged();
    } catch (error) {
      onMessage(error instanceof Error ? error.message : "Unable to rotate token");
    }
  }

  async function disable() {
    try {
      await disableSensor(sensor.id);
      onMessage("Sensor disabled");
      await onChanged();
    } catch (error) {
      onMessage(error instanceof Error ? error.message : "Unable to disable sensor");
    }
  }

  async function enable() {
    try {
      await enableSensor(sensor.id);
      onMessage("Sensor enabled. The existing sensor token remains valid.");
      await onChanged();
    } catch (error) {
      onMessage(error instanceof Error ? error.message : "Unable to enable sensor");
    }
  }

  return (
    <div className="rounded-md border border-line bg-paper p-3">
      <div className="grid gap-3 lg:grid-cols-[1fr_auto] lg:items-center">
        <div>
          <input
            className="focus-ring w-full rounded-md border border-line bg-white px-3 py-2 text-sm font-semibold text-ink"
            value={name}
            onChange={(event) => setName(event.target.value)}
          />
          <div className="mt-2 flex flex-wrap gap-2 text-xs text-zinc-600">
            <span>{sensor.hostname ?? "No hostname"}</span>
            <span>{sensor.connection_state}</span>
            <span>{sensor.worker_state ?? "state unknown"}</span>
            <span>{sensor.version ? `v${sensor.version}` : "version unknown"}</span>
            <span>{sensor.os_name ?? "OS unknown"}</span>
            {sensor.current_job_id ? <span>Job {sensor.current_job_id}</span> : null}
            <span>{sensor.last_seen_at ? `Last seen ${timeAgo(sensor.last_seen_at)}` : "Never seen"}</span>
            {sensor.last_error ? <span className="text-danger">{sensor.last_error}</span> : null}
          </div>
        </div>
        <div className="flex flex-wrap gap-2">
          <button className="ButtonSecondary" disabled={!live || name === sensor.name} onClick={rename} type="button">
            <Save size={16} aria-hidden="true" />
            Rename
          </button>
          <button className="ButtonSecondary" disabled={!live} onClick={rotate} type="button">
            <KeyRound size={16} aria-hidden="true" />
            Rotate
          </button>
          {sensor.connection_state === "disabled" ? (
            <button className="ButtonSecondary" disabled={!live} onClick={enable} type="button">Enable</button>
          ) : (
            <button className="ButtonDanger" disabled={!live} onClick={disable} type="button">
              <PowerOff size={16} aria-hidden="true" />
              Disable
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
