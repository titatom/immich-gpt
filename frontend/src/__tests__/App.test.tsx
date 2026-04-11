import { describe, it, expect, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
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
    getBuckets: vi.fn().mockResolvedValue([]),
    createBucket: noop,
    updateBucket: noop,
    deleteBucket: noop,
    getPrompts: vi.fn().mockResolvedValue([]),
    createPrompt: noop,
    updatePrompt: noop,
    deletePrompt: noop,
    getAssets: vi.fn().mockResolvedValue([]),
    getAssetCount: vi.fn().mockResolvedValue({ count: 0 }),
    getJobs: vi.fn().mockResolvedValue([]),
    getJob: noop,
    startSyncJob: noop,
    startClassifyJob: noop,
    cancelJob: noop,
    getReviewQueue: vi.fn().mockResolvedValue([]),
    getReviewCount: vi.fn().mockResolvedValue({ count: 0 }),
    getReviewItem: noop,
    approveAsset: noop,
    rejectAsset: noop,
    bulkReview: noop,
    getAlbums: vi.fn().mockResolvedValue([]),
    getAuditLogs: vi.fn().mockResolvedValue([]),
    getAuditLogCount: vi.fn().mockResolvedValue({ count: 0 }),
    getBucketStats: vi.fn().mockResolvedValue([]),
    getProviderModels: vi.fn().mockResolvedValue([]),
    saveImmichSettings: noop,
    getThumbnailUrl: (id: string, size = "thumbnail") =>
      `/api/thumbnails/${id}?size=${size}`,
  };
});

function makeClient() {
  return new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
}

vi.mock("../components/BrandLogo", () => ({
  default: ({ subtitle = "Review-first AI library organization" }: { subtitle?: string }) => (
    <div>
      <img src="/logo.svg" alt="immich-gpt logo" />
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

  it("renders all nav links in the sidebar", async () => {
    render(
      <Wrapper>
        <App />
      </Wrapper>
    );
    // Use getAllByText since nav + page heading may both match
    await waitFor(() => expect(screen.getAllByText("Dashboard").length).toBeGreaterThanOrEqual(1));
    expect(screen.getAllByText("Review").length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText("Buckets").length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText("Jobs").length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText("Logs").length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText("Settings").length).toBeGreaterThanOrEqual(1);
    expect(screen.getByRole("link", { name: "Source code" })).toHaveAttribute(
      "href",
      "https://github.com/titatom/immich-gpt",
    );
  });

  it("renders AI metadata enrichment label", async () => {
    render(
      <Wrapper>
        <App />
      </Wrapper>
    );
    await waitFor(() => expect(screen.getByText("Review-first AI library organization")).toBeInTheDocument());
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
    // Multiple instances of "Dashboard" is expected (nav + page heading)
    await waitFor(() => expect(screen.getAllByText("Dashboard").length).toBeGreaterThanOrEqual(1));
  });

  it("renders the jobs page on /jobs route", async () => {
    render(
      <Wrapper path="/jobs">
        <App />
      </Wrapper>
    );
    // At least the nav link must be present
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

  it("renders buckets page on /buckets route", async () => {
    render(
      <Wrapper path="/buckets">
        <App />
      </Wrapper>
    );
    await waitFor(() => expect(screen.getAllByText("Buckets").length).toBeGreaterThanOrEqual(1));
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
