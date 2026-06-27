import React from "react";
import { render, screen } from "@testing-library/react";
import { ScanActions } from "./ScanActions";
import type { ScanJob, Sensor } from "@/lib/types";

const onlineSensor: Sensor = {
  id: "sensor-1",
  site_id: "site-1",
  site_name: "Main Office",
  name: "MacBook Sensor",
  hostname: "macbook",
  status: "online",
  connection_state: "online",
  created_at: "2026-06-27T12:00:00Z",
  last_seen_at: "2026-06-27T12:00:00Z",
  current_job: null
};

const failedJob: ScanJob = {
  id: "job-1",
  site_id: "site-1",
  sensor_id: "sensor-1",
  target_cidr: "192.168.1.0/24",
  include_wifi: true,
  status: "failed",
  created_at: "2026-06-27T12:00:00Z",
  updated_at: "2026-06-27T12:01:00Z",
  claimed_at: "2026-06-27T12:00:10Z",
  started_at: "2026-06-27T12:00:20Z",
  completed_at: "2026-06-27T12:01:00Z",
  preview: {},
  result_summary: { assets_seen: 3, findings_created: 1 },
  error_message: "worker died"
};

test("renders scan action controls with sensor status", () => {
  render(React.createElement(ScanActions, { scanJobs: [], sensors: [onlineSensor], onChanged: () => undefined }));

  expect(screen.getByText("Scan Actions")).toBeInTheDocument();
  expect(screen.getByText("MacBook Sensor")).toBeInTheDocument();
  expect(screen.getByText("Sensor online")).toBeInTheDocument();
  expect(screen.getByLabelText("Target CIDR")).toHaveValue("192.168.1.0/24");
  expect(screen.getByRole("button", { name: "Copy Preview" })).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "Copy Cloud Scan" })).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "Queue Remote Scan" })).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "Generate Report" })).toBeInTheDocument();
  expect(screen.getByText("No remote jobs queued.")).toBeInTheDocument();
});

test("renders failed job details and retry control", () => {
  render(React.createElement(ScanActions, { scanJobs: [failedJob], sensors: [onlineSensor], onChanged: () => undefined }));

  expect(screen.getByText("Assets: 3")).toBeInTheDocument();
  expect(screen.getByText("Findings: 1")).toBeInTheDocument();
  expect(screen.getByText("worker died")).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "Retry" })).toBeInTheDocument();
});
