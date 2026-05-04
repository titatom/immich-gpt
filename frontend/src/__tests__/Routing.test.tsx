import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import React from "react";

const mocks = vi.hoisted(() => ({
  treeMock: vi.fn(),
  createMock: vi.fn(),
  updateMock: vi.fn(),
  deleteMock: vi.fn(),
  dupMock: vi.fn(),
  examplesMock: vi.fn(),
  addExampleMock: vi.fn(),
  deleteExampleMock: vi.fn(),
  promptPreviewMock: vi.fn(),
  classifyMock: vi.fn(),
  plansMock: vi.fn(),
  planSummaryMock: vi.fn(),
  approveMock: vi.fn(),
  rejectMock: vi.fn(),
  applyMock: vi.fn(),
}));

vi.mock("../services/api", () => ({
  getRoutingTree: mocks.treeMock,
  createRoutingNode: mocks.createMock,
  updateRoutingNode: mocks.updateMock,
  deleteRoutingNode: mocks.deleteMock,
  duplicateRoutingNode: mocks.dupMock,
  moveRoutingNode: vi.fn(),
  listRoutingNodes: vi.fn().mockResolvedValue([]),
  listRoutingExamples: mocks.examplesMock,
  addRoutingExample: mocks.addExampleMock,
  deleteRoutingExample: mocks.deleteExampleMock,
  getRoutingPromptPreview: mocks.promptPreviewMock,
  startRoutingClassify: mocks.classifyMock,
  listRoutingPlans: mocks.plansMock,
  getRoutingPlanSummary: mocks.planSummaryMock,
  getRoutingPlanItems: vi.fn().mockResolvedValue([]),
  approveRoutingPlanItems: mocks.approveMock,
  rejectRoutingPlanItems: mocks.rejectMock,
  moveRoutingPlanItems: vi.fn(),
  applyRoutingPlan: mocks.applyMock,
  getRoutingPlan: vi.fn(),
}));

const {
  treeMock, createMock, examplesMock, promptPreviewMock,
  plansMock, planSummaryMock, approveMock, rejectMock,
} = mocks;

import Routing from "../pages/Routing";
import RoutingPlans from "../pages/RoutingPlans";

function makeClient() {
  return new QueryClient({
    defaultOptions: { queries: { retry: false, gcTime: 0, staleTime: 0 } },
  });
}

function Wrapper({ children }: { children: React.ReactNode }) {
  return (
    <QueryClientProvider client={makeClient()}>
      <MemoryRouter>{children}</MemoryRouter>
    </QueryClientProvider>
  );
}

beforeEach(() => {
  treeMock.mockReset();
  createMock.mockReset();
  examplesMock.mockReset();
  promptPreviewMock.mockReset();
  plansMock.mockReset();
  planSummaryMock.mockReset();
  approveMock.mockReset();
  rejectMock.mockReset();
});

