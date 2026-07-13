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
