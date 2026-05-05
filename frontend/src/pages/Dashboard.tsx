import React, { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import {
  getImmichSettings, getAssetCount, getJobs,
  getAlbums, startSyncJob, startRoutingClassify, clearTerminalJobs,
  listRoutingPlans, listRoutingNodes,
} from "../services/api";
import type {
  SyncScope, ImmichAlbum, RoutingNode, RoutingPlan,
} from "../types";
import JobProgressBar from "../components/JobProgressBar";
import JobDetail from "../components/JobDetail";
import {
  Database, Play, RefreshCw, AlertTriangle, CheckCircle,
  Star, FolderOpen, ChevronDown, ChevronUp, Trash2, Layers,
  Network, GitBranch,
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

type WorkflowMode = "sync" | "sync_route" | "route";

function WorkflowPanel({
  onSync, onRoute, isLoading, disabled,
}: {
  onSync: (scope: SyncScope, albumIds: string[] | undefined, runRoutingAfter: boolean) => void;
  onRoute: () => void;
  isLoading: boolean;
  disabled: boolean;
}) {
  const [scope, setScope] = useState<SyncScope>("all");
  const [selectedAlbumIds, setSelectedAlbumIds] = useState<Set<string>>(new Set());
  const [albumsExpanded, setAlbumsExpanded] = useState(false);
  const [albumSearch, setAlbumSearch] = useState("");
  const [workflowMode, setWorkflowMode] = useState<WorkflowMode>("sync_route");

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
  const canRun = !disabled && !isLoading && (workflowMode === "route" || scopeValid);

  const WORKFLOW_OPTIONS: { value: WorkflowMode; label: string; desc: string; icon: React.ReactNode }[] = [
    {
      value: "sync",
      label: "Sync Only",
      desc: "Pull new assets from Immich into immich-gpt. No routing.",
      icon: <RefreshCw size={14} />,
    },
    {
      value: "sync_route",
      label: "Sync + Route",
      desc: "Pull new assets, then immediately classify them through your routing tree.",
      icon: <Layers size={14} />,
    },
    {
      value: "route",
      label: "Route Only",
      desc: "Run routing classification on assets already synced. No new assets are pulled from Immich.",
      icon: <Play size={14} />,
    },
  ];

  function handleRun() {
    if (workflowMode === "route") {
      onRoute();
    } else {
      onSync(
        scope,
        scope === "albums" ? Array.from(selectedAlbumIds) : undefined,
        workflowMode === "sync_route",
      );
    }
  }

  const showScopeSelector = workflowMode !== "route";

  return (
    <div className={styles.syncPanel}>
      <div className={styles.syncPanelLabel}>Run Workflow</div>

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
          background: canRun ? (workflowMode === "route" ? "var(--color-purple)" : undefined) : undefined,
        }}
      >
        {workflowMode === "sync" && <RefreshCw size={14} />}
        {workflowMode === "sync_route" && <Layers size={14} />}
        {workflowMode === "route" && <Play size={14} />}
        {isLoading ? "Starting…" : (
          workflowMode === "sync" ? "Start Sync" :
          workflowMode === "sync_route" ? "Sync + Route" :
          "Run Routing"
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

  const { data: jobs = [] } = useQuery({
    queryKey: ["jobs", { limit: 10 }],
    queryFn: () => getJobs({ limit: 10 }),
    refetchInterval: 3_000,
  });

  const { data: nodes = [] } = useQuery<RoutingNode[]>({
    queryKey: ["routing-nodes-flat"],
    queryFn: listRoutingNodes,
    refetchInterval: 60_000,
  });

  const { data: plans = [] } = useQuery<RoutingPlan[]>({
    queryKey: ["routing-plans"],
    queryFn: () => listRoutingPlans(),
    refetchInterval: 15_000,
  });

  const enabledLeaves = nodes.filter((n) => n.is_leaf && n.enabled);
  const pendingPlans = plans.filter((p) => p.status === "ready" || p.status === "draft");
  const pendingItems = pendingPlans.reduce((s, p) => s + p.item_count, 0);

  const routeMutation = useMutation({
    mutationFn: () => startRoutingClassify({}),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["jobs"] });
      qc.invalidateQueries({ queryKey: ["routing-plans"] });
    },
  });

  const syncMutation = useMutation({
    mutationFn: (params: { scope: SyncScope; album_ids?: string[]; runRoutingAfter: boolean }) =>
      startSyncJob({ scope: params.scope, album_ids: params.album_ids }).then(
        (job) => {
          if (params.runRoutingAfter) {
            routeMutation.mutate();
          }
          return job;
        }
      ),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["jobs"] });
      qc.invalidateQueries({ queryKey: ["asset-count"] });
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
          AI-first photo routing for Immich
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
        <StatCard
          label="Synced Assets"
          value={assetCount?.count?.toLocaleString() ?? "—"}
          icon={<Database size={16} color="var(--accent)" />}
        />
        <StatCard
          label="Routing Leaves"
          value={enabledLeaves.length}
          icon={<Network size={16} color="#a78bfa" />}
        />
        <StatCard
          label="Pending Plan Items"
          value={pendingItems}
          color={pendingItems ? "var(--color-warning)" : "var(--text-primary)"}
          icon={<GitBranch size={16} color="var(--color-warning)" />}
        />
      </div>

      <WorkflowPanel
        onSync={(scope, albumIds, runRoutingAfter) =>
          syncMutation.mutate({ scope, album_ids: albumIds, runRoutingAfter })
        }
        onRoute={() => routeMutation.mutate()}
        isLoading={syncMutation.isPending || routeMutation.isPending}
        disabled={!!activeJob}
      />

      {pendingItems > 0 && (
        <div className={styles.actionsRow}>
          <Link to="/routing/plans" style={{
            display: "flex", alignItems: "center", gap: 8,
            padding: "10px 20px", borderRadius: "var(--radius-md)",
            background: "#d97706", color: "white", fontSize: "var(--text-md)", fontWeight: 600, textDecoration: "none",
          }}>
            <GitBranch size={15} /> Review {pendingItems} pending item{pendingItems !== 1 ? "s" : ""}
          </Link>
        </div>
      )}

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
    </div>
  );
}
