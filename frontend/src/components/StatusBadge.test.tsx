import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { StatusBadge } from "./StatusBadge";

describe("StatusBadge", () => {
  it.each([
    ["online", "Online"],
    ["degraded", "Degradado"],
    ["offline", "Offline"]
  ] as const)("renders the %s operational state", (status, label) => {
    render(<StatusBadge status={status} />);

    expect(screen.getByText(label)).toBeTruthy();
  });
});
