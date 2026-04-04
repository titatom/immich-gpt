import React, { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import {
  getImmichSettings,
  getAssetCount,
  getReviewCount,
  getJobs,
  getBucketStats,
  getAlbums,
  startSyncJob,
  startClassifyJob,
  clearTerminalJobs,
} from "../services/api";
import type { BucketStat, SyncScope, ImmichAlbum } from "../types";
import JobProgressBar from "../components/JobProgressBar";
import {
  Database, Eye, Play, RefreshCw, AlertTriangle, CheckCircle,
  Star, FolderOpen, ChevronDown, ChevronUp, Trash2,
} from "lucide-react";

function StatCard({ label, value, color = "#f1f5f9", icon }: {
  label: string; value: string | number; color?: string; icon?: React.ReactNode;
}) {
  return (
    <div style={{
      background: "#1e293b", border: "1px solid #334155",
      borderRadius: 12, padding: "20px 24px", flex: 1, minWidth: 140,
    }}>
      <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 8 }}>
        {icon}
        <span style={{ fontSize: 12, color: "#64748b", fontWeight: 500 }}>{label}</span>
      </div>
      <div style={{ fontSize: 28, fontWeight: 700, color }}>{value}</div>
    </div>
  );
}

const SCOPE_OPTIONS: { value: SyncScope; label: string; desc: string; icon: React.ReactNode }[] = [
  { value: "all", label: "All Photos & Videos", desc: "Every asset in your Immich library", icon: <RefreshCw size={14} /> },
  { value: "favorites", label: "Favourites Only", desc: "Assets you have marked as favourite", icon: <Star size={14} /> },
  { value: "albums", label: "Specific Albums", desc: "Choose one or more albums", icon: <FolderOpen size={14} /> },
];

