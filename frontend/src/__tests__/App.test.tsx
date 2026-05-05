import { describe, it, expect, vi } from "vitest";
import { render, screen, waitFor, waitForElementToBeRemoved } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import React from "react";
import App from "../App";

// Mock every API export so pages mount without real HTTP calls.
vi.mock("../services/api", async (importOriginal) => {
  const real = await importOriginal<typeof import("../services/api")>();
  const noop = vi.fn().mockResolvedValue(undefined);
  return {
    ...real,
    getCurrentUser: vi.fn().mockResolvedValue({
      id: "test-user",
      email: "test@example.com",
      username: "testuser",
      role: "user",
      force_password_change: false,
    }),
    login: vi.fn().mockResolvedValue({ id: "test-user", email: "test@example.com", username: "testuser", role: "user", force_password_change: false }),
    logout: vi.fn().mockResolvedValue(undefined),
    getSetupStatus: vi.fn().mockResolvedValue({ setup_required: false }),
    setupCreateAdmin: noop,
    getHealth: vi.fn().mockResolvedValue({ status: "ok" }),
    getImmichSettings: vi.fn().mockResolvedValue({ immich_url: "", connected: false }),
    testImmichConnection: noop,
    getProviders: vi.fn().mockResolvedValue([]),
    upsertProvider: noop,
    deleteProvider: noop,
    testProvider: noop,
    getRoutingPreferences: vi.fn().mockResolvedValue({ learn_from_corrections: false }),
    saveRoutingPreferences: noop,
    getAssets: vi.fn().mockResolvedValue([]),
    getAssetCount: vi.fn().mockResolvedValue({ count: 0 }),
    getAllAssetIds: vi.fn().mockResolvedValue({ ids: [] }),
    getJobs: vi.fn().mockResolvedValue([]),
    getJob: noop,
    startSyncJob: noop,
    cancelJob: noop,
    pauseJob: noop,
    resumeJob: noop,
    deleteJob: noop,
    clearTerminalJobs: noop,
    getAlbums: vi.fn().mockResolvedValue([]),
    getAuditLogs: vi.fn().mockResolvedValue([]),
    getAuditLogCount: vi.fn().mockResolvedValue({ count: 0 }),
    getProviderModels: vi.fn().mockResolvedValue([]),
    saveImmichSettings: noop,
    getThumbnailUrl: (id: string, size = "thumbnail") =>
      `/api/thumbnails/${id}?size=${size}`,
    // Routing tree
    getRoutingTree: vi.fn().mockResolvedValue({ nodes: [] }),
    listRoutingNodes: vi.fn().mockResolvedValue([]),
    createRoutingNode: noop,
    updateRoutingNode: noop,
    deleteRoutingNode: noop,
    duplicateRoutingNode: noop,
    moveRoutingNode: noop,
    listRoutingExamples: vi.fn().mockResolvedValue([]),
    addRoutingExample: noop,
    deleteRoutingExample: noop,
    getRoutingPromptPreview: vi.fn().mockResolvedValue({ bucket_id: "x", path: "X", compiled_prompt: "" }),
    startRoutingClassify: vi.fn().mockResolvedValue({ job_id: "job-1", plan_id: "plan-1", status: "queued" }),
    listRoutingPlans: vi.fn().mockResolvedValue([]),
    getRoutingPlan: noop,
    getRoutingPlanSummary: vi.fn().mockResolvedValue({
      plan_id: "x", total: 0,
      groups: { auto_applied: [], ready_to_approve: [], needs_review: [], trash_candidates: [], rejected: [], failed: [] },
    }),
    getRoutingPlanItems: vi.fn().mockResolvedValue([]),
    approveRoutingPlanItems: noop,
    rejectRoutingPlanItems: noop,
    moveRoutingPlanItems: noop,
    applyRoutingPlan: noop,
  };
});

function makeClient() {
  return new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
}

vi.mock("../components/BrandLogo", () => ({
  default: ({ subtitle = "AI photo routing for Immich" }: { subtitle?: string }) => (
    <div>
      <img src="/logo.png" alt="immich-gpt logo" />
      <div>Immich GPT</div>
      <div>{subtitle}</div>
    </div>
  ),
}));

