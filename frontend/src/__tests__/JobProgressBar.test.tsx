import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import JobProgressBar from "../components/JobProgressBar";
import type { JobRun } from "../types";

const baseJob: JobRun = {
  id: "job-1",
  job_type: "asset_sync",
  status: "queued",
  progress_percent: 0,
  processed_count: 0,
  total_count: 0,
  success_count: 0,
  error_count: 0,
  created_at: "2024-01-01T00:00:00Z",
};

describe("JobProgressBar", () => {
  it("renders without crashing", () => {
    const { container } = render(<JobProgressBar job={baseJob} />);
    expect(container.firstChild).not.toBeNull();
  });

  it("shows 'Asset Sync' label for asset_sync job type", () => {
    render(<JobProgressBar job={baseJob} />);
    expect(screen.getByText("Asset Sync")).toBeInTheDocument();
  });

  it("shows 'AI Classification' label for classification job type", () => {
    render(<JobProgressBar job={{ ...baseJob, job_type: "classification" }} />);
    expect(screen.getByText("AI Classification")).toBeInTheDocument();
  });

  it("shows the status label", () => {
    render(<JobProgressBar job={{ ...baseJob, status: "completed" }} />);
    expect(screen.getByText("Completed")).toBeInTheDocument();
  });

  it("shows 'Failed' for failed status", () => {
    render(<JobProgressBar job={{ ...baseJob, status: "failed" }} />);
    expect(screen.getByText("Failed")).toBeInTheDocument();
  });

  it("shows processed/total counts when total_count > 0", () => {
    render(
      <JobProgressBar
        job={{ ...baseJob, processed_count: 10, total_count: 50 }}
      />
    );
    expect(screen.getByText("10 / 50")).toBeInTheDocument();
  });

  it("hides counts when total_count is 0", () => {
    render(<JobProgressBar job={baseJob} />);
    expect(screen.queryByText(/\//)).not.toBeInTheDocument();
  });

  it("shows success count when > 0", () => {
    render(<JobProgressBar job={{ ...baseJob, success_count: 5 }} />);
    expect(screen.getByText("✓ 5")).toBeInTheDocument();
  });

  it("shows error count when > 0", () => {
    render(<JobProgressBar job={{ ...baseJob, error_count: 2 }} />);
    expect(screen.getByText("✗ 2")).toBeInTheDocument();
  });

  it("shows current_step when present", () => {
    render(<JobProgressBar job={{ ...baseJob, current_step: "Processing photo.jpg" }} />);
    expect(screen.getByText("Processing photo.jpg")).toBeInTheDocument();
  });

  it("shows message when not compact and message present", () => {
    render(
      <JobProgressBar job={{ ...baseJob, message: "Job finished successfully" }} compact={false} />
    );
    expect(screen.getByText("Job finished successfully")).toBeInTheDocument();
  });

  it("hides message in compact mode", () => {
    render(
      <JobProgressBar job={{ ...baseJob, message: "Hidden message" }} compact={true} />
    );
    expect(screen.queryByText("Hidden message")).not.toBeInTheDocument();
  });

  it("shows progress percentage in non-compact mode", () => {
    render(
      <JobProgressBar job={{ ...baseJob, progress_percent: 42 }} compact={false} />
    );
    expect(screen.getByText("42%")).toBeInTheDocument();
  });
});
