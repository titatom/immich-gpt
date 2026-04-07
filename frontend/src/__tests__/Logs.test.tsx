import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import React from "react";
import Logs from "../pages/Logs";

vi.mock("../services/api", () => ({
  getAuditLogs: vi.fn(),
  getAuditLogCount: vi.fn(),
  getJobs: vi.fn(),
}));

import { getAuditLogs, getAuditLogCount, getJobs } from "../services/api";

function renderPage() {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });

  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter initialEntries={["/logs"]}>
        <Logs />
      </MemoryRouter>
    </QueryClientProvider>
  );
}

describe("Logs page", () => {
  beforeEach(() => {
    vi.mocked(getAuditLogs).mockResolvedValue([
      {
        id: "log-1",
        action: "writeback_description",
        status: "success",
        level: "info",
        source: "writeback",
        job_run_id: "job-1",
        details_json: { description: "Updated description" },
        created_at: "2026-04-07T12:00:00Z",
      },
    ]);
    vi.mocked(getAuditLogCount).mockResolvedValue({ count: 1 });
    vi.mocked(getJobs).mockResolvedValue([
      {
        id: "job-1",
        job_type: "classification",
        status: "completed",
        current_step: "writing_results",
        progress_percent: 100,
        processed_count: 12,
        total_count: 12,
        success_count: 11,
        error_count: 1,
        message: "Completed with one skipped asset",
        log_lines: ["[12:00:00] Starting classification", "[12:00:15] Completed"],
        created_at: "2026-04-07T11:59:00Z",
        updated_at: "2026-04-07T12:00:15Z",
        completed_at: "2026-04-07T12:00:15Z",
      },
    ]);
  });

  it("shows operational activity and recent job output", async () => {
    renderPage();

    await waitFor(() => expect(screen.getByText("Logs")).toBeInTheDocument());
    expect(screen.getByText("Recent job output")).toBeInTheDocument();
    expect(screen.getByText("Activity log")).toBeInTheDocument();
    expect(screen.getByText("writeback_description")).toBeInTheDocument();

    await userEvent.click(screen.getByText("Classification job"));

    await waitFor(() => expect(screen.getByText("[12:00:00] Starting classification")).toBeInTheDocument());
    expect(screen.getByRole("button", { name: "Show matching activity" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Open jobs page" })).toBeInTheDocument();
  });
});
