import React, { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  getJobs, cancelJob, pauseJob, resumeJob, deleteJob,
  startSyncJob, startClassifyJob,
} from "../services/api";
import JobProgressBar from "../components/JobProgressBar";
import JobDetail from "../components/JobDetail";
import SyncOptionsModal from "../components/SyncOptionsModal";
import { RefreshCw, Play, XCircle, ChevronDown, ChevronUp, Pause, RotateCcw, Trash2 } from "lucide-react";
import type { SyncScope } from "../types";

const TERMINAL = new Set(["completed", "failed", "cancelled"]);
const ACTIVE = new Set(["queued", "starting", "syncing_assets", "preparing_image", "classifying_ai", "validating_result", "saving_suggestion", "writing_results"]);


export default function Jobs() {
  const qc = useQueryClient();
  const [expandedJobId, setExpandedJobId] = useState<string | null>(null);
  const [typeFilter, setTypeFilter] = useState("");
  const [showSyncModal, setShowSyncModal] = useState(false);
  const [confirmDeleteId, setConfirmDeleteId] = useState<string | null>(null);

  const { data: jobs = [], isLoading } = useQuery({
    queryKey: ["jobs", typeFilter],
    queryFn: () => getJobs({ job_type: typeFilter || undefined, limit: 50 }),
    refetchInterval: 3_000,
  });

  const syncMut = useMutation({
    mutationFn: (params: { scope: SyncScope; album_ids?: string[] }) => startSyncJob(params),
    onSuccess: (d) => {
      setShowSyncModal(false);
      qc.invalidateQueries({ queryKey: ["jobs"] });
      setExpandedJobId(d.job_id);
    },
  });

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

  const pauseMut = useMutation({
    mutationFn: pauseJob,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["jobs"] }),
  });

  const resumeMut = useMutation({
    mutationFn: resumeJob,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["jobs"] }),
  });

  const deleteMut = useMutation({
    mutationFn: deleteJob,
    onSuccess: () => {
      setConfirmDeleteId(null);
      qc.invalidateQueries({ queryKey: ["jobs"] });
    },
  });

  const handleSyncConfirm = (scope: SyncScope, albumIds?: string[]) => {
    syncMut.mutate({ scope, album_ids: albumIds });
  };

  return (
    <div style={{ padding: "32px 40px", maxWidth: 900 }}>
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 24 }}>
        <div>
          <h1 style={{ fontSize: 24, fontWeight: 700, color: "#f1f5f9", margin: 0 }}>Jobs</h1>
          <p style={{ fontSize: 14, color: "#64748b", margin: "4px 0 0" }}>Background sync and classification jobs</p>
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
          {jobs.map((job) => {
            const isActive = ACTIVE.has(job.status);
            const isPaused = job.status === "paused";
            const isTerminal = TERMINAL.has(job.status);

            return (
              <div key={job.id} style={{ background: "#1e293b", border: "1px solid #334155", borderRadius: 10, overflow: "hidden" }}>
                <div
                  style={{ padding: "12px 16px", cursor: "pointer" }}
                  onClick={() => setExpandedJobId(expandedJobId === job.id ? null : job.id)}
                >
                  <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                    <div style={{ flex: 1 }}>
                      <JobProgressBar job={job} compact />
                    </div>

                    {/* Action buttons */}
                    <div style={{ display: "flex", gap: 5, alignItems: "center" }}>
                      {/* Pause — only for active jobs */}
                      {isActive && (
                        <button
                          onClick={(e) => { e.stopPropagation(); pauseMut.mutate(job.id); }}
                          title="Pause"
                          style={{ padding: "5px 8px", borderRadius: 6, border: "1px solid #334155", background: "transparent", color: "#f59e0b", cursor: "pointer" }}
                        >
                          <Pause size={13} />
                        </button>
                      )}

                      {/* Resume — only for paused jobs */}
                      {isPaused && (
                        <button
                          onClick={(e) => { e.stopPropagation(); resumeMut.mutate(job.id); }}
                          title="Resume"
                          style={{ padding: "5px 8px", borderRadius: 6, border: "1px solid #334155", background: "transparent", color: "#22c55e", cursor: "pointer" }}
                        >
                          <RotateCcw size={13} />
                        </button>
                      )}

                      {/* Cancel — for active or paused */}
                      {(isActive || isPaused) && (
                        <button
                          onClick={(e) => { e.stopPropagation(); cancelMut.mutate(job.id); }}
                          title="Cancel"
                          style={{ padding: "5px 8px", borderRadius: 6, border: "1px solid #334155", background: "transparent", color: "#ef4444", cursor: "pointer" }}
                        >
                          <XCircle size={13} />
                        </button>
                      )}

                      {/* Delete — only for terminal jobs */}
                      {isTerminal && (
                        confirmDeleteId === job.id ? (
                          <div style={{ display: "flex", gap: 4, alignItems: "center" }} onClick={(e) => e.stopPropagation()}>
                            <span style={{ fontSize: 11, color: "#94a3b8" }}>Delete?</span>
                            <button
                              onClick={() => deleteMut.mutate(job.id)}
                              style={{ padding: "3px 8px", borderRadius: 5, border: "none", background: "#dc2626", color: "white", fontSize: 11, fontWeight: 600, cursor: "pointer" }}
                            >Yes</button>
                            <button
                              onClick={() => setConfirmDeleteId(null)}
                              style={{ padding: "3px 8px", borderRadius: 5, border: "1px solid #334155", background: "transparent", color: "#64748b", fontSize: 11, cursor: "pointer" }}
                            >No</button>
                          </div>
                        ) : (
                          <button
                            onClick={(e) => { e.stopPropagation(); setConfirmDeleteId(job.id); }}
                            title="Delete"
                            style={{ padding: "5px 8px", borderRadius: 6, border: "1px solid #334155", background: "transparent", color: "#ef4444", cursor: "pointer" }}
                          >
                            <Trash2 size={13} />
                          </button>
                        )
                      )}

                      {expandedJobId === job.id ? <ChevronUp size={14} color="#64748b" /> : <ChevronDown size={14} color="#64748b" />}
                    </div>
                  </div>
                </div>

                {expandedJobId === job.id && (
                  <div style={{ padding: "0 16px 16px", borderTop: "1px solid #1e293b" }}>
                    <JobDetail jobId={job.id} />
                  </div>
                )}
              </div>
            );
          })}
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
