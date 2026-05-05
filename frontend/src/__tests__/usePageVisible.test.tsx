import { describe, it, expect, vi, afterEach } from "vitest";
import { render, screen } from "@testing-library/react";
import React from "react";
import { usePageVisible } from "../hooks/usePageVisible";

function Probe() {
  const visible = usePageVisible();
  return <div>{visible ? "visible" : "hidden"}</div>;
}

describe("usePageVisible", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("tracks document visibility changes", () => {
    render(<Probe />);
    expect(screen.getByText("visible")).toBeInTheDocument();

    vi.spyOn(document, "visibilityState", "get").mockReturnValue("hidden");
    document.dispatchEvent(new Event("visibilitychange"));
    expect(screen.getByText("hidden")).toBeInTheDocument();
  });
});
