import React from "react";
import { CheckCircle, XCircle, Clock, Loader } from "lucide-react";
import type { JobRun } from "../types";
import styles from "./JobProgressBar.module.css";

interface Props {
  job: JobRun;
  compact?: boolean;
}

const STATUS_COLORS: Record<string, string> = {
  queued:           "#94a3b8",
  starting:         "#38bdf8",
  syncing_assets:   "#38bdf8",
  preparing_image:  "#a78bfa",
  classifying_ai:   "#f59e0b",
  validating_result:"#f59e0b",
  saving_suggestion:"#34d399",
  writing_results:  "#34d399",
  completed:        "#22c55e",
  failed:           "#ef4444",
  cancelled:        "#64748b",
  paused:           "#f59e0b",
};

const STATUS_LABELS: Record<string, string> = {
  queued:            "Queued",
  starting:          "Starting",
  syncing_assets:    "Syncing assets",
  preparing_image:   "Preparing images",
  classifying_ai:    "Classifying with AI",
  validating_result: "Validating",
  saving_suggestion: "Saving suggestions",
  writing_results:   "Writing results",
  completed:         "Completed",
  failed:            "Failed",
  cancelled:         "Cancelled",
  paused:            "Paused",
};

function StatusIcon({ status }: { status: string }) {
  if (status === "completed") return <CheckCircle size={16} color="#22c55e" />;
  if (status === "failed")    return <XCircle size={16} color="#ef4444" />;
  if (status === "cancelled") return <XCircle size={16} color="#64748b" />;
  if (status === "queued" || status === "paused") return <Clock size={16} color="#94a3b8" />;
  return <Loader size={16} color="#38bdf8" style={{ animation: "spin 1s linear infinite" }} />;
}

export default function JobProgressBar({ job, compact = false }: Props) {
  const color = STATUS_COLORS[job.status] ?? "#94a3b8";
  const label = STATUS_LABELS[job.status] ?? job.status;

  return (
    <div className={[styles.root, compact ? styles.rootCompact : styles.rootFull].join(" ")}>
      <div className={[styles.header, compact ? styles.headerCompact : styles.headerFull].join(" ")}>
        <StatusIcon status={job.status} />
        <span className={styles.jobType}>
          {job.job_type === "asset_sync" ? "Asset Sync" : "AI Classification"}
        </span>
        <span
          className={styles.statusBadge}
          style={{ color, background: `${color}18` }}
        >
          {label}
        </span>
      </div>

      <div className={[styles.track, compact ? styles.trackCompact : styles.trackFull].join(" ")}>
        <div
          className={styles.fill}
          style={{ width: `${job.progress_percent}%`, background: color }}
        />
      </div>

      <div className={styles.stats}>
        {job.total_count > 0 && (
          <span className={styles.statCount}>
            {job.processed_count} / {job.total_count}
          </span>
        )}
        {job.success_count > 0 && (
          <span className={styles.statSuccess}>✓ {job.success_count}</span>
        )}
        {job.error_count > 0 && (
          <span className={styles.statError}>✗ {job.error_count}</span>
        )}
        {job.current_step && (
          <span className={styles.statStep}>{job.current_step}</span>
        )}
        {!compact && (
          <span className={styles.statPercent}>
            {Math.round(job.progress_percent)}%
          </span>
        )}
      </div>

      {job.message && !compact && (
        <div className={styles.message}>{job.message}</div>
      )}
    </div>
  );
}