describe("Routing tree page", () => {
  it("renders nested nodes", async () => {
    treeMock.mockResolvedValue({
      nodes: [
        {
          id: "n1", parent_id: null, name: "Personal", path: "Personal",
          is_leaf: false, enabled: true, priority: 100,
          destination_type: "virtual", create_album_if_missing: true,
          auto_apply_enabled: false, auto_apply_threshold: 0.95, review_below_threshold: 0.85,
          exclusive: false, allow_secondary: true,
          minimum_quality: "any", allow_blurry: true, allow_dark: true,
          allow_screenshot: true, allow_duplicate: true,
          suggest_description: true, suggest_tags: true, suggest_location: false, suggest_caption: false,
          write_description: true, write_tags: true, write_location: false,
          custom_prompt_enabled: false,
          positive_criteria: [], negative_criteria: [],
          privacy_rules: {}, quality_rules: {}, automation_rules: {}, metadata_rules: {},
          children: [
            {
              id: "n2", parent_id: "n1", name: "Lake House", path: "Personal/Lake House",
              is_leaf: true, enabled: true, priority: 100,
              destination_type: "virtual", create_album_if_missing: true,
              auto_apply_enabled: false, auto_apply_threshold: 0.95, review_below_threshold: 0.85,
              exclusive: false, allow_secondary: true,
              minimum_quality: "any", allow_blurry: true, allow_dark: true,
              allow_screenshot: true, allow_duplicate: true,
              suggest_description: true, suggest_tags: true, suggest_location: false, suggest_caption: false,
              write_description: true, write_tags: true, write_location: false,
              custom_prompt_enabled: false,
              positive_criteria: [], negative_criteria: [],
              privacy_rules: {}, quality_rules: {}, automation_rules: {}, metadata_rules: {},
              children: [],
            },
          ],
        },
      ],
    });

    render(<Wrapper><Routing /></Wrapper>);
    await waitFor(() => expect(screen.getAllByText("Personal").length).toBeGreaterThan(0));
    // Children render only after the parent is expanded; click chevron toggle.
    expect(screen.getAllByText("Personal").length).toBeGreaterThan(0);
  });

  it("creates a new root node via the inline form", async () => {
    treeMock.mockResolvedValue({ nodes: [] });
    createMock.mockResolvedValue({ id: "new-1" });

    render(<Wrapper><Routing /></Wrapper>);
    await waitFor(() => expect(screen.getByText(/Add root/i)).toBeInTheDocument());
    fireEvent.click(screen.getByText(/Add root/i));
    const input = await screen.findByPlaceholderText("Name");
    fireEvent.change(input, { target: { value: "Family" } });
    const createBtn = await screen.findByRole("button", { name: "Create" });
    fireEvent.click(createBtn);
    await waitFor(() => expect(createMock).toHaveBeenCalled());
    const firstCallArg = createMock.mock.calls[0]?.[0];
    expect(firstCallArg).toEqual(
      expect.objectContaining({ name: "Family", parent_id: null, is_leaf: true })
    );
  });

  it("opens the leaf editor when a node is selected", async () => {
    const node = {
      id: "leaf-1", parent_id: null, name: "Lake House", path: "Lake House",
      is_leaf: true, enabled: true, priority: 100,
      destination_type: "virtual", create_album_if_missing: true,
      auto_apply_enabled: false, auto_apply_threshold: 0.95, review_below_threshold: 0.85,
      exclusive: false, allow_secondary: true,
      minimum_quality: "any", allow_blurry: true, allow_dark: true,
      allow_screenshot: true, allow_duplicate: true,
      suggest_description: true, suggest_tags: true, suggest_location: false, suggest_caption: false,
      write_description: true, write_tags: true, write_location: false,
      custom_prompt_enabled: false,
      positive_criteria: ["sharp image"], negative_criteria: [],
      privacy_rules: {}, quality_rules: {}, automation_rules: {}, metadata_rules: {},
      children: [],
    };
    treeMock.mockResolvedValue({ nodes: [node] });
    examplesMock.mockResolvedValue([]);
    promptPreviewMock.mockResolvedValue({ bucket_id: "n1", path: "Lake House", compiled_prompt: "X" });

    render(<Wrapper><Routing /></Wrapper>);
    await waitFor(() => expect(screen.getAllByText("Lake House").length).toBeGreaterThan(0));
    fireEvent.click(screen.getAllByText("Lake House")[0]);
    await waitFor(() => expect(screen.getByText("Matching")).toBeInTheDocument());

    fireEvent.click(screen.getByText("Matching"));
    await waitFor(() => expect(screen.getByText("sharp image")).toBeInTheDocument());
  });
});

describe("Routing plans page", () => {
  it("renders empty state when no plans", async () => {
    plansMock.mockResolvedValue([]);
    render(<Wrapper><RoutingPlans /></Wrapper>);
    await waitFor(() => expect(screen.getByText(/No plans yet/i)).toBeInTheDocument());
  });

  it("shows plan summary groups when a plan is selected", async () => {
    plansMock.mockResolvedValue([
      { id: "p1", job_id: "j1", status: "ready", item_count: 5,
        created_at: new Date().toISOString(), updated_at: new Date().toISOString() },
    ]);
    planSummaryMock.mockResolvedValue({
      plan_id: "p1", total: 5,
      groups: {
        auto_applied: [],
        ready_to_approve: [{ path: "Personal/Lake", bucket_id: "b1", count: 3, item_ids: ["i1","i2","i3"] }],
        needs_review: [{ path: "Family/Kids", bucket_id: "b2", count: 2, item_ids: ["i4","i5"] }],
        trash_candidates: [],
        rejected: [],
        failed: [],
      },
    });
    render(<Wrapper><RoutingPlans /></Wrapper>);
    await waitFor(() => expect(screen.getByText(/ready/i)).toBeInTheDocument());
    fireEvent.click(screen.getByText(/ready/i));
    await waitFor(() => expect(screen.getByText("Ready to approve")).toBeInTheDocument());
    expect(screen.getByText("Needs review")).toBeInTheDocument();
    expect(screen.getByText("Personal/Lake")).toBeInTheDocument();
    expect(screen.getByText("Family/Kids")).toBeInTheDocument();
  });

  it("approves a group via the Approve button", async () => {
    plansMock.mockResolvedValue([
      { id: "p1", job_id: null, status: "ready", item_count: 1,
        created_at: new Date().toISOString(), updated_at: new Date().toISOString() },
    ]);
    planSummaryMock.mockResolvedValue({
      plan_id: "p1", total: 1,
      groups: {
        auto_applied: [],
        ready_to_approve: [{ path: "X", bucket_id: "b1", count: 1, item_ids: ["i1"] }],
        needs_review: [],
        trash_candidates: [],
        rejected: [],
        failed: [],
      },
    });
    approveMock.mockResolvedValue({ approved: 1 });
    render(<Wrapper><RoutingPlans /></Wrapper>);
    await waitFor(() => expect(screen.getByText(/ready/i)).toBeInTheDocument());
    fireEvent.click(screen.getByText(/ready/i));
    await waitFor(() => expect(screen.getByText("Approve")).toBeInTheDocument());
    fireEvent.click(screen.getByText("Approve"));
    await waitFor(() => expect(approveMock).toHaveBeenCalled());
  });
});
