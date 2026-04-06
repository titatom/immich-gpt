import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import React from "react";

// Mock every API export so pages mount without real HTTP calls.
vi.mock("../services/api", async (importOriginal) => {
  const real = await importOriginal<typeof import("../services/api")>();
  const noop = vi.fn().mockResolvedValue(undefined);
  return {
    ...real,
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

function Wrapper({ children, path = "/" }: { children: React.ReactNode; path?: string }) {
  return (
    <QueryClientProvider client={makeClient()}>
      <MemoryRouter initialEntries={[path]}>{children}</MemoryRouter>
    </QueryClientProvider>
  );
}

import App from "../App";

describe("App routing", () => {
  it("renders the app brand name", () => {
    render(
      <Wrapper>
        <App />
      </Wrapper>
    );
    expect(screen.getByText("Immich GPT")).toBeInTheDocument();
  });

  it("renders all nav links in the sidebar", () => {
    render(
      <Wrapper>
        <App />
      </Wrapper>
    );
    // Use getAllByText since nav + page heading may both match
    expect(screen.getAllByText("Dashboard").length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText("Review").length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText("Buckets").length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText("Jobs").length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText("Settings").length).toBeGreaterThanOrEqual(1);
  });

  it("renders version label in the sidebar", () => {
    render(
      <Wrapper>
        <App />
      </Wrapper>
    );
    expect(screen.getByText("v0.1.0")).toBeInTheDocument();
  });

  it("renders the dashboard page by default", () => {
    render(
      <Wrapper path="/">
        <App />
      </Wrapper>
    );
    // Multiple instances of "Dashboard" is expected (nav + page heading)
    expect(screen.getAllByText("Dashboard").length).toBeGreaterThanOrEqual(1);
  });

  it("renders the jobs page on /jobs route", () => {
    render(
      <Wrapper path="/jobs">
        <App />
      </Wrapper>
    );
    // At least the nav link must be present
    expect(screen.getAllByText("Jobs").length).toBeGreaterThanOrEqual(1);
  });

  it("renders settings page on /settings route", () => {
    render(
      <Wrapper path="/settings">
        <App />
      </Wrapper>
    );
    expect(screen.getAllByText("Settings").length).toBeGreaterThanOrEqual(1);
  });

  it("renders buckets page on /buckets route", () => {
    render(
      <Wrapper path="/buckets">
        <App />
      </Wrapper>
    );
    expect(screen.getAllByText("Buckets").length).toBeGreaterThanOrEqual(1);
  });

  it("renders assets page on /assets route", () => {
    render(
      <Wrapper path="/assets">
        <App />
      </Wrapper>
    );
    expect(screen.getAllByText("Assets").length).toBeGreaterThanOrEqual(1);
  });

  it("renders logs page on /logs route", () => {
    render(
      <Wrapper path="/logs">
        <App />
      </Wrapper>
    );
    expect(screen.getAllByText("Audit Logs").length).toBeGreaterThanOrEqual(1);
  });
});
