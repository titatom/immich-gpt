import React from "react";
import { useQuery } from "@tanstack/react-query";
import { getJob } from "../services/api";
import LogPanel from "./LogPanel";
import styles from "./JobDetail.module.css";

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

  const hasLogs = job.log_lines && job.log_lines.length > 0;

  return (
    <div className={styles.root}>
      <div className={[styles.stats, hasLogs ? "" : styles.statsEmpty].join(" ")}>
        {job.total_count > 0 && (
          <span className={styles.statCount}>{job.processed_count} / {job.total_count} assets</span>
        )}
        {job.success_count > 0 && (
          <span className={styles.statSuccess}>✓ {job.success_count} succeeded</span>
        )}
        {job.error_count > 0 && (
          <span className={styles.statError}>✗ {job.error_count} failed</span>
        )}
        {job.message && <span className={styles.statMsg}>{job.message}</span>}
        <span className={styles.statPercent}>{Math.round(job.progress_percent)}% complete</span>
      </div>
      {hasLogs && (
        <div>
          <div className={styles.logLabel}>Log</div>
          <LogPanel lines={job.log_lines} maxHeight={250} />
        </div>
      )}
    </div>
  );
}