function Wrapper({ children, path = "/" }: { children: React.ReactNode; path?: string }) {
  return (
    <QueryClientProvider client={makeClient()}>
      <MemoryRouter initialEntries={[path]}>{children}</MemoryRouter>
    </QueryClientProvider>
  );
}

describe("App routing", () => {
  it("renders the app brand name", async () => {
    render(
      <Wrapper>
        <App />
      </Wrapper>
    );
    await waitFor(() => expect(screen.getAllByText("Immich GPT").length).toBeGreaterThanOrEqual(1));
  });

  it("shows a fallback while lazy route bundles load", async () => {
    render(
      <Wrapper path="/setup">
        <App />
      </Wrapper>
    );
    expect(screen.getByText("Loading...")).toBeInTheDocument();
    await waitForElementToBeRemoved(() => screen.queryByText("Loading..."));
  });

  it("renders all nav links in the sidebar", async () => {
    render(
      <Wrapper>
        <App />
      </Wrapper>
    );
    await waitFor(() => expect(screen.getAllByText("Dashboard").length).toBeGreaterThanOrEqual(1));
    await waitFor(() => expect(screen.getAllByText("Assets").length).toBeGreaterThanOrEqual(1));
    await waitFor(() => expect(screen.getAllByText("Routing").length).toBeGreaterThanOrEqual(1));
    await waitFor(() => expect(screen.getAllByText("Routing plans").length).toBeGreaterThanOrEqual(1));
    await waitFor(() => expect(screen.getAllByText("Jobs").length).toBeGreaterThanOrEqual(1));
    await waitFor(() => expect(screen.getAllByText("Logs").length).toBeGreaterThanOrEqual(1));
    await waitFor(() => expect(screen.getAllByText("Settings").length).toBeGreaterThanOrEqual(1));
    await waitFor(() => expect(screen.getByRole("link", { name: /donate/i })).toHaveAttribute(
      "href",
      expect.stringContaining("paypal.com"),
    ));
  });

  it("renders the shared logo image", async () => {
    render(
      <Wrapper>
        <App />
      </Wrapper>
    );
    await waitFor(() => expect(screen.getByAltText("immich-gpt logo")).toBeInTheDocument());
  });

  it("renders the dashboard page by default", async () => {
    render(
      <Wrapper path="/">
        <App />
      </Wrapper>
    );
    await waitFor(() => expect(screen.getAllByText("Dashboard").length).toBeGreaterThanOrEqual(1));
  });

  it("renders the jobs page on /jobs route", async () => {
    render(
      <Wrapper path="/jobs">
        <App />
      </Wrapper>
    );
    await waitFor(() => expect(screen.getAllByText("Jobs").length).toBeGreaterThanOrEqual(1));
  });

  it("renders settings page on /settings route", async () => {
    render(
      <Wrapper path="/settings">
        <App />
      </Wrapper>
    );
    await waitFor(() => expect(screen.getAllByText("Settings").length).toBeGreaterThanOrEqual(1));
  });

  it("renders routing tree page on /routing route", async () => {
    render(
      <Wrapper path="/routing">
        <App />
      </Wrapper>
    );
    await waitFor(() => expect(screen.getAllByText(/Routing tree/i).length).toBeGreaterThanOrEqual(1));
  });

  it("renders routing plans page on /routing/plans route", async () => {
    render(
      <Wrapper path="/routing/plans">
        <App />
      </Wrapper>
    );
    await waitFor(() =>
      expect(screen.getAllByText(/Routing plans/i).length).toBeGreaterThanOrEqual(1)
    );
  });

  it("renders assets page on /assets route", async () => {
    render(
      <Wrapper path="/assets">
        <App />
      </Wrapper>
    );
    await waitFor(() => expect(screen.getAllByText("Assets").length).toBeGreaterThanOrEqual(1));
  });

  it("renders logs page on /logs route", async () => {
    render(
      <Wrapper path="/logs">
        <App />
      </Wrapper>
    );
    await waitFor(() => expect(screen.getAllByText("Logs").length).toBeGreaterThanOrEqual(1));
  });
});
