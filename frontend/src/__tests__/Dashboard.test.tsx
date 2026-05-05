import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import React from "react";

const mocks = vi.hoisted(() => ({
  getImmichSettings: vi.fn(),
  getAssetCount: vi.fn(),
  getJobs: vi.fn(),
  getAlbums: vi.fn(),
  startSyncJob: vi.fn(),
  startRoutingClassify: vi.fn(),
  clearTerminalJobs: vi.fn(),
  listRoutingPlans: vi.fn(),
  listRoutingNodes: vi.fn(),
}));

vi.mock("../services/api", () => ({
  getImmichSettings: mocks.getImmichSettings,
  getAssetCount: mocks.getAssetCount,
  getJobs: mocks.getJobs,
  getAlbums: mocks.getAlbums,
  startSyncJob: mocks.startSyncJob,
  startRoutingClassify: mocks.startRoutingClassify,
  clearTerminalJobs: mocks.clearTerminalJobs,
  listRoutingPlans: mocks.listRoutingPlans,
  listRoutingNodes: mocks.listRoutingNodes,
}));

import Dashboard from "../pages/Dashboard";

function makeClient() {
  return new QueryClient({
    defaultOptions: { queries: { retry: false, gcTime: 0, staleTime: 0 } },
  });
}

function renderDashboard() {
  return render(
    <QueryClientProvider client={makeClient()}>
      <MemoryRouter>
        <Dashboard />
      </MemoryRouter>
    </QueryClientProvider>
  );
}

beforeEach(() => {
  vi.clearAllMocks();
  mocks.getImmichSettings.mockResolvedValue({ immich_url: "", connected: false });
  mocks.getAssetCount.mockResolvedValue({ count: 0 });
  mocks.getJobs.mockResolvedValue([]);
  mocks.getAlbums.mockResolvedValue([]);
  mocks.listRoutingPlans.mockResolvedValue([]);
  mocks.listRoutingNodes.mockResolvedValue([]);
  mocks.startSyncJob.mockResolvedValue({ job_id: "sync-job", status: "queued" });
  mocks.startRoutingClassify.mockResolvedValue({ job_id: "route-job", plan_id: "plan", status: "queued" });
});

describe("Dashboard workflow", () => {
  it("sends sync+route to backend without starting routing immediately", async () => {
    renderDashboard();

    await screen.findByText("Run Workflow");
    const runButton = screen.getAllByRole("button", { name: /sync \+ route/i }).at(-1);
    expect(runButton).toBeTruthy();
    fireEvent.click(runButton!);

    await waitFor(() => {
      expect(mocks.startSyncJob).toHaveBeenCalledWith({
        scope: "all",
        album_ids: undefined,
        run_routing_after: true,
      });
    });
    expect(mocks.startRoutingClassify).not.toHaveBeenCalled();
  });
});
