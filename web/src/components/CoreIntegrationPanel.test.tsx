import React from "react";
import { fireEvent, render, screen } from "@testing-library/react";
import { vi } from "vitest";
import { CoreIntegrationPanel } from "./CoreIntegrationPanel";

test("renders Core integration action buttons", () => {
  render(React.createElement(CoreIntegrationPanel));

  expect(screen.getByText("SecOpsAI Core Integration")).toBeInTheDocument();
  expect(screen.getByRole("button", { name: /Download Bundle/ })).toBeInTheDocument();
  expect(screen.getByRole("button", { name: /Copy Export/ })).toBeInTheDocument();
  expect(screen.getByRole("button", { name: /Copy Import/ })).toBeInTheDocument();
  expect(screen.getByRole("button", { name: /Copy Assets/ })).toBeInTheDocument();
  expect(screen.getByRole("button", { name: /Copy Triage/ })).toBeInTheDocument();
  expect(screen.getByRole("button", { name: /Copy API Sync/ })).toBeInTheDocument();
  expect(screen.getByRole("button", { name: /Copy One-Step Sync/ })).toBeInTheDocument();
  expect(screen.getByRole("button", { name: /Copy Support Bundle/ })).toBeInTheDocument();
});

test("copies Core import command", async () => {
  const writeText = vi.fn().mockResolvedValue(undefined);
  Object.defineProperty(navigator, "clipboard", {
    configurable: true,
    value: { writeText }
  });

  render(React.createElement(CoreIntegrationPanel));
  fireEvent.click(screen.getByRole("button", { name: /Copy Import/ }));

  expect(writeText).toHaveBeenCalledWith(expect.stringContaining("secopsai.cli edge import"));
  expect(await screen.findByText("Copy Import copied")).toBeInTheDocument();
});
