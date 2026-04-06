import React, { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import {
  getImmichSettings, getAssetCount, getReviewCount, getJobs,
  getBucketStats, getAlbums, startSyncJob, startClassifyJob, clearTerminalJobs,
} from "../services/api";
import type { BucketStat, SyncScope, ImmichAlbum } from "../types";
import JobProgressBar from "../components/JobProgressBar";
import JobDetail from "../components/JobDetail";
import {
  Database, Eye, Play, RefreshCw, AlertTriangle, CheckCircle,
  Star, FolderOpen, ChevronDown, ChevronUp, Trash2,
} from "lucide-react";
import styles from "./Dashboard.module.css";

function StatCard({ label, value, color = "var(--text-primary)", icon }: {
  label: string; value: string | number; color?: string; icon?: React.ReactNode;
}) {
  return (
    <div className={styles.statCard}>
      <div className={styles.statCardHeader}>
        {icon}
        <span className={styles.statLabel}>{label}</span>
      </div>
      <div className={styles.statValue} style={{ color }}>{value}</div>
    </div>
  );
}

const SCOPE_OPTIONS: { value: SyncScope; label: string; desc: string; icon: React.ReactNode }[] = [
  { value: "all",       label: "All Photos & Videos", desc: "Every asset in your Immich library",        icon: <RefreshCw size={14} /> },
  { value: "favorites", label: "Favourites Only",      desc: "Assets you have marked as favourite",      icon: <Star size={14} /> },
  { value: "albums",    label: "Specific Albums",      desc: "Choose one or more albums",                icon: <FolderOpen size={14} /> },
];

function SyncPanel({ onSync, isLoading, disabled }: {
  onSync: (scope: SyncScope, albumIds?: string[]) => void;
  isLoading: boolean;
  disabled: boolean;
}) {
  const [scope, setScope] = useState<SyncScope>("all");
  const [selectedAlbumIds, setSelectedAlbumIds] = useState<Set<string>>(new Set());
  const [albumsExpanded, setAlbumsExpanded] = useState(false);
  const [albumSearch, setAlbumSearch] = useState("");

  const { data: albums = [] } = useQuery<ImmichAlbum[]>({
    queryKey: ["albums"],
    queryFn: getAlbums,
    enabled: scope === "albums",
  });

  const filtered = albums.filter((a) => a.albumName.toLowerCase().includes(albumSearch.toLowerCase()));

  const toggle = (id: string) => setSelectedAlbumIds((prev) => {
    const next = new Set(prev);
    if (next.has(id)) { next.delete(id); } else { next.add(id); }
    return next;
  });

  const canSync = !disabled && !isLoading && (scope !== "albums" || selectedAlbumIds.size > 0);

  return (
    <div className={styles.syncPanel}>
      <div className={styles.syncPanelLabel}>Sync Assets</div>

      <div className={styles.scopeRow}>
        {SCOPE_OPTIONS.map((opt) => (
          <button
            key={opt.value}
            onClick={() => { setScope(opt.value); if (opt.value !== "albums") setSelectedAlbumIds(new Set()); }}
            className={[styles.scopeBtn, scope === opt.value ? styles.scopeBtnActive : styles.scopeBtnInactive].join(" ")}
          >
            {opt.icon} {opt.label}
          </button>
        ))}
      </div>

      <div className={styles.scopeDesc}>
        {SCOPE_OPTIONS.find((o) => o.value === scope)?.desc}
      </div>

      {scope === "albums" && (
        <div style={{ marginBottom: 14 }}>
          <div className={styles.albumPickerHeader} onClick={() => setAlbumsExpanded((v) => !v)}>
            <span className={styles.albumPickerHeaderText}>
              Albums
              {selectedAlbumIds.size > 0 && (
                <span className={styles.albumBadge}>{selectedAlbumIds.size} selected</span>
              )}
            </span>
            {albumsExpanded ? <ChevronUp size={13} color="var(--text-muted)" /> : <ChevronDown size={13} color="var(--text-muted)" />}
          </div>

          {albumsExpanded && (
            <div className={styles.albumList}>
              <div className={styles.albumSearch}>
                <input
                  type="text"
                  placeholder="Search albums…"
                  value={albumSearch}
                  onChange={(e) => setAlbumSearch(e.target.value)}
                  className={styles.albumSearchInput}
                />
              </div>
              <div className={styles.albumScroll}>
                {filtered.length === 0 ? (
                  <div className={styles.albumEmpty}>
                    {albums.length === 0 ? "No albums found" : "No matches"}
                  </div>
                ) : filtered.map((a) => {
                  const sel = selectedAlbumIds.has(a.id);
                  return (
                    <div
                      key={a.id}
                      onClick={() => toggle(a.id)}
                      className={[styles.albumRow, sel ? styles.albumRowSelected : ""].join(" ")}
                    >
                      <div className={[styles.albumCheckbox, sel ? styles.albumCheckboxSelected : ""].join(" ")}>
                        {sel && <svg width="8" height="6" viewBox="0 0 8 6" fill="none"><path d="M1 3L3 5L7 1" stroke="white" strokeWidth="1.5" strokeLinecap="round" /></svg>}
                      </div>
                      <span className={styles.albumName}>{a.albumName}</span>
                      <span className={styles.albumCount}>{a.assetCount.toLocaleString()}</span>
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
        className={[styles.scopeBtn, canSync ? styles.scopeBtnActive : styles.scopeBtnInactive].join(" ")}
        style={{ padding: "9px 20px" }}
      >
        <RefreshCw size={14} />
        {isLoading ? "Starting…" : "Start Sync"}
      </button>
    </div>
  );
}

const TERMINAL_STATUSES = new Set(["completed", "failed", "cancelled"]);

export default function Dashboard() {
  const qc = useQueryClient();
  const [confirmClear, setConfirmClear] = useState(false);
  const [expandedJobId, setExpandedJobId] = useState<string | null>(null);

  const { data: immich } = useQuery({
    queryKey: ["immich-settings"],
    queryFn: getImmichSettings,
    refetchInterval: 30_000,
  });

  const { data: assetCount } = useQuery<{ count: number }>({
    queryKey: ["asset-count"],
    queryFn: () => getAssetCount(),
  });

  const { data: reviewCount } = useQuery<{ count: number }>({
    queryKey: ["review-count"],
    queryFn: () => getReviewCount(),
    refetchInterval: 10_000,
  });

  const { data: jobs = [] } = useQuery({
    queryKey: ["jobs", { limit: 10 }],
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
      qc.invalidateQueries({ queryKey: ["jobs"] });
      qc.invalidateQueries({ queryKey: ["asset-count"] });
    },
  });

  const classifyMutation = useMutation({
    mutationFn: () => startClassifyJob(),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["jobs"] }),
  });

  const clearMutation = useMutation({
    mutationFn: clearTerminalJobs,
    onSuccess: () => {
      setConfirmClear(false);
      qc.invalidateQueries({ queryKey: ["jobs"] });
    },
  });

  const activeJob = jobs.find((j) => !TERMINAL_STATUSES.has(j.status) && j.status !== "paused");
  const terminalJobs = jobs.filter((j) => TERMINAL_STATUSES.has(j.status));

  const classifyDisabled = classifyMutation.isPending || !!activeJob || !assetCount?.count;

  return (
    <div className={styles.page}>
      <div className="pageHeader" style={{ marginBottom: 32 }}>
        <h1 style={{ fontSize: "var(--text-2xl)", fontWeight: 700, color: "var(--text-primary)", margin: 0 }}>Dashboard</h1>
        <p style={{ fontSize: "var(--text-md)", color: "var(--text-muted)", margin: "4px 0 0" }}>
          AI-first metadata enrichment for Immich
        </p>
      </div>

      {immich && (
        <div className={[styles.statusBanner, immich.connected ? styles.statusBannerOk : styles.statusBannerErr].join(" ")}>
          {immich.connected
            ? <CheckCircle size={16} color="var(--color-success)" />
            : <AlertTriangle size={16} color="var(--color-error)" />}
          <span>
            {immich.connected
              ? `Connected to Immich — ${immich.asset_count?.toLocaleString()} total assets`
              : `Immich not connected${immich.error ? `: ${immich.error}` : ""}`}
          </span>
          {!immich.connected && (
            <Link to="/settings" className={styles.statusBannerLink}>Configure →</Link>
          )}
        </div>
      )}

      <div className={styles.statsRow}>
        <StatCard label="Synced Assets" value={assetCount?.count?.toLocaleString() ?? "—"} icon={<Database size={16} color="var(--accent)" />} />
        <StatCard label="Pending Review" value={reviewCount?.count ?? "—"} color={reviewCount?.count ? "var(--color-warning)" : "var(--text-primary)"} icon={<Eye size={16} color="var(--color-warning)" />} />
        <StatCard label="Classified" value={bucketStats.reduce((s, b) => s + b.total, 0).toLocaleString()} icon={<Database size={16} color="#a78bfa" />} />
      </div>

      <SyncPanel
        onSync={(scope, albumIds) => syncMutation.mutate({ scope, album_ids: albumIds })}
        isLoading={syncMutation.isPending}
        disabled={!!activeJob}
      />

      <div className={styles.actionsRow}>
        <button
          onClick={() => classifyMutation.mutate()}
          disabled={classifyDisabled}
          className={[styles.scopeBtn, !classifyDisabled ? styles.scopeBtnActive : styles.scopeBtnInactive].join(" ")}
          style={{ background: !classifyDisabled ? "var(--color-purple)" : undefined, padding: "10px 20px", fontSize: "var(--text-md)" }}
        >
          <Play size={15} /> Run AI Classification
        </button>

        {reviewCount?.count ? (
          <Link to="/review" style={{
            display: "flex", alignItems: "center", gap: 8,
            padding: "10px 20px", borderRadius: "var(--radius-md)",
            background: "#d97706", color: "white", fontSize: "var(--text-md)", fontWeight: 600, textDecoration: "none",
          }}>
            <Eye size={15} /> Review {reviewCount.count} Suggestion{reviewCount.count !== 1 ? "s" : ""}
          </Link>
        ) : null}
      </div>

      {activeJob && (
        <div className={styles.section}>
          <h2 className={styles.sectionTitle}>Active Job</h2>
          <div className={styles.jobCard}>
            <div
              className={styles.jobCardHeader}
              onClick={() => setExpandedJobId(expandedJobId === activeJob.id ? null : activeJob.id)}
            >
              <div style={{ flex: 1 }}><JobProgressBar job={activeJob} compact /></div>
              {expandedJobId === activeJob.id ? <ChevronUp size={14} color="var(--text-muted)" /> : <ChevronDown size={14} color="var(--text-muted)" />}
            </div>
            {expandedJobId === activeJob.id && (
              <div className={styles.jobCardDetail}><JobDetail jobId={activeJob.id} /></div>
            )}
          </div>
        </div>
      )}

      {jobs.length > 0 && (
        <div className={styles.section}>
          <div className={styles.sectionHeader}>
            <h2 className={styles.sectionTitle} style={{ margin: 0 }}>Recent Jobs</h2>
            <div style={{ display: "flex", gap: 10, alignItems: "center" }}>
              {terminalJobs.length > 0 && (
                confirmClear ? (
                  <div className={styles.clearRow}>
                    <span className={styles.clearConfirmText}>
                      Clear {terminalJobs.length} finished job{terminalJobs.length !== 1 ? "s" : ""}?
                    </span>
                    <button
                      onClick={() => clearMutation.mutate()}
                      style={{ padding: "3px 10px", borderRadius: 6, border: "none", background: "#dc2626", color: "white", fontSize: "var(--text-xs)", fontWeight: 600, cursor: "pointer" }}
                    >Yes</button>
                    <button
                      onClick={() => setConfirmClear(false)}
                      style={{ padding: "3px 10px", borderRadius: 6, border: "1px solid var(--border)", background: "transparent", color: "var(--text-muted)", fontSize: "var(--text-xs)", cursor: "pointer" }}
                    >Cancel</button>
                  </div>
                ) : (
                  <button
                    onClick={() => setConfirmClear(true)}
                    style={{ display: "flex", alignItems: "center", gap: 5, padding: "4px 10px", borderRadius: 6, border: "1px solid var(--border)", background: "transparent", color: "var(--text-muted)", fontSize: "var(--text-sm)", cursor: "pointer" }}
                  >
                    <Trash2 size={12} /> Clear finished
                  </button>
                )
              )}
              <Link to="/jobs" className={styles.sectionLink}>View all →</Link>
            </div>
          </div>
          <div className={styles.jobList}>
            {jobs.slice(0, 5).map((job) => (
              <div key={job.id} className={styles.jobCard}>
                <div
                  className={styles.jobCardHeader}
                  onClick={() => setExpandedJobId(expandedJobId === job.id ? null : job.id)}
                >
                  <div style={{ flex: 1 }}><JobProgressBar job={job} compact /></div>
                  {expandedJobId === job.id ? <ChevronUp size={14} color="var(--text-muted)" /> : <ChevronDown size={14} color="var(--text-muted)" />}
                </div>
                {expandedJobId === job.id && (
                  <div className={styles.jobCardDetail}><JobDetail jobId={job.id} /></div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {bucketStats.length > 0 && (
        <div>
          <h2 className={styles.sectionTitle} style={{ marginBottom: 12 }}>Classification by Bucket</h2>
          <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
            {[...bucketStats].sort((a, b) => b.total - a.total).map((stat: BucketStat) => {
              const approved = stat.by_status["approved"] ?? 0;
              const pending  = stat.by_status["pending_review"] ?? 0;
              const rejected = stat.by_status["rejected"] ?? 0;
              const total    = stat.total;
              return (
                <div key={stat.bucket_name} className={styles.bucketStatRow}>
                  <span className={styles.bucketStatName}>{stat.bucket_name}</span>
                  <div className={styles.bucketStatTrack}>
                    {approved > 0 && <div style={{ width: `${(approved/total)*100}%`, background: "var(--color-success)", transition: "width 0.4s" }} />}
                    {pending  > 0 && <div style={{ width: `${(pending/total)*100}%`,  background: "var(--color-warning)", transition: "width 0.4s" }} />}
                    {rejected > 0 && <div style={{ width: `${(rejected/total)*100}%`, background: "var(--text-faint)",   transition: "width 0.4s" }} />}
                  </div>
                  <span className={styles.bucketStatTotal}>{total}</span>
                </div>
              );
            })}
          </div>
          <div className={styles.legend}>
            <span><span className={styles.legendDot} style={{ background: "var(--color-success)" }} /> Approved</span>
            <span><span className={styles.legendDot} style={{ background: "var(--color-warning)" }} /> Pending</span>
            <span><span className={styles.legendDot} style={{ background: "var(--text-faint)" }} /> Rejected</span>
          </div>
        </div>
      )}
    </div>
  );
}
