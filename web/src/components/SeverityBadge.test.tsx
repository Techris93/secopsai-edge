import React from "react";
import { render, screen } from "@testing-library/react";
import { SeverityBadge } from "./SeverityBadge";

test("renders the severity label", () => {
  render(React.createElement(SeverityBadge, { severity: "high" }));
  expect(screen.getByText("high")).toBeInTheDocument();
});
