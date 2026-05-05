import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import React from "react";
import Settings from "../pages/Settings";

vi.mock("../services/api", () => ({
  getImmichSettings: vi.fn(),
  saveImmichSettings: vi.fn(),
  testImmichConnection: vi.fn(),
  getProviders: vi.fn().mockResolvedValue([]),
  upsertProvider: vi.fn(),
  deleteProvider: vi.fn(),
  testProvider: vi.fn(),
  getProviderModels: vi.fn().mockResolvedValue([]),
  getRoutingPreferences: vi.fn().mockResolvedValue({ learn_from_corrections: false }),
  saveRoutingPreferences: vi.fn(),
  getHealth: vi.fn().mockResolvedValue({ status: "ok" }),
}));

import { getImmichSettings } from "../services/api";

function renderPage() {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });

  return render(
    <QueryClientProvider client={client}>
      <Settings />
    </QueryClientProvider>
  );
}

describe("Settings page", () => {
  beforeEach(() => {
    vi.mocked(getImmichSettings).mockResolvedValue({
      immich_url: "http://immich.example",
      connected: true,
      asset_count: 42,
    });
  });

  it("fills the Immich URL input after settings load", async () => {
    renderPage();

    const input = await screen.findByDisplayValue("http://immich.example");
    expect(input).toBeInTheDocument();
  });
});
