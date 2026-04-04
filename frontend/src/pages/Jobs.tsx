import React, { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { getJobs, getJob, cancelJob, startSyncJob, startClassifyJob } from "../services/api";
import JobProgressBar from "../components/JobProgressBar";
import LogPanel from "../components/LogPanel";
import SyncOptionsModal from "../components/SyncOptionsModal";
import { RefreshCw, Play, XCircle, ChevronDown, ChevronUp } from "lucide-react";
import type { SyncScope } from "../types";

function JobDetail({ jobId }: { jobId: string }) {
  const { data: job } = useQuery({
    queryKey: ["job", jobId],
    queryFn: () => getJob(jobId),
    refetchInterval: (q) => {
      const data = q.state.data;
      if (!data) return 2000;
      return ["completed", "failed", "cancelled"].includes(data.status) ? false : 2000;
    },
  });

  if (!job) return null;

  return (
    <div style={{ padding: "12px 0" }}>
      <JobProgressBar job={job} />
      {job.log_lines && job.log_lines.length > 0 && (
        <div style={{ marginTop: 12 }}>
          <div style={{ fontSize: 12, color: "#64748b", marginBottom: 6 }}>Log</div>
          <LogPanel lines={job.log_lines} maxHeight={250} />
        </div>
      )}
    </div>
  );
}

export default function Jobs() {
  const qc = useQueryClient();
  const [expandedJobId, setExpandedJobId] = useState<string | null>(null);
  const [typeFilter, setTypeFilter] = useState("");
  const [showSyncModal, setShowSyncModal] = useState(false);

  const { data: jobs = [], isLoading } = useQuery({
    queryKey: ["jobs", typeFilter],
    queryFn: () => getJobs({ job_type: typeFilter || undefined, limit: 50 }),
    refetchInterval: 3_000,
  });

  const syncMut = useMutation({
    mutationFn: (params: { scope: SyncScope; album_ids?: string[] }) =>
      startSyncJob(params),
    onSuccess: (d) => {
      setShowSyncModal(false);
      qc.invalidateQueries({ queryKey: ["jobs"] });
      setExpandedJobId(d.job_id);
    },
  });

  const handleSyncConfirm = (scope: SyncScope, albumIds?: string[]) => {
    syncMut.mutate({ scope, album_ids: albumIds });
  };

  const classifyMut = useMutation({
    mutationFn: () => startClassifyJob(),
    onSuccess: (d) => {
      qc.invalidateQueries({ queryKey: ["jobs"] });
      setExpandedJobId(d.job_id);
    },
  });

  const cancelMut = useMutation({
    mutationFn: cancelJob,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["jobs"] }),
  });

  return (
    <div style={{ padding: "32px 40px", maxWidth: 900 }}>
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 24 }}>
        <div>
          <h1 style={{ fontSize: 24, fontWeight: 700, color: "#f1f5f9", margin: 0 }}>Jobs</h1>
          <p style={{ fontSize: 14, color: "#64748b", margin: "4px 0 0" }}>
            Background sync and classification jobs
          </p>
        </div>
        <div style={{ display: "flex", gap: 8 }}>
          <button
            onClick={() => setShowSyncModal(true)}
            disabled={syncMut.isPending}
            style={{ display: "flex", alignItems: "center", gap: 6, padding: "9px 16px", borderRadius: 8, border: "none", background: "#1e40af", color: "white", fontSize: 13, fontWeight: 600, cursor: "pointer" }}
          >
            <RefreshCw size={14} /> Sync Assets
          </button>
          <button
            onClick={() => classifyMut.mutate()}
            disabled={classifyMut.isPending}
            style={{ display: "flex", alignItems: "center", gap: 6, padding: "9px 16px", borderRadius: 8, border: "none", background: "#7c3aed", color: "white", fontSize: 13, fontWeight: 600, cursor: "pointer" }}
          >
            <Play size={14} /> Classify
          </button>
        </div>
      </div>

      {/* Filter */}
      <div style={{ marginBottom: 20 }}>
        <select
          value={typeFilter}
          onChange={(e) => setTypeFilter(e.target.value)}
          style={{ background: "#1e293b", border: "1px solid #334155", color: "#94a3b8", borderRadius: 8, padding: "7px 12px", fontSize: 13 }}
        >
          <option value="">All types</option>
          <option value="asset_sync">Asset Sync</option>
          <option value="classification">Classification</option>
        </select>
      </div>

      {isLoading ? (
        <div style={{ color: "#64748b", padding: 32, textAlign: "center" }}>Loading...</div>
      ) : jobs.length === 0 ? (
        <div style={{ textAlign: "center", padding: 64, color: "#64748b" }}>No jobs yet.</div>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
          {jobs.map((job) => (
            <div
              key={job.id}
              style={{
                background: "#1e293b",
                border: "1px solid #334155",
                borderRadius: 10,
                overflow: "hidden",
              }}
            >
              {/* Job row */}
              <div
                style={{ padding: "12px 16px", cursor: "pointer" }}
                onClick={() => setExpandedJobId(expandedJobId === job.id ? null : job.id)}
              >
                <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                  <div style={{ flex: 1 }}>
                    <JobProgressBar job={job} compact />
                  </div>
                  <div style={{ display: "flex", gap: 6, alignItems: "center" }}>
                    {!["completed", "failed", "cancelled"].includes(job.status) && (
                      <button
                        onClick={(e) => { e.stopPropagation(); cancelMut.mutate(job.id); }}
                        style={{ padding: "5px 8px", borderRadius: 6, border: "1px solid #334155", background: "transparent", color: "#ef4444", cursor: "pointer" }}
                        title="Cancel"
                      >
                        <XCircle size={13} />
                      </button>
                    )}
                    {expandedJobId === job.id ? <ChevronUp size={14} color="#64748b" /> : <ChevronDown size={14} color="#64748b" />}
                  </div>
                </div>
              </div>

              {/* Expanded detail */}
              {expandedJobId === job.id && (
                <div style={{ padding: "0 16px 16px", borderTop: "1px solid #1e293b" }}>
                  <JobDetail jobId={job.id} />
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      {showSyncModal && (
        <SyncOptionsModal
          onClose={() => setShowSyncModal(false)}
          onConfirm={handleSyncConfirm}
          isLoading={syncMut.isPending}
        />
      )}
    </div>
  );
}
