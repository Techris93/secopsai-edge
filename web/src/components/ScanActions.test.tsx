import React from "react";
import { render, screen } from "@testing-library/react";
import { ScanActions } from "./ScanActions";

test("renders scan action controls", () => {
  render(React.createElement(ScanActions, { scanJobs: [], onChanged: () => undefined }));

  expect(screen.getByText("Scan Actions")).toBeInTheDocument();
  expect(screen.getByLabelText("Target CIDR")).toHaveValue("192.168.1.0/24");
  expect(screen.getByRole("button", { name: "Copy Preview" })).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "Copy Cloud Scan" })).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "Queue Remote Scan" })).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "Generate Report" })).toBeInTheDocument();
  expect(screen.getByText("No remote jobs queued.")).toBeInTheDocument();
});
