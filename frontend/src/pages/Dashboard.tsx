import React, { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import {
  getImmichSettings,
  getAssetCount,
  getReviewCount,
  getJobs,
  startSyncJob,
  startClassifyJob,
} from "../services/api";
import JobProgressBar from "../components/JobProgressBar";
import SyncOptionsModal from "../components/SyncOptionsModal";
import { Database, Eye, Play, RefreshCw, Zap, AlertTriangle, CheckCircle } from "lucide-react";
import type { SyncScope } from "../types";

function StatCard({ label, value, color = "#f1f5f9", icon }: {
  label: string; value: string | number; color?: string; icon?: React.ReactNode;
}) {
  return (
    <div style={{
      background: "#1e293b",
      border: "1px solid #334155",
      borderRadius: 12,
      padding: "20px 24px",
      flex: 1,
      minWidth: 140,
    }}>
      <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 8 }}>
        {icon}
        <span style={{ fontSize: 12, color: "#64748b", fontWeight: 500 }}>{label}</span>
      </div>
      <div style={{ fontSize: 28, fontWeight: 700, color }}>{value}</div>
    </div>
  );
}

export default function Dashboard() {
  const qc = useQueryClient();
  const [showSyncModal, setShowSyncModal] = useState(false);

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
    queryFn: () => getJobs({ limit: 5 }),
    refetchInterval: 3_000,
  });

  const syncMutation = useMutation({
    mutationFn: (params: { scope: SyncScope; album_ids?: string[] }) =>
      startSyncJob(params),
    onSuccess: () => {
      setShowSyncModal(false);
      qc.invalidateQueries({ queryKey: ["jobs-recent"] });
      qc.invalidateQueries({ queryKey: ["asset-count"] });
    },
  });

  const classifyMutation = useMutation({
    mutationFn: () => startClassifyJob(),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["jobs-recent"] });
    },
  });

  const activeJob = jobs.find((j) =>
    !["completed", "failed", "cancelled"].includes(j.status)
  );

  const handleSyncConfirm = (scope: SyncScope, albumIds?: string[]) => {
    syncMutation.mutate({ scope, album_ids: albumIds });
  };

  return (
    <div style={{ padding: "32px 40px", maxWidth: 1100 }}>
      <div style={{ marginBottom: 32 }}>
        <h1 style={{ fontSize: 24, fontWeight: 700, color: "#f1f5f9", margin: 0 }}>
          Dashboard
        </h1>
        <p style={{ fontSize: 14, color: "#64748b", margin: "4px 0 0" }}>
          AI-first metadata enrichment for Immich
        </p>
      </div>

      {/* Immich status banner */}
      {immich && (
        <div style={{
          display: "flex",
          alignItems: "center",
          gap: 10,
          padding: "12px 16px",
          borderRadius: 10,
          marginBottom: 24,
          background: immich.connected ? "rgba(34,197,94,0.08)" : "rgba(239,68,68,0.08)",
          border: `1px solid ${immich.connected ? "#16a34a30" : "#dc262630"}`,
        }}>
          {immich.connected
            ? <CheckCircle size={16} color="#22c55e" />
            : <AlertTriangle size={16} color="#ef4444" />}
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
        <StatCard
          label="Synced Assets"
          value={assetCount?.count?.toLocaleString() ?? "—"}
          icon={<Database size={16} color="#38bdf8" />}
        />
        <StatCard
          label="Pending Review"
          value={reviewCount?.count ?? "—"}
          color={reviewCount?.count ? "#f59e0b" : "#f1f5f9"}
          icon={<Eye size={16} color="#f59e0b" />}
        />
        <StatCard
          label="Provider"
          value="OpenAI"
          icon={<Zap size={16} color="#a78bfa" />}
        />
      </div>

      {/* Action buttons */}
      <div style={{ display: "flex", gap: 12, marginBottom: 32 }}>
        <button
          onClick={() => setShowSyncModal(true)}
          disabled={syncMutation.isPending || !!activeJob}
          style={{
            display: "flex",
            alignItems: "center",
            gap: 8,
            padding: "10px 20px",
            borderRadius: 8,
            border: "none",
            background: "#1e40af",
            color: "white",
            fontSize: 14,
            fontWeight: 600,
            cursor: syncMutation.isPending || !!activeJob ? "not-allowed" : "pointer",
            opacity: syncMutation.isPending || !!activeJob ? 0.6 : 1,
          }}
        >
          <RefreshCw size={15} />
          Sync Assets
        </button>

        <button
          onClick={() => classifyMutation.mutate()}
          disabled={classifyMutation.isPending || !!activeJob || !assetCount?.count}
          style={{
            display: "flex",
            alignItems: "center",
            gap: 8,
            padding: "10px 20px",
            borderRadius: 8,
            border: "none",
            background: "#7c3aed",
            color: "white",
            fontSize: 14,
            fontWeight: 600,
            cursor: (classifyMutation.isPending || !!activeJob || !assetCount?.count) ? "not-allowed" : "pointer",
            opacity: (classifyMutation.isPending || !!activeJob || !assetCount?.count) ? 0.6 : 1,
          }}
        >
          <Play size={15} />
          Run AI Classification
        </button>

        {reviewCount?.count ? (
          <Link
            to="/review"
            style={{
              display: "flex",
              alignItems: "center",
              gap: 8,
              padding: "10px 20px",
              borderRadius: 8,
              background: "#d97706",
              color: "white",
              fontSize: 14,
              fontWeight: 600,
              textDecoration: "none",
            }}
          >
            <Eye size={15} />
            Review {reviewCount.count} Suggestion{reviewCount.count !== 1 ? "s" : ""}
          </Link>
        ) : null}
      </div>

      {/* Active job */}
      {activeJob && (
        <div style={{ marginBottom: 24 }}>
          <h2 style={{ fontSize: 14, fontWeight: 600, color: "#94a3b8", marginBottom: 12 }}>
            Active Job
          </h2>
          <JobProgressBar job={activeJob} />
        </div>
      )}

      {/* Recent jobs */}
      {jobs.length > 0 && (
        <div>
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 12 }}>
            <h2 style={{ fontSize: 14, fontWeight: 600, color: "#94a3b8", margin: 0 }}>
              Recent Jobs
            </h2>
            <Link to="/jobs" style={{ fontSize: 12, color: "#38bdf8", textDecoration: "none" }}>
              View all →
            </Link>
          </div>
          <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
            {jobs.slice(0, 3).map((job) => (
              <JobProgressBar key={job.id} job={job} compact />
            ))}
          </div>
        </div>
      )}

      {showSyncModal && (
        <SyncOptionsModal
          onClose={() => setShowSyncModal(false)}
          onConfirm={handleSyncConfirm}
          isLoading={syncMutation.isPending}
        />
      )}
    </div>
  );
}
