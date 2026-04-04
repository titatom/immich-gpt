import React from "react";
import { useQuery } from "@tanstack/react-query";
import { useSearchParams } from "react-router-dom";
import { getAuditLogs, getAuditLogCount } from "../services/api";
import type { AuditLog } from "../types";
import { CheckCircle, XCircle, Clock } from "lucide-react";

const PAGE_SIZE = 50;

function StatusIcon({ status }: { status?: string }) {
  if (status === "success") return <CheckCircle size={14} color="#22c55e" />;
  if (status === "failed") return <XCircle size={14} color="#ef4444" />;
  return <Clock size={14} color="#64748b" />;
}

function actionColor(action: string) {
  if (action.includes("description")) return "#38bdf8";
  if (action.includes("tag")) return "#a78bfa";
  if (action.includes("album")) return "#34d399";
  if (action.includes("error")) return "#ef4444";
  return "#94a3b8";
}

export default function Logs() {
  const [searchParams, setSearchParams] = useSearchParams();

  const page = parseInt(searchParams.get("page") || "1", 10);
  const statusFilter = searchParams.get("status") || "";
  const actionFilter = searchParams.get("action") || "";
  const jobId = searchParams.get("job_run_id") || "";

  function setParam(key: string, value: string) {
    setSearchParams((prev) => {
      const next = new URLSearchParams(prev);
      if (value) next.set(key, value);
      else next.delete(key);
      if (key !== "page") next.set("page", "1");
      return next;
    });
  }

  const params = {
    page,
    page_size: PAGE_SIZE,
    status: statusFilter || undefined,
    action: actionFilter || undefined,
    job_run_id: jobId || undefined,
  };

  const { data: logs = [], isLoading } = useQuery({
    queryKey: ["audit-logs", params],
    queryFn: () => getAuditLogs(params),
  });

  const { data: countData } = useQuery({
    queryKey: ["audit-log-count", statusFilter, jobId],
    queryFn: () => getAuditLogCount({
      status: statusFilter || undefined,
      job_run_id: jobId || undefined,
    }),
  });

  const totalPages = countData ? Math.ceil(countData.count / PAGE_SIZE) : 1;

  return (
    <div style={{ padding: "32px 40px", maxWidth: 1100 }}>
      <div style={{ marginBottom: 24 }}>
        <h1 style={{ fontSize: 24, fontWeight: 700, color: "#f1f5f9", margin: 0 }}>Audit Logs</h1>
        <p style={{ fontSize: 14, color: "#64748b", margin: "4px 0 0" }}>
          {countData ? `${countData.count.toLocaleString()} entries` : "Write-back actions and classification events"}
        </p>
      </div>

      {/* Filters */}
      <div style={{ display: "flex", gap: 10, marginBottom: 20, flexWrap: "wrap" }}>
        <select
          value={statusFilter}
          onChange={(e) => setParam("status", e.target.value)}
          style={{ background: "#1e293b", border: "1px solid #334155", color: "#94a3b8", borderRadius: 8, padding: "7px 12px", fontSize: 13 }}
        >
          <option value="">All statuses</option>
          <option value="success">Success</option>
          <option value="failed">Failed</option>
        </select>
        <select
          value={actionFilter}
          onChange={(e) => setParam("action", e.target.value)}
          style={{ background: "#1e293b", border: "1px solid #334155", color: "#94a3b8", borderRadius: 8, padding: "7px 12px", fontSize: 13 }}
        >
          <option value="">All actions</option>
          <option value="writeback_description">Write description</option>
          <option value="writeback_tags">Write tags</option>
          <option value="writeback_album">Write album</option>
          <option value="classification_error">Classification error</option>
        </select>
        {jobId && (
          <button
            onClick={() => setParam("job_run_id", "")}
            style={{ padding: "7px 12px", borderRadius: 8, border: "1px solid #334155", background: "transparent", color: "#64748b", fontSize: 13, cursor: "pointer" }}
          >
            Job: {jobId.slice(0, 8)}… ×
          </button>
        )}
      </div>

      {isLoading ? (
        <div style={{ color: "#64748b", textAlign: "center", padding: 64 }}>Loading…</div>
      ) : logs.length === 0 ? (
        <div style={{ textAlign: "center", padding: 64, color: "#64748b" }}>No audit log entries.</div>
      ) : (
        <>
          <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
            {/* Header */}
            <div style={{
              display: "grid",
              gridTemplateColumns: "24px 1fr 120px 140px 160px",
              gap: 12,
              padding: "6px 12px",
              fontSize: 11,
              fontWeight: 700,
              color: "#475569",
              textTransform: "uppercase",
              letterSpacing: "0.05em",
            }}>
              <span />
              <span>Action</span>
              <span>Asset</span>
              <span>Job</span>
              <span>Time</span>
            </div>

            {logs.map((log: AuditLog) => (
              <div key={log.id} style={{
                display: "grid",
                gridTemplateColumns: "24px 1fr 120px 140px 160px",
                gap: 12,
                padding: "10px 12px",
                background: "#1e293b",
                border: "1px solid #334155",
                borderRadius: 8,
                alignItems: "center",
              }}>
                <StatusIcon status={log.status} />
                <div>
                  <span style={{
                    fontSize: 12,
                    fontWeight: 600,
                    color: actionColor(log.action),
                  }}>
                    {log.action}
                  </span>
                  {log.error_message && (
                    <div style={{ fontSize: 11, color: "#ef4444", marginTop: 2 }}>
                      {log.error_message.slice(0, 120)}
                    </div>
                  )}
                </div>
                <span style={{ fontSize: 11, color: "#64748b", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                  {log.asset_id ? log.asset_id.slice(0, 8) + "…" : "—"}
                </span>
                <span style={{ fontSize: 11, color: "#64748b", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                  {log.job_run_id ? (
                    <button
                      onClick={() => setParam("job_run_id", log.job_run_id!)}
                      style={{ background: "none", border: "none", cursor: "pointer", color: "#38bdf8", fontSize: 11, padding: 0 }}
                    >
                      {log.job_run_id.slice(0, 8)}…
                    </button>
                  ) : "—"}
                </span>
                <span style={{ fontSize: 11, color: "#475569" }}>
                  {new Date(log.created_at).toLocaleString()}
                </span>
              </div>
            ))}
          </div>

          {/* Pagination */}
          <div style={{ display: "flex", gap: 8, justifyContent: "center", alignItems: "center", marginTop: 20 }}>
            <button
              onClick={() => setParam("page", String(Math.max(1, page - 1)))}
              disabled={page <= 1}
              style={{ padding: "7px 14px", borderRadius: 6, border: "1px solid #334155", background: "transparent", color: page <= 1 ? "#334155" : "#94a3b8", cursor: page <= 1 ? "default" : "pointer", fontSize: 13 }}
            >
              ← Prev
            </button>
            <span style={{ fontSize: 13, color: "#64748b" }}>Page {page} of {totalPages}</span>
            <button
              onClick={() => setParam("page", String(Math.min(totalPages, page + 1)))}
              disabled={page >= totalPages}
              style={{ padding: "7px 14px", borderRadius: 6, border: "1px solid #334155", background: "transparent", color: page >= totalPages ? "#334155" : "#94a3b8", cursor: page >= totalPages ? "default" : "pointer", fontSize: 13 }}
            >
              Next →
            </button>
          </div>
        </>
      )}
    </div>
  );
}
