import React, { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Link, useSearchParams } from "react-router-dom";
import { getAuditLogs, getAuditLogCount, getJobs } from "../services/api";
import LogPanel from "../components/LogPanel";
import type { AuditLog, JobRun } from "../types";
import { CheckCircle, XCircle, Clock, ChevronDown, ChevronUp, Search, Copy, Check } from "lucide-react";

const PAGE_SIZE = 50;
const sectionStyle: React.CSSProperties = {
  background: "#0f172a",
  border: "1px solid #1e293b",
  borderRadius: 12,
  padding: 20,
  marginBottom: 24,
};

function StatusIcon({ status }: { status?: string }) {
  if (status === "success") return <CheckCircle size={13} color="#22c55e" />;
  if (status === "failed") return <XCircle size={13} color="#ef4444" />;
  return <Clock size={13} color="#64748b" />;
}

function jobTypeLabel(jobType: string) {
  if (jobType === "asset_sync") return "Asset sync job";
  if (jobType === "classification") return "Classification job";
  return jobType.replace(/_/g, " ");
}

function jobStatusColor(status: string) {
  if (status === "completed") return "#22c55e";
  if (status === "failed") return "#ef4444";
  if (status === "paused") return "#f59e0b";
  if (status === "cancelled") return "#94a3b8";
  return "#38bdf8";
}

function levelColor(level?: string) {
  if (level === "error") return "#ef4444";
  if (level === "warning") return "#f59e0b";
  return "#64748b";
}

function actionColor(action: string) {
  if (action.includes("description")) return "#38bdf8";
  if (action.includes("tag")) return "#a78bfa";
  if (action.includes("album")) return "#34d399";
  if (action.includes("error") || action.includes("fail")) return "#ef4444";
  return "#94a3b8";
}

function CopyButton({ value }: { value: string }) {
  const [copied, setCopied] = useState(false);
  const handleCopy = (e: React.MouseEvent) => {
    e.stopPropagation();
    navigator.clipboard.writeText(value).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    });
  };
  return (
    <button
      onClick={handleCopy}
      title="Copy JSON"
      style={{ background: "transparent", border: "none", cursor: "pointer", color: copied ? "#22c55e" : "#475569", padding: "2px 6px", borderRadius: 4 }}
    >
      {copied ? <Check size={11} /> : <Copy size={11} />}
    </button>
  );
}