function SyncPanel({
  onSync, isLoading, disabled,
}: { onSync: (scope: SyncScope, albumIds?: string[]) => void; isLoading: boolean; disabled: boolean }) {
  const [scope, setScope] = useState<SyncScope>("all");
  const [selectedAlbumIds, setSelectedAlbumIds] = useState<Set<string>>(new Set());
  const [albumsExpanded, setAlbumsExpanded] = useState(false);
  const [albumSearch, setAlbumSearch] = useState("");

  const { data: albums = [] } = useQuery<ImmichAlbum[]>({
    queryKey: ["albums"],
    queryFn: getAlbums,
    enabled: scope === "albums",
  });

  const filtered = albums.filter((a) =>
    a.albumName.toLowerCase().includes(albumSearch.toLowerCase())
  );

  const toggle = (id: string) => setSelectedAlbumIds((prev) => {
    const next = new Set(prev);
    if (next.has(id)) { next.delete(id); } else { next.add(id); }
    return next;
  });

  const canSync = !disabled && !isLoading && (scope !== "albums" || selectedAlbumIds.size > 0);

  return (
    <div style={{
      background: "#1e293b", border: "1px solid #334155",
      borderRadius: 12, padding: "18px 20px", marginBottom: 32,
    }}>
      <div style={{ fontSize: 13, fontWeight: 600, color: "#94a3b8", marginBottom: 14 }}>
        Sync Assets
      </div>

      {/* Scope selector */}
      <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginBottom: 14 }}>
        {SCOPE_OPTIONS.map((opt) => (
          <button
            key={opt.value}
            onClick={() => { setScope(opt.value); if (opt.value !== "albums") setSelectedAlbumIds(new Set()); }}
            style={{
              display: "flex", alignItems: "center", gap: 6,
              padding: "7px 14px", borderRadius: 8, border: "none",
              background: scope === opt.value ? "#1e40af" : "#0f172a",
              color: scope === opt.value ? "white" : "#94a3b8",
              fontSize: 13, fontWeight: scope === opt.value ? 600 : 400,
              cursor: "pointer", transition: "background 0.15s",
            }}
          >
            {opt.icon} {opt.label}
          </button>
        ))}
      </div>

      {/* Scope description */}
      <div style={{ fontSize: 12, color: "#475569", marginBottom: 14 }}>
        {SCOPE_OPTIONS.find((o) => o.value === scope)?.desc}
      </div>

      {/* Album picker */}
      {scope === "albums" && (
        <div style={{ marginBottom: 14 }}>
          <div
            style={{
              display: "flex", alignItems: "center", justifyContent: "space-between",
              padding: "8px 12px", background: "#0f172a", borderRadius: 8,
              border: "1px solid #334155", cursor: "pointer", marginBottom: 6,
            }}
            onClick={() => setAlbumsExpanded((v) => !v)}
          >
            <span style={{ fontSize: 13, color: "#94a3b8" }}>
              Albums
              {selectedAlbumIds.size > 0 && (
                <span style={{ marginLeft: 8, background: "#1e40af", color: "#93c5fd", borderRadius: 6, padding: "1px 8px", fontSize: 11 }}>
                  {selectedAlbumIds.size} selected
                </span>
              )}
            </span>
            {albumsExpanded ? <ChevronUp size={13} color="#64748b" /> : <ChevronDown size={13} color="#64748b" />}
          </div>

          {albumsExpanded && (
            <div style={{ border: "1px solid #334155", borderRadius: 8, overflow: "hidden" }}>
              <div style={{ padding: "8px 10px", borderBottom: "1px solid #334155" }}>
                <input
                  type="text"
                  placeholder="Search albums…"
                  value={albumSearch}
                  onChange={(e) => setAlbumSearch(e.target.value)}
                  style={{
                    width: "100%", boxSizing: "border-box",
                    background: "#0f172a", border: "1px solid #334155",
                    borderRadius: 6, padding: "6px 10px", fontSize: 13,
                    color: "#f1f5f9", outline: "none",
                  }}
                />
              </div>
              <div style={{ maxHeight: 180, overflowY: "auto" }}>
                {filtered.length === 0 ? (
                  <div style={{ padding: 16, textAlign: "center", fontSize: 13, color: "#64748b" }}>
                    {albums.length === 0 ? "No albums found" : "No matches"}
                  </div>
                ) : filtered.map((a) => {
                  const sel = selectedAlbumIds.has(a.id);
                  return (
                    <div
                      key={a.id}
                      onClick={() => toggle(a.id)}
                      style={{
                        display: "flex", alignItems: "center", gap: 10,
                        padding: "8px 12px", cursor: "pointer",
                        background: sel ? "rgba(59,130,246,0.08)" : "transparent",
                        borderBottom: "1px solid #1e293b",
                      }}
                    >
                      <div style={{
                        width: 14, height: 14, borderRadius: 3, flexShrink: 0,
                        border: `2px solid ${sel ? "#3b82f6" : "#475569"}`,
                        background: sel ? "#3b82f6" : "transparent",
                        display: "flex", alignItems: "center", justifyContent: "center",
                      }}>
                        {sel && <svg width="8" height="6" viewBox="0 0 8 6" fill="none"><path d="M1 3L3 5L7 1" stroke="white" strokeWidth="1.5" strokeLinecap="round" /></svg>}
                      </div>
                      <span style={{ fontSize: 13, color: "#e2e8f0", flex: 1 }}>{a.albumName}</span>
                      <span style={{ fontSize: 11, color: "#64748b" }}>{a.assetCount.toLocaleString()}</span>
                    </div>
                  );
                })}
              </div>
            </div>
          )}
        </div>
      )}

      <button
        onClick={() => onSync(scope, scope === "albums" ? Array.from(selectedAlbumIds) : undefined)}
        disabled={!canSync}
        style={{
          display: "flex", alignItems: "center", gap: 8,
          padding: "9px 20px", borderRadius: 8, border: "none",
          background: canSync ? "#1e40af" : "#1e293b",
          color: canSync ? "white" : "#475569",
          fontSize: 13, fontWeight: 600,
          cursor: canSync ? "pointer" : "not-allowed",
        }}
      >
        <RefreshCw size={14} />
        {isLoading ? "Starting…" : "Start Sync"}
      </button>
    </div>
  );
}

