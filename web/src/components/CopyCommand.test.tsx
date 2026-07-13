import React from "react";
import { fireEvent, render, screen } from "@testing-library/react";
import { Terminal } from "lucide-react";
import { vi } from "vitest";
import { CopyCommand } from "./CopyCommand";

test("copies the displayed local command", async () => {
  const writeText = vi.fn().mockResolvedValue(undefined);
  Object.defineProperty(navigator, "clipboard", {
    configurable: true,
    value: { writeText }
  });
  render(React.createElement(CopyCommand, { command: "./scripts/edge status --cloud", icon: Terminal }));

  fireEvent.click(screen.getByRole("button", { name: /Copy command/ }));

  expect(writeText).toHaveBeenCalledWith("./scripts/edge status --cloud");
  expect(await screen.findByText("Copied")).toBeInTheDocument();
});

test("falls back when the Clipboard API denies permission", async () => {
  const writeText = vi.fn().mockRejectedValue(new DOMException("Denied", "NotAllowedError"));
  const execCommand = vi.fn().mockReturnValue(true);
  Object.defineProperty(navigator, "clipboard", {
    configurable: true,
    value: { writeText }
  });
  Object.defineProperty(document, "execCommand", {
    configurable: true,
    value: execCommand
  });
  render(React.createElement(CopyCommand, { command: "./scripts/edge cloud drift-check", icon: Terminal }));

  fireEvent.click(screen.getByRole("button", { name: /Copy command/ }));

  expect(await screen.findByText("Copied")).toBeInTheDocument();
  expect(execCommand).toHaveBeenCalledWith("copy");
  expect(document.querySelector("textarea")).not.toBeInTheDocument();
});

test("shows an accessible failure state when both copy methods fail", async () => {
  const writeText = vi.fn().mockRejectedValue(new DOMException("Denied", "NotAllowedError"));
  Object.defineProperty(navigator, "clipboard", {
    configurable: true,
    value: { writeText }
  });
  Object.defineProperty(document, "execCommand", {
    configurable: true,
    value: vi.fn().mockReturnValue(false)
  });
  render(React.createElement(CopyCommand, { command: "./scripts/edge cloud backup", icon: Terminal }));

  fireEvent.click(screen.getByRole("button", { name: /Copy command/ }));

  expect(await screen.findByText("Copy failed")).toBeInTheDocument();
  expect(screen.getByRole("button", { name: /Copy failed/ })).toHaveAttribute("title", "Copy failed");
});