function LogRow({ log, onJobFilter }: { log: AuditLog; onJobFilter: (id: string) => void }) {
  const [expanded, setExpanded] = useState(false);
  const jsonStr = JSON.stringify(log, null, 2);

  return (
    <>
      <div
        onClick={() => setExpanded((v) => !v)}
        style={{
          display: "grid",
          gridTemplateColumns: "20px 80px 1fr 90px 110px 130px 26px",
          gap: 10,
          padding: "10px 12px",
          background: expanded ? "#0f172a" : "#1e293b",
          border: "1px solid #334155",
          borderRadius: expanded ? "8px 8px 0 0" : 8,
          alignItems: "center",
          cursor: "pointer",
          marginBottom: expanded ? 0 : 3,
        }}
      >
        <StatusIcon status={log.status} />

        {/* Level badge */}
        <span style={{
          fontSize: 10, fontWeight: 700, textTransform: "uppercase",
          color: levelColor(log.level), letterSpacing: "0.05em",
        }}>
          {log.level ?? "info"}
        </span>

        {/* Action + error */}
        <div style={{ overflow: "hidden" }}>
          <span style={{ fontSize: 12, fontWeight: 600, color: actionColor(log.action) }}>
            {log.action}
          </span>
          {log.source && (
            <span style={{ fontSize: 11, color: "#475569", marginLeft: 8 }}>[{log.source}]</span>
          )}
          {log.error_message && (
            <div style={{ fontSize: 11, color: "#ef4444", marginTop: 1, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
              {log.error_message.slice(0, 100)}
            </div>
          )}
        </div>

        {/* Asset ID */}
        <span style={{ fontSize: 11, color: "#64748b", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
          {log.asset_id ? log.asset_id.slice(0, 8) + "…" : "—"}
        </span>

        {/* Job ID — clickable */}
        <span style={{ fontSize: 11, color: "#64748b", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
          {log.job_run_id ? (
            <button
              onClick={(e) => { e.stopPropagation(); onJobFilter(log.job_run_id!); }}
              style={{ background: "none", border: "none", cursor: "pointer", color: "#38bdf8", fontSize: 11, padding: 0 }}
            >
              {log.job_run_id.slice(0, 8)}…
            </button>
          ) : "—"}
        </span>

        {/* Timestamp */}
        <span style={{ fontSize: 11, color: "#475569" }}>
          {new Date(log.created_at).toLocaleString()}
        </span>

        {expanded ? <ChevronUp size={12} color="#475569" /> : <ChevronDown size={12} color="#475569" />}
      </div>

      {/* Expanded detail */}
      {expanded && (
        <div style={{
          background: "#0a0f1a",
          border: "1px solid #334155",
          borderTop: "none",
          borderRadius: "0 0 8px 8px",
          padding: "12px 14px",
          marginBottom: 3,
        }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 8 }}>
            <div style={{ fontSize: 11, fontWeight: 600, color: "#475569", textTransform: "uppercase" }}>Details</div>
            <CopyButton value={jsonStr} />
          </div>
          {log.error_message && (
            <div style={{ fontSize: 12, color: "#ef4444", marginBottom: 8, lineHeight: 1.5 }}>
              <strong>Error:</strong> {log.error_message}
            </div>
          )}
          {log.details_json && Object.keys(log.details_json).length > 0 && (
            <pre style={{
              fontSize: 11, color: "#94a3b8", background: "#0f172a",
              border: "1px solid #1e293b", borderRadius: 6, padding: "8px 12px",
              overflow: "auto", maxHeight: 180, margin: 0, lineHeight: 1.5,
            }}>
              {JSON.stringify(log.details_json, null, 2)}
            </pre>
          )}
          <div style={{ marginTop: 8, display: "flex", gap: 20, fontSize: 11, color: "#475569", flexWrap: "wrap" }}>
            <span>ID: {log.id}</span>
            {log.asset_id && <span>Asset: {log.asset_id}</span>}
            {log.job_run_id && <span>Job: {log.job_run_id}</span>}
          </div>
        </div>
      )}
    </>
  );
}

function JobLogRow({
  job,
  activeJobFilter,
  onJobFilter,
}: {
  job: JobRun;
  activeJobFilter: string;
  onJobFilter: (id: string) => void;
}) {
  const [expanded, setExpanded] = useState(false);
  const logLines = job.log_lines ?? [];
  const hasLogs = logLines.length > 0;
  const isFiltered = activeJobFilter === job.id;

  return (
    <>
      <div
        onClick={() => setExpanded((v) => !v)}
        style={{
          display: "flex",
          justifyContent: "space-between",
          gap: 16,
          padding: "12px 14px",
          background: expanded ? "#111827" : "#1e293b",
          border: "1px solid #334155",
          borderRadius: expanded ? "8px 8px 0 0" : 8,
          cursor: "pointer",
          alignItems: "center",
          marginBottom: expanded ? 0 : 8,
        }}
      >
        <div style={{ minWidth: 0, flex: 1 }}>
          <div style={{ display: "flex", gap: 8, alignItems: "center", flexWrap: "wrap", marginBottom: 4 }}>
            <span style={{ fontSize: 13, fontWeight: 700, color: "#f1f5f9" }}>{jobTypeLabel(job.job_type)}</span>
            <span style={{
              fontSize: 10,
              fontWeight: 700,
              textTransform: "uppercase",
              letterSpacing: "0.06em",
              color: jobStatusColor(job.status),
            }}>
              {job.status.replace(/_/g, " ")}
            </span>
          </div>
          <div style={{ fontSize: 12, color: "#94a3b8", display: "flex", gap: 10, flexWrap: "wrap" }}>
            {job.total_count > 0 && <span>{job.processed_count} / {job.total_count} processed</span>}
            {job.success_count > 0 && <span>{job.success_count} succeeded</span>}
            {job.error_count > 0 && <span>{job.error_count} failed</span>}
            {job.message && <span style={{ color: "#cbd5e1" }}>{job.message}</span>}
            {!hasLogs && !job.message && <span>No line output yet</span>}
          </div>
        </div>

        <div style={{ display: "flex", alignItems: "center", gap: 10, flexShrink: 0 }}>
          <div style={{ textAlign: "right", fontSize: 11, color: "#64748b" }}>
            <div>Updated</div>
            <div>{new Date(job.updated_at ?? job.created_at).toLocaleString()}</div>
          </div>
          {expanded ? <ChevronUp size={12} color="#475569" /> : <ChevronDown size={12} color="#475569" />}
        </div>
      </div>

      {expanded && (
        <div style={{
          background: "#0a0f1a",
          border: "1px solid #334155",
          borderTop: "none",
          borderRadius: "0 0 8px 8px",
          padding: "14px",
          marginBottom: 8,
        }}>
          {hasLogs ? (
            <LogPanel lines={logLines} maxHeight={220} />
          ) : (
            <div style={{ color: "#64748b", fontSize: 12 }}>This job has not emitted line-by-line output yet.</div>
          )}
          <div style={{ display: "flex", gap: 10, flexWrap: "wrap", alignItems: "center", marginTop: 12 }}>
            <button
              onClick={(e) => {
                e.stopPropagation();
                onJobFilter(job.id);
              }}
              style={{
                padding: "7px 10px",
                borderRadius: 8,
                border: `1px solid ${isFiltered ? "#38bdf8" : "#334155"}`,
                background: "transparent",
                color: isFiltered ? "#38bdf8" : "#cbd5e1",
                fontSize: 12,
                cursor: "pointer",
              }}
            >
              {isFiltered ? "Filtering activity for this job" : "Show matching activity"}
            </button>
            <Link
              to="/jobs"
              onClick={(e) => e.stopPropagation()}
              style={{ color: "#38bdf8", fontSize: 12, textDecoration: "none" }}
            >
              Open jobs page
            </Link>
          </div>
        </div>
      )}
    </>
  );
}

export default function Logs() {
  const [searchParams, setSearchParams] = useSearchParams();

  const page = parseInt(searchParams.get("page") || "1", 10);
  const statusFilter = searchParams.get("status") || "";
  const actionFilter = searchParams.get("action") || "";
  const levelFilter = searchParams.get("level") || "";
  const sourceFilter = searchParams.get("source") || "";
  const jobId = searchParams.get("job_run_id") || "";
  const textSearch = searchParams.get("q") || "";
  const [searchInput, setSearchInput] = useState(textSearch);

  function setParam(key: string, value: string) {
    setSearchParams((prev) => {
      const next = new URLSearchParams(prev);
      if (value) next.set(key, value); else next.delete(key);
      if (key !== "page") next.set("page", "1");
      return next;
    });
  }

  const params = {
    page,
    page_size: PAGE_SIZE,
    status: statusFilter || undefined,
    action: actionFilter || undefined,
    level: levelFilter || undefined,
    source: sourceFilter || undefined,
    job_run_id: jobId || undefined,
    q: textSearch || undefined,
  };

  const { data: logs = [], isLoading } = useQuery({
    queryKey: ["audit-logs", params],
    queryFn: () => getAuditLogs(params),
  });

  const { data: countData } = useQuery({
    queryKey: ["audit-log-count", statusFilter, levelFilter, jobId],
    queryFn: () => getAuditLogCount({ status: statusFilter || undefined, level: levelFilter || undefined, job_run_id: jobId || undefined }),
  });

  const { data: recentJobs = [], isLoading: jobsLoading } = useQuery({
    queryKey: ["logs-page-jobs"],
    queryFn: () => getJobs({ limit: 8 }),
    refetchInterval: 3_000,
  });

  const totalPages = countData ? Math.ceil(countData.count / PAGE_SIZE) : 1;
  const jobsWithOutput = recentJobs.filter((job) => (job.log_lines?.length ?? 0) > 0 || Boolean(job.message));

  return (
    <div style={{ padding: "32px 40px", maxWidth: 1100 }}>
      <div style={{ marginBottom: 24 }}>
        <h1 style={{ fontSize: 24, fontWeight: 700, color: "#f1f5f9", margin: 0 }}>Logs</h1>
        <p style={{ fontSize: 14, color: "#64748b", margin: "4px 0 0" }}>
          Operational activity, write-back results, errors, and recent job output.
        </p>
      </div>

      <section style={sectionStyle}>
        <div style={{ marginBottom: 16 }}>
          <h2 style={{ fontSize: 18, fontWeight: 700, color: "#f1f5f9", margin: 0 }}>Recent job output</h2>
          <p style={{ fontSize: 13, color: "#64748b", margin: "4px 0 0" }}>
            Live line logs and status messages from recent sync and classification jobs.
          </p>
        </div>

        {jobsLoading ? (
          <div style={{ color: "#64748b", textAlign: "center", padding: 36 }}>Loading recent jobs…</div>
        ) : jobsWithOutput.length === 0 ? (
          <div style={{ textAlign: "center", padding: 36, color: "#64748b" }}>No recent job output yet.</div>
        ) : (
          <div>
            {jobsWithOutput.map((job) => (
              <JobLogRow
                key={job.id}
                job={job}
                activeJobFilter={jobId}
                onJobFilter={(id) => setParam("job_run_id", id)}
              />
            ))}
          </div>
        )}
      </section>

      <section style={sectionStyle}>
        <div style={{ marginBottom: 16 }}>
          <h2 style={{ fontSize: 18, fontWeight: 700, color: "#f1f5f9", margin: 0 }}>Activity log</h2>
          <p style={{ fontSize: 13, color: "#64748b", margin: "4px 0 0" }}>
            {countData ? `${countData.count.toLocaleString()} persisted activity entries` : "Persisted write-backs, classifications, warnings, and errors."}
          </p>
        </div>

        <div style={{ display: "flex", gap: 8, marginBottom: 16, flexWrap: "wrap", alignItems: "center" }}>
          <div style={{ position: "relative", flex: "1 1 200px" }}>
            <Search size={13} color="#64748b" style={{ position: "absolute", left: 9, top: "50%", transform: "translateY(-50%)" }} />
            <input
              value={searchInput}
              onChange={(e) => setSearchInput(e.target.value)}
              onKeyDown={(e) => { if (e.key === "Enter") setParam("q", searchInput); }}
              onBlur={() => setParam("q", searchInput)}
              placeholder="Search event, asset ID, job ID…"
              style={{
                width: "100%", paddingLeft: 28, padding: "7px 10px 7px 28px",
                background: "#1e293b", border: "1px solid #334155",
                borderRadius: 8, color: "#f1f5f9", fontSize: 12, outline: "none", boxSizing: "border-box",
              }}
            />
          </div>

          <select value={levelFilter} onChange={(e) => setParam("level", e.target.value)}
            style={{ background: "#1e293b", border: "1px solid #334155", color: "#94a3b8", borderRadius: 8, padding: "7px 10px", fontSize: 12 }}>
            <option value="">All levels</option>
            <option value="info">Info</option>
            <option value="warning">Warning</option>
            <option value="error">Error</option>
          </select>

          <select value={statusFilter} onChange={(e) => setParam("status", e.target.value)}
            style={{ background: "#1e293b", border: "1px solid #334155", color: "#94a3b8", borderRadius: 8, padding: "7px 10px", fontSize: 12 }}>
            <option value="">All statuses</option>
            <option value="success">Success</option>
            <option value="failed">Failed</option>
          </select>

          <select value={actionFilter} onChange={(e) => setParam("action", e.target.value)}
            style={{ background: "#1e293b", border: "1px solid #334155", color: "#94a3b8", borderRadius: 8, padding: "7px 10px", fontSize: 12 }}>
            <option value="">All event types</option>
            <option value="writeback_description">Write description</option>
            <option value="writeback_tags">Write tags</option>
            <option value="writeback_album">Write album</option>
            <option value="classification_error">Classification error</option>
          </select>

          {jobId && (
            <button onClick={() => setParam("job_run_id", "")}
              style={{ padding: "7px 10px", borderRadius: 8, border: "1px solid #334155", background: "transparent", color: "#38bdf8", fontSize: 12, cursor: "pointer" }}>
              Job: {jobId.slice(0, 8)}… ×
            </button>
          )}
        </div>

        {isLoading ? (
          <div style={{ color: "#64748b", textAlign: "center", padding: 64 }}>Loading…</div>
        ) : logs.length === 0 ? (
          <div style={{ textAlign: "center", padding: 64, color: "#64748b" }}>No activity entries.</div>
        ) : (
          <>
            <div style={{
              display: "grid",
              gridTemplateColumns: "20px 80px 1fr 90px 110px 130px 26px",
              gap: 10, padding: "4px 12px", marginBottom: 4,
              fontSize: 10, fontWeight: 700, color: "#334155",
              textTransform: "uppercase", letterSpacing: "0.07em",
            }}>
              <span />
              <span>Level</span>
              <span>Event / Source</span>
              <span>Asset</span>
              <span>Job</span>
              <span>Time</span>
              <span />
            </div>

            <div>
              {logs.map((log: AuditLog) => (
                <LogRow key={log.id} log={log} onJobFilter={(id) => setParam("job_run_id", id)} />
              ))}
            </div>

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
      </section>
    </div>
  );
}
