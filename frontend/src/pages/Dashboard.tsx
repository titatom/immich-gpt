import React, { useState, useRef } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import {
  getImmichSettings, getAssetCount, getReviewCount, getJobs,
  getBucketStats, getAlbums, startSyncJob, startClassifyJob, clearTerminalJobs, getBuckets,
} from "../services/api";
import type { BucketStat, SyncScope, ImmichAlbum, Bucket } from "../types";
import JobProgressBar from "../components/JobProgressBar";
import JobDetail from "../components/JobDetail";
import {
  Database, Eye, Play, RefreshCw, AlertTriangle, CheckCircle,
  Star, FolderOpen, ChevronDown, ChevronUp, Trash2, Layers,
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

type WorkflowMode = "sync" | "sync_ai" | "ai";

function SyncPanel({ onSync, onClassify, isSyncLoading, isClassifyLoading, disabled }: {
  onSync: (scope: SyncScope, albumIds: string[] | undefined, runAI: boolean) => void;
  onClassify: () => void;
  isSyncLoading: boolean;
  isClassifyLoading: boolean;
  disabled: boolean;
}) {
  const [scope, setScope] = useState<SyncScope>("all");
  const [selectedAlbumIds, setSelectedAlbumIds] = useState<Set<string>>(new Set());
  const [albumsExpanded, setAlbumsExpanded] = useState(false);
  const [albumSearch, setAlbumSearch] = useState("");
  const [workflowMode, setWorkflowMode] = useState<WorkflowMode>("sync_ai");

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

  const scopeValid = scope !== "albums" || selectedAlbumIds.size > 0;
  const isLoading = isSyncLoading || isClassifyLoading;
  const canRun = !disabled && !isLoading && (workflowMode === "ai" || scopeValid);

  const WORKFLOW_OPTIONS: { value: WorkflowMode; label: string; desc: string; icon: React.ReactNode }[] = [
    {
      value: "sync",
      label: "Sync Only",
      desc: "Pull new assets from Immich into immich-gpt. No AI processing.",
      icon: <RefreshCw size={14} />,
    },
    {
      value: "sync_ai",
      label: "Sync + AI",
      desc: "Pull new assets from Immich, then immediately run AI classification on all unclassified assets.",
      icon: <Layers size={14} />,
    },
    {
      value: "ai",
      label: "AI Only",
      desc: "Run AI classification on assets already synced. No new assets are pulled from Immich.",
      icon: <Play size={14} />,
    },
  ];

  function handleRun() {
    if (workflowMode === "ai") {
      onClassify();
    } else {
      onSync(
        scope,
        scope === "albums" ? Array.from(selectedAlbumIds) : undefined,
        workflowMode === "sync_ai",
      );
    }
  }

  const showScopeSelector = workflowMode !== "ai";

  return (
    <div className={styles.syncPanel}>
      <div className={styles.syncPanelLabel}>Run Workflow</div>

      {/* Workflow mode selector */}
      <div className={styles.scopeRow} style={{ marginBottom: 10 }}>
        {WORKFLOW_OPTIONS.map((opt) => (
          <button
            key={opt.value}
            onClick={() => setWorkflowMode(opt.value)}
            className={[styles.scopeBtn, workflowMode === opt.value ? styles.scopeBtnActive : styles.scopeBtnInactive].join(" ")}
          >
            {opt.icon} {opt.label}
          </button>
        ))}
      </div>

      <div className={styles.scopeDesc}>
        {WORKFLOW_OPTIONS.find((o) => o.value === workflowMode)?.desc}
      </div>

      {/* Scope selector — only shown when sync is involved */}
      {showScopeSelector && (
        <>
          <div style={{ fontSize: "var(--text-xs)", color: "var(--text-muted)", fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.05em", marginBottom: 8 }}>
            What to sync
          </div>
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
        </>
      )}

      <button
        onClick={handleRun}
        disabled={!canRun}
        className={[styles.scopeBtn, canRun ? styles.scopeBtnActive : styles.scopeBtnInactive].join(" ")}
        style={{
          padding: "9px 20px",
          marginTop: 4,
          background: canRun ? (workflowMode === "ai" ? "var(--color-purple)" : undefined) : undefined,
        }}
      >
        {workflowMode === "sync" && <RefreshCw size={14} />}
        {workflowMode === "sync_ai" && <Layers size={14} />}
        {workflowMode === "ai" && <Play size={14} />}
        {isLoading ? "Starting…" : (
          workflowMode === "sync" ? "Start Sync" :
          workflowMode === "sync_ai" ? "Sync + Classify" :
          "Run AI Classification"
        )}
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

  const { data: buckets = [] } = useQuery<Bucket[]>({
    queryKey: ["buckets"],
    queryFn: getBuckets,
    refetchInterval: 60_000,
  });

  const runAIAfterSyncRef = useRef(false);

  const classifyMutation = useMutation({
    mutationFn: () => startClassifyJob(),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["jobs"] }),
  });

  const syncMutation = useMutation({
    mutationFn: (params: { scope: SyncScope; album_ids?: string[] }) => startSyncJob(params),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["jobs"] });
      qc.invalidateQueries({ queryKey: ["asset-count"] });
      if (runAIAfterSyncRef.current) {
        runAIAfterSyncRef.current = false;
        classifyMutation.mutate();
      }
    },
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
        <StatCard label="Classified" value={bucketStats.reduce((s, b) => s + b.total, 0).toLocaleString()} icon={<Layers size={16} color="#a78bfa" />} />
        <StatCard label="Pending Review" value={reviewCount?.count ?? "—"} color={reviewCount?.count ? "var(--color-warning)" : "var(--text-primary)"} icon={<Eye size={16} color="var(--color-warning)" />} />
      </div>

      <SyncPanel
        onSync={(scope, albumIds, runAI) => {
          runAIAfterSyncRef.current = runAI;
          syncMutation.mutate({ scope, album_ids: albumIds });
        }}
        onClassify={() => classifyMutation.mutate()}
        isSyncLoading={syncMutation.isPending}
        isClassifyLoading={classifyMutation.isPending}
        disabled={!!activeJob}
      />

      {reviewCount?.count ? (
        <div className={styles.actionsRow}>
          <Link to="/review" style={{
            display: "flex", alignItems: "center", gap: 8,
            padding: "10px 20px", borderRadius: "var(--radius-md)",
            background: "#d97706", color: "white", fontSize: "var(--text-md)", fontWeight: 600, textDecoration: "none",
          }}>
            <Eye size={15} /> Review {reviewCount.count} Suggestion{reviewCount.count !== 1 ? "s" : ""}
          </Link>
        </div>
      ) : null}

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

      {(bucketStats.length > 0 || buckets.length > 0) && (
        <div>
          <h2 className={styles.sectionTitle} style={{ marginBottom: 12 }}>Classification by Bucket</h2>
          <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
            {(() => {
              // Merge bucket stats with all configured buckets so every bucket appears,
              // including trash and buckets with 0 classifications.
              const statsMap = new Map(bucketStats.map((s) => [s.bucket_name, s]));
              const allEntries: BucketStat[] = [...bucketStats];
              for (const b of buckets) {
                if (!statsMap.has(b.name)) {
                  allEntries.push({ bucket_name: b.name, bucket_id: b.id, total: 0, by_status: {} });
                }
              }
              return [...allEntries].sort((a, b) => b.total - a.total).map((stat: BucketStat) => {
                const approved = stat.by_status["approved"] ?? 0;
                const pending  = stat.by_status["pending_review"] ?? 0;
                const rejected = stat.by_status["rejected"] ?? 0;
                const total    = stat.total;
                const bucket   = buckets.find((b) => b.name === stat.bucket_name || b.id === stat.bucket_id);
                const isTrash  = bucket?.mapping_mode === "immich_trash";
                return (
                  <div key={stat.bucket_name} className={styles.bucketStatRow}>
                    <span className={styles.bucketStatName} style={{ display: "flex", alignItems: "center", gap: 5 }}>
                      {isTrash && <Trash2 size={12} color="var(--text-muted)" />}
                      {stat.bucket_name}
                    </span>
                    <div className={styles.bucketStatTrack}>
                      {total === 0 && <div style={{ width: "100%", background: "var(--bg-raised)", opacity: 0.4 }} />}
                      {approved > 0 && <div style={{ width: `${(approved/total)*100}%`, background: "var(--color-success)", transition: "width 0.4s" }} />}
                      {pending  > 0 && <div style={{ width: `${(pending/total)*100}%`,  background: "var(--color-warning)", transition: "width 0.4s" }} />}
                      {rejected > 0 && <div style={{ width: `${(rejected/total)*100}%`, background: "var(--text-faint)",   transition: "width 0.4s" }} />}
                    </div>
                    <span className={styles.bucketStatTotal}>{total}</span>
                  </div>
                );
              });
            })()}
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