export default function Dashboard() {
  const qc = useQueryClient();
  const [confirmClear, setConfirmClear] = useState(false);

  const { data: immich } = useQuery({
    queryKey: ["immich-settings"],
    queryFn: getImmichSettings,
    refetchInterval: 30_000,
  });

  const { data: assetCount } = useQuery({
    queryKey: ["asset-count"],
    queryFn: getAssetCount,
  });

  const { data: reviewCount } = useQuery<{ count: number }>({
    queryKey: ["review-count"],
    queryFn: () => getReviewCount(),
    refetchInterval: 10_000,
  });

  const { data: jobs = [] } = useQuery({
    queryKey: ["jobs-recent"],
    queryFn: () => getJobs({ limit: 10 }),
    refetchInterval: 3_000,
  });

  const { data: bucketStats = [] } = useQuery({
    queryKey: ["bucket-stats"],
    queryFn: getBucketStats,
    refetchInterval: 30_000,
  });

  const syncMutation = useMutation({
    mutationFn: (params: { scope: SyncScope; album_ids?: string[] }) => startSyncJob(params),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["jobs-recent"] });
      qc.invalidateQueries({ queryKey: ["asset-count"] });
    },
  });

  const classifyMutation = useMutation({
    mutationFn: () => startClassifyJob(),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["jobs-recent"] }),
  });

  const clearMutation = useMutation({
    mutationFn: clearTerminalJobs,
    onSuccess: () => {
      setConfirmClear(false);
      qc.invalidateQueries({ queryKey: ["jobs-recent"] });
    },
  });

  const activeJob = jobs.find((j) => !["completed", "failed", "cancelled"].includes(j.status));
  const terminalJobs = jobs.filter((j) => ["completed", "failed", "cancelled"].includes(j.status));

  return (
    <div style={{ padding: "32px 40px", maxWidth: 1100 }}>
      <div style={{ marginBottom: 32 }}>
        <h1 style={{ fontSize: 24, fontWeight: 700, color: "#f1f5f9", margin: 0 }}>Dashboard</h1>
        <p style={{ fontSize: 14, color: "#64748b", margin: "4px 0 0" }}>
          AI-first metadata enrichment for Immich
        </p>
      </div>

      {/* Immich status banner */}
      {immich && (
        <div style={{
          display: "flex", alignItems: "center", gap: 10,
          padding: "12px 16px", borderRadius: 10, marginBottom: 24,
          background: immich.connected ? "rgba(34,197,94,0.08)" : "rgba(239,68,68,0.08)",
          border: `1px solid ${immich.connected ? "#16a34a30" : "#dc262630"}`,
        }}>
          {immich.connected ? <CheckCircle size={16} color="#22c55e" /> : <AlertTriangle size={16} color="#ef4444" />}
          <span style={{ fontSize: 13, color: immich.connected ? "#86efac" : "#fca5a5" }}>
            {immich.connected
              ? `Connected to Immich — ${immich.asset_count?.toLocaleString()} total assets`
              : `Immich not connected${immich.error ? `: ${immich.error}` : ""}`}
          </span>
          {!immich.connected && (
            <Link to="/settings" style={{ marginLeft: "auto", fontSize: 12, color: "#38bdf8" }}>
              Configure →
            </Link>
          )}
        </div>
      )}

      {/* Stats */}
      <div style={{ display: "flex", gap: 16, marginBottom: 32, flexWrap: "wrap" }}>
        <StatCard label="Synced Assets" value={assetCount?.count?.toLocaleString() ?? "—"} icon={<Database size={16} color="#38bdf8" />} />
        <StatCard label="Pending Review" value={reviewCount?.count ?? "—"} color={reviewCount?.count ? "#f59e0b" : "#f1f5f9"} icon={<Eye size={16} color="#f59e0b" />} />
        <StatCard label="Classified" value={bucketStats.reduce((s, b) => s + b.total, 0).toLocaleString()} icon={<Database size={16} color="#a78bfa" />} />
      </div>

      {/* Inline sync panel */}
      <SyncPanel
        onSync={(scope, albumIds) => syncMutation.mutate({ scope, album_ids: albumIds })}
        isLoading={syncMutation.isPending}
        disabled={!!activeJob}
      />

      {/* Classify & review shortcuts */}
      <div style={{ display: "flex", gap: 12, marginBottom: 32 }}>
        <button
          onClick={() => classifyMutation.mutate()}
          disabled={classifyMutation.isPending || !!activeJob || !assetCount?.count}
          style={{
            display: "flex", alignItems: "center", gap: 8,
            padding: "10px 20px", borderRadius: 8, border: "none",
            background: "#7c3aed", color: "white", fontSize: 14, fontWeight: 600,
            cursor: (classifyMutation.isPending || !!activeJob || !assetCount?.count) ? "not-allowed" : "pointer",
            opacity: (classifyMutation.isPending || !!activeJob || !assetCount?.count) ? 0.6 : 1,
          }}
        >
          <Play size={15} /> Run AI Classification
        </button>

        {reviewCount?.count ? (
          <Link to="/review" style={{
            display: "flex", alignItems: "center", gap: 8,
            padding: "10px 20px", borderRadius: 8,
            background: "#d97706", color: "white", fontSize: 14, fontWeight: 600, textDecoration: "none",
          }}>
            <Eye size={15} /> Review {reviewCount.count} Suggestion{reviewCount.count !== 1 ? "s" : ""}
          </Link>
        ) : null}
      </div>

      {/* Active job */}
      {activeJob && (
        <div style={{ marginBottom: 24 }}>
          <h2 style={{ fontSize: 14, fontWeight: 600, color: "#94a3b8", marginBottom: 12 }}>Active Job</h2>
          <JobProgressBar job={activeJob} />
        </div>
      )}

      {/* Recent jobs */}
      {jobs.length > 0 && (
        <div style={{ marginBottom: 32 }}>
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 12 }}>
            <h2 style={{ fontSize: 14, fontWeight: 600, color: "#94a3b8", margin: 0 }}>Recent Jobs</h2>
            <div style={{ display: "flex", gap: 10, alignItems: "center" }}>
              {terminalJobs.length > 0 && (
                confirmClear ? (
                  <div style={{ display: "flex", gap: 6, alignItems: "center" }}>
                    <span style={{ fontSize: 12, color: "#94a3b8" }}>Clear {terminalJobs.length} finished job{terminalJobs.length !== 1 ? "s" : ""}?</span>
                    <button
                      onClick={() => clearMutation.mutate()}
                      style={{ padding: "3px 10px", borderRadius: 6, border: "none", background: "#dc2626", color: "white", fontSize: 11, fontWeight: 600, cursor: "pointer" }}
                    >
                      Yes
                    </button>
                    <button
                      onClick={() => setConfirmClear(false)}
                      style={{ padding: "3px 10px", borderRadius: 6, border: "1px solid #334155", background: "transparent", color: "#64748b", fontSize: 11, cursor: "pointer" }}
                    >
                      Cancel
                    </button>
                  </div>
                ) : (
                  <button
                    onClick={() => setConfirmClear(true)}
                    style={{
                      display: "flex", alignItems: "center", gap: 5,
                      padding: "4px 10px", borderRadius: 6,
                      border: "1px solid #334155", background: "transparent",
                      color: "#64748b", fontSize: 12, cursor: "pointer",
                    }}
                  >
                    <Trash2 size={12} /> Clear finished
                  </button>
                )
              )}
              <Link to="/jobs" style={{ fontSize: 12, color: "#38bdf8", textDecoration: "none" }}>
                View all →
              </Link>
            </div>
          </div>
          <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
            {jobs.slice(0, 5).map((job) => (
              <JobProgressBar key={job.id} job={job} compact />
            ))}
          </div>
        </div>
      )}

      {/* Bucket statistics */}
      {bucketStats.length > 0 && (
        <div>
          <h2 style={{ fontSize: 14, fontWeight: 600, color: "#94a3b8", marginBottom: 12 }}>
            Classification by Bucket
          </h2>
          <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
            {[...bucketStats].sort((a, b) => b.total - a.total).map((stat: BucketStat) => {
              const approved = stat.by_status["approved"] || 0;
              const pending = stat.by_status["pending_review"] || 0;
              const rejected = stat.by_status["rejected"] || 0;
              const total = stat.total;
              return (
                <div key={stat.bucket_name} style={{
                  background: "#1e293b", border: "1px solid #334155",
                  borderRadius: 8, padding: "10px 16px",
                  display: "flex", alignItems: "center", gap: 12,
                }}>
                  <span style={{ fontSize: 13, fontWeight: 600, color: "#f1f5f9", width: 120, flexShrink: 0 }}>
                    {stat.bucket_name}
                  </span>
                  <div style={{ flex: 1, height: 8, background: "#0f172a", borderRadius: 4, overflow: "hidden", display: "flex" }}>
                    {approved > 0 && <div style={{ width: `${(approved / total) * 100}%`, background: "#22c55e", transition: "width 0.4s" }} />}
                    {pending > 0 && <div style={{ width: `${(pending / total) * 100}%`, background: "#f59e0b", transition: "width 0.4s" }} />}
                    {rejected > 0 && <div style={{ width: `${(rejected / total) * 100}%`, background: "#475569", transition: "width 0.4s" }} />}
                  </div>
                  <span style={{ fontSize: 12, color: "#64748b", width: 32, textAlign: "right" }}>{total}</span>
                </div>
              );
            })}
          </div>
          <div style={{ display: "flex", gap: 16, marginTop: 8, fontSize: 11, color: "#475569" }}>
            <span style={{ display: "flex", alignItems: "center", gap: 4 }}><span style={{ width: 10, height: 10, background: "#22c55e", borderRadius: 2, display: "inline-block" }} /> Approved</span>
            <span style={{ display: "flex", alignItems: "center", gap: 4 }}><span style={{ width: 10, height: 10, background: "#f59e0b", borderRadius: 2, display: "inline-block" }} /> Pending</span>
            <span style={{ display: "flex", alignItems: "center", gap: 4 }}><span style={{ width: 10, height: 10, background: "#475569", borderRadius: 2, display: "inline-block" }} /> Rejected</span>
          </div>
        </div>
      )}
    </div>
  );
}
