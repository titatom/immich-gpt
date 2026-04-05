import React from "react";
import { useQuery } from "@tanstack/react-query";
import { getJob } from "../services/api";
import LogPanel from "./LogPanel";

const TERMINAL = new Set(["completed", "failed", "cancelled"]);

interface Props {
  jobId: string;
}

export default function JobDetail({ jobId }: Props) {
  const { data: job } = useQuery({
    queryKey: ["job", jobId],
    queryFn: () => getJob(jobId),
    refetchInterval: (q) => {
      const d = q.state.data;
      if (!d) return 2000;
      return TERMINAL.has(d.status) || d.status === "paused" ? false : 2000;
    },
  });
  if (!job) return null;
  return (
    <div style={{ padding: "12px 0" }}>
      <div style={{
        display: "flex", gap: 16, fontSize: 12, color: "#64748b", flexWrap: "wrap",
        marginBottom: job.log_lines && job.log_lines.length > 0 ? 12 : 0,
      }}>
        {job.total_count > 0 && (
          <span style={{ color: "#94a3b8" }}>{job.processed_count} / {job.total_count} assets</span>
        )}
        {job.success_count > 0 && (
          <span style={{ color: "#22c55e" }}>✓ {job.success_count} succeeded</span>
        )}
        {job.error_count > 0 && (
          <span style={{ color: "#ef4444" }}>✗ {job.error_count} failed</span>
        )}
        {job.message && (
          <span style={{ color: "#64748b" }}>{job.message}</span>
        )}
        <span style={{ color: "#475569", marginLeft: "auto" }}>{Math.round(job.progress_percent)}% complete</span>
      </div>
      {job.log_lines && job.log_lines.length > 0 && (
        <div>
          <div style={{ fontSize: 12, color: "#64748b", marginBottom: 6 }}>Log</div>
          <LogPanel lines={job.log_lines} maxHeight={250} />
        </div>
      )}
    </div>
  );
}
