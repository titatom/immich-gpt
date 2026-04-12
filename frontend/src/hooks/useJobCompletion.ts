import { useEffect, useRef } from "react";
import { useQueryClient } from "@tanstack/react-query";
import type { JobRun } from "../types";

const TERMINAL = new Set(["completed", "failed", "cancelled"]);

/**
 * Watches the shared ["jobs"] query cache and invalidates related data queries
 * whenever a job transitions into a terminal state for the first time.
 *
 * - asset_sync completed  → asset list, asset count
 * - classification completed → assets, asset count, bucket stats,
 *                              review queue, review count, asset detail
 *
 * "failed" and "cancelled" only invalidate the jobs list itself (already
 * happens via the 3 s poll), so no extra work is needed for those.
 */
export function useJobCompletion() {
  const qc = useQueryClient();
  // Track which job IDs we have already reacted to so we only fire once.
  const seen = useRef<Map<string, string>>(new Map());

  useEffect(() => {
    // Subscribe to every cache update that touches any query whose key starts
    // with "jobs".  React Query fires this whenever the cache entry changes.
    const unsubscribe = qc.getQueryCache().subscribe((event) => {
      if (event.type !== "updated") return;
      const key = event.query.queryKey;
      if (!Array.isArray(key) || key[0] !== "jobs") return;

      const jobs = event.query.state.data as JobRun[] | undefined;
      if (!jobs) return;

      for (const job of jobs) {
        const prevStatus = seen.current.get(job.id);

        if (TERMINAL.has(job.status) && prevStatus !== job.status) {
          // Only cascade on a genuine completion (not already-terminal jobs
          // that we saw when the page first loaded).
          const isNewlyTerminal = prevStatus !== undefined && prevStatus !== job.status;

          if (isNewlyTerminal && job.status === "completed") {
            if (job.job_type === "asset_sync") {
              qc.invalidateQueries({ queryKey: ["assets"] });
              qc.invalidateQueries({ queryKey: ["asset-count"] });
            } else if (job.job_type === "classification") {
              qc.invalidateQueries({ queryKey: ["assets"] });
              qc.invalidateQueries({ queryKey: ["asset-count"] });
              qc.invalidateQueries({ queryKey: ["bucket-stats"] });
              qc.invalidateQueries({ queryKey: ["review-queue"] });
              qc.invalidateQueries({ queryKey: ["review-count"] });
              qc.invalidateQueries({ queryKey: ["asset-detail"] });
            }
          }

          seen.current.set(job.id, job.status);
        } else if (!TERMINAL.has(job.status)) {
          // Track non-terminal status so we can detect the transition later.
          seen.current.set(job.id, job.status);
        }
      }
    });

    return unsubscribe;
  }, [qc]);
}
