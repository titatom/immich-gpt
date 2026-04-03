import React from "react";
import { CheckCircle, XCircle, Clock, Loader } from "lucide-react";
import type { JobRun } from "../types";

interface Props {
  job: JobRun;
  compact?: boolean;
}

const statusColors: Record<string, string> = {
  queued: "#94a3b8",
  starting: "#38bdf8",
  syncing_assets: "#38bdf8",
  preparing_image: "#a78bfa",
  classifying_ai: "#f59e0b",
  validating_result: "#f59e0b",
  saving_suggestion: "#34d399",
  writing_results: "#34d399",
  completed: "#22c55e",
  failed: "#ef4444",
  cancelled: "#64748b",
};

const statusLabels: Record<string, string> = {
  queued: "Queued",
  starting: "Starting",
  syncing_assets: "Syncing assets",
  preparing_image: "Preparing images",
  classifying_ai: "Classifying with AI",
  validating_result: "Validating",
  saving_suggestion: "Saving suggestions",
  writing_results: "Writing results",
  completed: "Completed",
  failed: "Failed",
  cancelled: "Cancelled",
};

function StatusIcon({ status }: { status: string }) {
  if (status === "completed") return <CheckCircle size={16} color="#22c55e" />;
  if (status === "failed") return <XCircle size={16} color="#ef4444" />;
  if (status === "cancelled") return <XCircle size={16} color="#64748b" />;
  if (status === "queued") return <Clock size={16} color="#94a3b8" />;
  return <Loader size={16} color="#38bdf8" style={{ animation: "spin 1s linear infinite" }} />;
}

export default function JobProgressBar({ job, compact = false }: Props) {
  const color = statusColors[job.status] || "#94a3b8";
  const label = statusLabels[job.status] || job.status;

  return (
    <div style={{
      background: "#1e293b",
      border: "1px solid #334155",
      borderRadius: 10,
      padding: compact ? "12px 16px" : "16px 20px",
    }}>
      {/* Header row */}
      <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: compact ? 8 : 12 }}>
        <StatusIcon status={job.status} />
        <span style={{ fontSize: 13, fontWeight: 600, color: "#f1f5f9" }}>
          {job.job_type === "asset_sync" ? "Asset Sync" : "AI Classification"}
        </span>
        <span style={{
          marginLeft: "auto",
          fontSize: 11,
          fontWeight: 600,
          color,
          background: `${color}18`,
          padding: "2px 8px",
          borderRadius: 6,
        }}>
          {label}
        </span>
      </div>

      {/* Progress bar */}
      <div style={{
        height: 6,
        background: "#0f172a",
        borderRadius: 3,
        overflow: "hidden",
        marginBottom: compact ? 8 : 12,
      }}>
        <div style={{
          height: "100%",
          width: `${job.progress_percent}%`,
          background: color,
          borderRadius: 3,
          transition: "width 0.5s ease",
        }} />
      </div>

      {/* Stats row */}
      <div style={{ display: "flex", gap: 16, fontSize: 12, color: "#64748b", flexWrap: "wrap" }}>
        {job.total_count > 0 && (
          <span style={{ color: "#94a3b8" }}>
            {job.processed_count} / {job.total_count}
          </span>
        )}
        {job.success_count > 0 && (
          <span style={{ color: "#22c55e" }}>✓ {job.success_count}</span>
        )}
        {job.error_count > 0 && (
          <span style={{ color: "#ef4444" }}>✗ {job.error_count}</span>
        )}
        {job.current_step && (
          <span style={{ color: "#64748b", flex: 1, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
            {job.current_step}
          </span>
        )}
        {!compact && (
          <span style={{ color: "#475569", marginLeft: "auto" }}>
            {Math.round(job.progress_percent)}%
          </span>
        )}
      </div>

      {/* Message */}
      {job.message && !compact && (
        <div style={{ marginTop: 8, fontSize: 12, color: "#64748b" }}>
          {job.message}
        </div>
      )}
    </div>
  );
}
