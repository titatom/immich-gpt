import React, { useState, useCallback } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useSearchParams } from "react-router-dom";
import {
  getReviewQueue,
  getReviewCount,
  getBuckets,
  getAlbums,
  approveAsset,
  rejectAsset,
  bulkReview,
  getThumbnailUrl,
  reclassifyAssets,
  getReviewQueueIds,
} from "../services/api";
import type { ReviewItem, Bucket } from "../types";
import Thumbnail from "../components/Thumbnail";
import ConfidenceBadge from "../components/ConfidenceBadge";
import TagList from "../components/TagList";
import { CheckCircle, XCircle, ChevronDown, ChevronUp, RefreshCw } from "lucide-react";
import { useNavigate } from "react-router-dom";

interface ApproveData {
  approved_bucket_id?: string;
  approved_bucket_name?: string;
  approved_description?: string;
  approved_tags?: string[];
  approved_subalbum?: string;
  subalbum_approved?: boolean;
  trigger_writeback?: boolean;
}

/** Per-asset editable fields stored in the parent to persist across page navigation. */
interface EditState {
  description: string;
  tags: string[];
  bucketId: string;
  subalbum: string;
}

interface ReviewCardProps {
  item: ReviewItem;
  buckets: Bucket[];
  albums: Array<{ id: string; albumName: string }>;
  editState: EditState;
  onEditChange: (assetId: string, patch: Partial<EditState>) => void;
  onApprove: (assetId: string, data: ApproveData) => void;
  onReject: (assetId: string) => void;
  onReanalyse: (assetId: string) => void;
  approving?: boolean;
  rejecting?: boolean;
  reanalysing?: boolean;
}

function ReviewCard({
  item,
  buckets,
  albums,
  editState,
  onEditChange,
  onApprove,
  onReject,
  onReanalyse,
  approving,
  rejecting,
  reanalysing,
}: ReviewCardProps) {
  const [showMeta, setShowMeta] = useState(false);
  const [lightbox, setLightbox] = useState(false);

  const busy = approving || rejecting || reanalysing;

  const handleApprove = () => {
    if (busy) return;
    const bucket = buckets.find((b) => b.id === editState.bucketId);
    onApprove(item.asset_id, {
      approved_bucket_id: editState.bucketId || item.suggested_bucket_id,
      approved_bucket_name: bucket?.name || item.suggested_bucket_name,
      approved_description: editState.description,
      approved_tags: editState.tags,
      approved_subalbum: editState.subalbum || undefined,
      subalbum_approved: !!editState.subalbum,
      trigger_writeback: true,
    });
  };

  return (
    <div style={{
      background: "#1e293b", border: "1px solid #334155",
      borderRadius: 12, overflow: "hidden", marginBottom: 12,
    }}>
      <div style={{ display: "flex", gap: 16, padding: 16, alignItems: "flex-start" }}>
        {/* Thumbnail */}
        <Thumbnail assetId={item.asset_id} size={88} onClick={() => setLightbox(true)} />

        {/* Fields — always editable */}
        <div style={{ flex: 1, minWidth: 0, display: "flex", flexDirection: "column", gap: 10 }}>
          {/* Filename + date + location */}
          <div style={{ display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap" }}>
            <span style={{ fontSize: 13, fontWeight: 600, color: "#f1f5f9", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
              {item.original_filename || item.immich_id}
            </span>
            {item.file_created_at && (
              <span style={{ fontSize: 11, color: "#475569" }}>{new Date(item.file_created_at).toLocaleDateString()}</span>
            )}
            {item.city && <span style={{ fontSize: 11, color: "#475569" }}>{item.city}</span>}
          </div>

          {/* Bucket select + confidence */}
          <div style={{ display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap" }}>
            <span style={{ fontSize: 11, color: "#64748b", flexShrink: 0 }}>Bucket:</span>
            <select
              value={editState.bucketId}
              onChange={(e) => onEditChange(item.asset_id, { bucketId: e.target.value })}
              style={{
                background: "#0f172a", border: "1px solid #334155",
                borderRadius: 6, color: "#38bdf8", fontSize: 12,
                fontWeight: 600, padding: "2px 8px", cursor: "pointer",
              }}
            >
              <option value="">— none —</option>
              {buckets.filter((b) => b.enabled).map((b) => (
                <option key={b.id} value={b.id}>{b.name}</option>
              ))}
            </select>
            <ConfidenceBadge confidence={item.confidence} />
            {item.provider_name && (
              <span style={{ fontSize: 11, color: "#475569" }}>via {item.provider_name}</span>
            )}
          </div>

          {/* Explanation */}
          {item.explanation && (
            <div style={{
              fontSize: 12, color: "#94a3b8", background: "#0f172a",
              borderRadius: 6, padding: "6px 10px", lineHeight: 1.5,
            }}>
              {item.explanation}
            </div>
          )}

          {/* Description — always editable */}
          <div>
            <label style={{ fontSize: 11, color: "#64748b", display: "block", marginBottom: 3 }}>Description</label>
            <textarea
              value={editState.description}
              onChange={(e) => onEditChange(item.asset_id, { description: e.target.value })}
              rows={2}
              style={{
                width: "100%", boxSizing: "border-box",
                background: "#0f172a", border: "1px solid #334155",
                borderRadius: 6, color: "#f1f5f9", fontSize: 12,
                padding: "6px 10px", resize: "vertical", outline: "none", lineHeight: 1.5,
              }}
            />
          </div>

          {/* Tags — always editable */}
          <div>
            <label style={{ fontSize: 11, color: "#64748b", display: "block", marginBottom: 3 }}>Tags</label>
            <TagList
              tags={editState.tags}
              editable
              onChange={(tags) => onEditChange(item.asset_id, { tags })}
            />
          </div>

          {/* Sub-album — always editable with existing album suggestions */}
          <div>
            <label style={{ fontSize: 11, color: "#64748b", display: "block", marginBottom: 3 }}>
              Sub-album / Album
              {item.subalbum_suggestion && (
                <span style={{ marginLeft: 6, color: "#64748b", fontWeight: 400 }}>
                  (suggested: <button
                    onClick={() => onEditChange(item.asset_id, { subalbum: item.subalbum_suggestion! })}
                    style={{ background: "none", border: "none", color: "#38bdf8", fontSize: 11, cursor: "pointer", padding: 0 }}
                  >{item.subalbum_suggestion}</button>)
                </span>
              )}
            </label>
            <div style={{ display: "flex", gap: 6 }}>
              <input
                value={editState.subalbum}
                onChange={(e) => onEditChange(item.asset_id, { subalbum: e.target.value })}
                placeholder="Album name or leave empty"
                style={{
                  flex: 1, background: "#0f172a", border: "1px solid #334155",
                  borderRadius: 6, color: "#f1f5f9", fontSize: 12,
                  padding: "6px 10px", outline: "none",
                }}
              />
              {albums.length > 0 && (
                <select
                  value=""
                  onChange={(e) => { if (e.target.value) onEditChange(item.asset_id, { subalbum: e.target.value }); }}
                  style={{
                    background: "#0f172a", border: "1px solid #334155", borderRadius: 6,
                    color: "#64748b", fontSize: 12, padding: "6px 10px",
                  }}
                >
                  <option value="">Existing albums…</option>
                  {albums.map((a) => <option key={a.id} value={a.albumName}>{a.albumName}</option>)}
                </select>
              )}
            </div>
          </div>

          {/* Metadata toggle */}
          <button
            onClick={() => setShowMeta((v) => !v)}
            style={{
              alignSelf: "flex-start", background: "transparent", border: "none",
              color: "#475569", fontSize: 11, cursor: "pointer",
              display: "flex", alignItems: "center", gap: 4, padding: 0,
            }}
          >
            {showMeta ? <ChevronUp size={11} /> : <ChevronDown size={11} />}
            {showMeta ? "Hide metadata" : "Show metadata"}
          </button>
          {showMeta && (
            <div style={{ fontSize: 11, color: "#475569", display: "flex", gap: 16, flexWrap: "wrap" }}>
              {item.camera_make && <span>Camera: {item.camera_make} {item.camera_model}</span>}
              {item.city && <span>Location: {item.city}{item.country ? `, ${item.country}` : ""}</span>}
              {item.asset_type && <span>Type: {item.asset_type}</span>}
            </div>
          )}
        </div>

        {/* Actions */}
        <div style={{ display: "flex", flexDirection: "column", gap: 6, flexShrink: 0 }}>
          <button
            onClick={handleApprove}
            disabled={busy}
            style={{
              display: "flex", alignItems: "center", gap: 6,
              padding: "8px 14px", borderRadius: 8, border: "none",
              background: approving ? "#166534" : "#16a34a",
              color: "white", fontSize: 13, fontWeight: 600,
              cursor: busy ? "not-allowed" : "pointer",
              opacity: busy && !approving ? 0.5 : 1,
            }}
          >
            <CheckCircle size={14} /> {approving ? "Approving…" : "Approve"}
          </button>
          <button
            onClick={() => { if (!busy) onReject(item.asset_id); }}
            disabled={busy}
            style={{
              display: "flex", alignItems: "center", gap: 6,
              padding: "8px 14px", borderRadius: 8, border: "1px solid #334155",
              background: "transparent", color: rejecting ? "#94a3b8" : "#94a3b8",
              fontSize: 13, fontWeight: 500,
              cursor: busy ? "not-allowed" : "pointer",
              opacity: busy && !rejecting ? 0.5 : 1,
            }}
          >
            <XCircle size={14} /> {rejecting ? "Rejecting…" : "Reject"}
          </button>
          <button
            onClick={() => { if (!busy) onReanalyse(item.asset_id); }}
            disabled={busy}
            title="Re-run AI analysis on this asset"
            style={{
              display: "flex", alignItems: "center", gap: 6,
              padding: "8px 14px", borderRadius: 8, border: "1px solid #334155",
              background: "transparent", color: "#7c3aed", fontSize: 13, fontWeight: 500,
              cursor: busy ? "not-allowed" : "pointer",
              opacity: busy && !reanalysing ? 0.5 : 1,
            }}
          >
            <RefreshCw size={14} /> {reanalysing ? "Starting…" : "Re-analyse"}
          </button>
        </div>
      </div>

      {/* Lightbox */}
      {lightbox && (
        <div
          onClick={() => setLightbox(false)}
          style={{
            position: "fixed", inset: 0, background: "rgba(0,0,0,0.85)",
            display: "flex", alignItems: "center", justifyContent: "center",
            zIndex: 1000, cursor: "pointer",
          }}
        >
          <img
            src={getThumbnailUrl(item.asset_id, "preview")}
            alt=""
            style={{ maxWidth: "90vw", maxHeight: "90vh", borderRadius: 12, objectFit: "contain" }}
            onClick={(e) => e.stopPropagation()}
          />
        </div>
      )}
    </div>
  );
}

/** Build an EditState from a ReviewItem's suggestion values. */
function buildDefaultEditState(item: ReviewItem): EditState {
  return {
    description: item.description_suggestion ?? item.current_description ?? "",
    tags: item.tags_suggestion ?? item.current_tags ?? [],
    bucketId: item.suggested_bucket_id ?? "",
    subalbum: item.subalbum_suggestion ?? "",
  };
}

export default function Review() {
  const qc = useQueryClient();
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const page = parseInt(searchParams.get("page") || "1", 10);
  const selectedBucketFilter = searchParams.get("bucket_id") || "";

  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [selectAllPages, setSelectAllPages] = useState(false);
  const [loadingAllIds, setLoadingAllIds] = useState(false);
  const [reanalyseMessage, setReanalyseMessage] = useState<string | null>(null);
  const [mutationError, setMutationError] = useState<string | null>(null);

  /**
   * Persistent edit state keyed by asset_id.
   * Survives page navigation. Cleared when bucket filter changes (new queue context).
   */
  const [editStates, setEditStates] = useState<Map<string, EditState>>(new Map());

  const pageSize = 20;

  /** Change page without resetting selection or edits. */
  function goToPage(newPage: number) {
    setSearchParams((prev) => {
      const next = new URLSearchParams(prev);
      next.set("page", String(newPage));
      return next;
    });
  }

  /** Change bucket filter — reset selection and edits since the context changes. */
  function setBucketFilter(bucketId: string) {
    setSearchParams((prev) => {
      const next = new URLSearchParams(prev);
      if (bucketId) next.set("bucket_id", bucketId); else next.delete("bucket_id");
      next.set("page", "1");
      return next;
    });
    setSelected(new Set());
    setSelectAllPages(false);
    setEditStates(new Map());
  }

  const handleEditChange = useCallback((assetId: string, patch: Partial<EditState>) => {
    setEditStates((prev) => {
      const next = new Map(prev);
      const current = next.get(assetId);
      if (current) {
        next.set(assetId, { ...current, ...patch });
      }
      return next;
    });
  }, []);

  const { data: buckets = [] } = useQuery({ queryKey: ["buckets"], queryFn: getBuckets });
  const { data: albums = [] } = useQuery({ queryKey: ["albums"], queryFn: getAlbums });

  const { data: items = [], isLoading } = useQuery({
    queryKey: ["review-queue", page, selectedBucketFilter],
    queryFn: () => getReviewQueue({ page, page_size: pageSize, bucket_id: selectedBucketFilter || undefined }),
    refetchInterval: 15_000,
  });

  // When items load, populate edit states for new assets (don't overwrite existing edits).
  React.useEffect(() => {
    if (!items.length) return;
    setEditStates((prev) => {
      const next = new Map(prev);
      let changed = false;
      for (const item of items) {
        if (!next.has(item.asset_id)) {
          next.set(item.asset_id, buildDefaultEditState(item));
          changed = true;
        }
      }
      return changed ? next : prev;
    });
  }, [items]);

  const { data: countData } = useQuery<{ count: number }>({
    queryKey: ["review-count"],
    queryFn: () => getReviewCount(),
    refetchInterval: 10_000,
  });

  const approveMutation = useMutation({
    mutationFn: ({ assetId, data }: { assetId: string; data: ApproveData }) => approveAsset(assetId, data),
    onSuccess: (_result, { assetId }) => {
      setMutationError(null);
      // Remove the approved asset's edit state.
      setEditStates((prev) => { const next = new Map(prev); next.delete(assetId); return next; });
      qc.invalidateQueries({ queryKey: ["review-queue"] });
      qc.invalidateQueries({ queryKey: ["review-count"] });
    },
    onError: (err: unknown) => {
      const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      setMutationError(detail || "Failed to approve asset. Please try again.");
      setTimeout(() => setMutationError(null), 6000);
    },
  });

  const rejectMutation = useMutation({
    mutationFn: rejectAsset,
    onSuccess: (_result, assetId) => {
      setMutationError(null);
      setEditStates((prev) => { const next = new Map(prev); next.delete(assetId); return next; });
      qc.invalidateQueries({ queryKey: ["review-queue"] });
      qc.invalidateQueries({ queryKey: ["review-count"] });
    },
    onError: (err: unknown) => {
      const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      setMutationError(detail || "Failed to reject asset. Please try again.");
      setTimeout(() => setMutationError(null), 6000);
    },
  });

  const bulkMutation = useMutation({
    mutationFn: (action: "approve_all" | "reject_all") =>
      bulkReview({ asset_ids: Array.from(selected), action, trigger_writeback: true }),
    onSuccess: () => {
      setMutationError(null);
      // Clear edit states for bulk-actioned assets.
      setEditStates((prev) => {
        const next = new Map(prev);
        for (const id of selected) next.delete(id);
        return next;
      });
      setSelected(new Set());
      setSelectAllPages(false);
      qc.invalidateQueries({ queryKey: ["review-queue"] });
      qc.invalidateQueries({ queryKey: ["review-count"] });
    },
    onError: (err: unknown) => {
      const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      setMutationError(detail || "Bulk action failed. Please try again.");
      setTimeout(() => setMutationError(null), 6000);
    },
  });

  const reclassifyMut = useMutation({
    mutationFn: (ids: string[]) => reclassifyAssets(ids, true),
    onSuccess: (data, ids) => {
      setReanalyseMessage(
        `Re-analysis job started for ${ids.length} asset${ids.length !== 1 ? "s" : ""}. Job ID: ${data.job_id}`
      );
      setSelected(new Set());
      setSelectAllPages(false);
      qc.invalidateQueries({ queryKey: ["jobs"] });
      setTimeout(() => setReanalyseMessage(null), 5000);
    },
  });

  const toggleSelect = (id: string) => {
    setSelectAllPages(false);
    const s = new Set(selected);
    if (s.has(id)) { s.delete(id); } else { s.add(id); }
    setSelected(s);
  };

  const allPageSelected = items.length > 0 && items.every((i) => selected.has(i.asset_id));

  function toggleSelectAll() {
    if (selectAllPages || allPageSelected) {
      setSelected(new Set());
      setSelectAllPages(false);
    } else {
      setSelected(new Set(items.map((i) => i.asset_id)));
    }
  }

  async function selectAcrossAllPages() {
    setLoadingAllIds(true);
    try {
      const result = await getReviewQueueIds({
        bucket_id: selectedBucketFilter || undefined,
      });
      setSelected(new Set(result.ids));
      setSelectAllPages(true);
    } finally {
      setLoadingAllIds(false);
    }
  }

  return (
    <div style={{ padding: "32px 40px", maxWidth: 960 }}>
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 24 }}>
        <div>
          <h1 style={{ fontSize: 24, fontWeight: 700, color: "#f1f5f9", margin: 0 }}>Review Queue</h1>
          <p style={{ fontSize: 14, color: "#64748b", margin: "4px 0 0" }}>
            {countData?.count ?? 0} items pending review
          </p>
        </div>
        <select
          value={selectedBucketFilter}
          onChange={(e) => setBucketFilter(e.target.value)}
          style={{ background: "#1e293b", border: "1px solid #334155", color: "#94a3b8", borderRadius: 8, padding: "7px 12px", fontSize: 13 }}
        >
          <option value="">All buckets</option>
          {buckets.map((b) => <option key={b.id} value={b.id}>{b.name}</option>)}
        </select>
      </div>

      {/* Mutation error banner */}
      {mutationError && (
        <div style={{
          marginBottom: 16, padding: "10px 16px", borderRadius: 8,
          background: "rgba(239,68,68,0.12)", border: "1px solid rgba(239,68,68,0.3)",
          fontSize: 13, color: "#fca5a5",
          display: "flex", alignItems: "center", justifyContent: "space-between",
        }}>
          <span>{mutationError}</span>
          <button onClick={() => setMutationError(null)} style={{ background: "none", border: "none", color: "#f87171", cursor: "pointer", fontSize: 16, lineHeight: 1 }}>×</button>
        </div>
      )}

      {/* Re-analyse message */}
      {reanalyseMessage && (
        <div style={{
          marginBottom: 16, padding: "10px 16px", borderRadius: 8,
          background: "rgba(124,58,237,0.12)", border: "1px solid rgba(124,58,237,0.3)",
          fontSize: 13, color: "#c4b5fd",
          display: "flex", alignItems: "center", justifyContent: "space-between",
        }}>
          <span>{reanalyseMessage}</span>
          <button onClick={() => navigate("/jobs")} style={{ background: "none", border: "none", color: "#a78bfa", cursor: "pointer", fontSize: 12, textDecoration: "underline" }}>
            View Jobs
          </button>
        </div>
      )}

      {/* Bulk actions */}
      {selected.size > 0 && (
        <div style={{
          display: "flex", alignItems: "center", gap: 12,
          padding: "10px 16px", background: "#1e293b", border: "1px solid #334155",
          borderRadius: 8, marginBottom: 16, flexWrap: "wrap",
        }}>
          <span style={{ fontSize: 13, color: "#94a3b8" }}>{selected.size} selected</span>
          <button onClick={() => bulkMutation.mutate("approve_all")} style={{ padding: "6px 14px", borderRadius: 6, border: "none", background: "#16a34a", color: "white", fontSize: 12, fontWeight: 600, cursor: "pointer" }}>
            Approve All
          </button>
          <button onClick={() => bulkMutation.mutate("reject_all")} style={{ padding: "6px 14px", borderRadius: 6, border: "1px solid #334155", background: "transparent", color: "#94a3b8", fontSize: 12, cursor: "pointer" }}>
            Reject All
          </button>
          <button
            onClick={() => reclassifyMut.mutate(Array.from(selected))}
            disabled={reclassifyMut.isPending}
            style={{
              display: "flex", alignItems: "center", gap: 5,
              padding: "6px 14px", borderRadius: 6, border: "1px solid #334155",
              background: "transparent", color: "#7c3aed", fontSize: 12,
              cursor: reclassifyMut.isPending ? "not-allowed" : "pointer",
              opacity: reclassifyMut.isPending ? 0.6 : 1,
            }}
          >
            <RefreshCw size={12} />
            {reclassifyMut.isPending ? "Starting…" : "Re-analyse All"}
          </button>
          <button onClick={() => { setSelected(new Set()); setSelectAllPages(false); }} style={{ padding: "6px 14px", borderRadius: 6, border: "none", background: "transparent", color: "#64748b", fontSize: 12, cursor: "pointer" }}>
            Clear
          </button>
        </div>
      )}

      {items.length > 0 && (
        <div style={{ marginBottom: 8 }}>
          <button
            onClick={toggleSelectAll}
            style={{ background: "transparent", border: "none", color: "#64748b", fontSize: 12, cursor: "pointer", padding: "4px 0" }}
          >
            {(selectAllPages || allPageSelected) ? "Deselect all" : "Select all on page"}
          </button>
        </div>
      )}

      {/* Cross-page select-all banner */}
      {allPageSelected && !selectAllPages && countData && countData.count > items.length && (
        <div style={{
          marginBottom: 12, padding: "10px 16px", borderRadius: 8,
          background: "rgba(56,189,248,0.08)", border: "1px solid rgba(56,189,248,0.25)",
          fontSize: 13, color: "#7dd3fc",
          display: "flex", alignItems: "center", justifyContent: "space-between", gap: 12,
        }}>
          <span>All {items.length} items on this page are selected.</span>
          <button
            onClick={selectAcrossAllPages}
            disabled={loadingAllIds}
            style={{ background: "none", border: "none", color: "#38bdf8", cursor: "pointer", fontSize: 13, fontWeight: 600, whiteSpace: "nowrap" }}
          >
            {loadingAllIds ? "Loading…" : `Select all ${countData.count.toLocaleString()} items`}
          </button>
        </div>
      )}
      {selectAllPages && countData && (
        <div style={{
          marginBottom: 12, padding: "10px 16px", borderRadius: 8,
          background: "rgba(56,189,248,0.08)", border: "1px solid rgba(56,189,248,0.25)",
          fontSize: 13, color: "#7dd3fc",
          display: "flex", alignItems: "center", justifyContent: "space-between", gap: 12,
        }}>
          <span>All {selected.size.toLocaleString()} matching items are selected.</span>
          <button
            onClick={() => { setSelected(new Set()); setSelectAllPages(false); }}
            style={{ background: "none", border: "none", color: "#38bdf8", cursor: "pointer", fontSize: 13, fontWeight: 600 }}
          >
            Clear selection
          </button>
        </div>
      )}

      {isLoading ? (
        <div style={{ color: "#64748b", padding: 32, textAlign: "center" }}>Loading...</div>
      ) : items.length === 0 ? (
        <div style={{ textAlign: "center", padding: 64, background: "#1e293b", borderRadius: 12, border: "1px solid #334155" }}>
          <CheckCircle size={40} color="#22c55e" style={{ marginBottom: 16 }} />
          <div style={{ fontSize: 18, fontWeight: 600, color: "#f1f5f9", marginBottom: 8 }}>All caught up!</div>
          <div style={{ fontSize: 14, color: "#64748b" }}>No items pending review. Run AI classification to generate suggestions.</div>
        </div>
      ) : (
        items.map((item) => (
          <div key={item.asset_id} style={{ position: "relative" }}>
            <div style={{ position: "absolute", top: 12, left: 12, zIndex: 1 }}>
              <input type="checkbox" checked={selected.has(item.asset_id)} onChange={() => toggleSelect(item.asset_id)} style={{ width: 16, height: 16, cursor: "pointer" }} />
            </div>
            <ReviewCard
              item={item}
              buckets={buckets}
              albums={albums}
              editState={editStates.get(item.asset_id) ?? buildDefaultEditState(item)}
              onEditChange={handleEditChange}
              onApprove={(assetId, data) => approveMutation.mutate({ assetId, data })}
              onReject={(assetId) => rejectMutation.mutate(assetId)}
              onReanalyse={(assetId) => reclassifyMut.mutate([assetId])}
              approving={approveMutation.isPending && approveMutation.variables?.assetId === item.asset_id}
              rejecting={rejectMutation.isPending && rejectMutation.variables === item.asset_id}
              reanalysing={reclassifyMut.isPending && reclassifyMut.variables?.length === 1 && reclassifyMut.variables[0] === item.asset_id}
            />
          </div>
        ))
      )}

      {/* Pagination */}
      {(items.length === pageSize || page > 1) && (
        <div style={{ display: "flex", gap: 8, justifyContent: "center", marginTop: 16 }}>
          <button onClick={() => goToPage(Math.max(1, page - 1))} disabled={page === 1}
            style={{ padding: "8px 16px", borderRadius: 8, border: "1px solid #334155", background: "transparent", color: "#94a3b8", cursor: "pointer", opacity: page === 1 ? 0.4 : 1 }}>
            ← Prev
          </button>
          <span style={{ padding: "8px 16px", color: "#64748b", fontSize: 13 }}>Page {page}</span>
          <button onClick={() => goToPage(page + 1)} disabled={items.length < pageSize}
            style={{ padding: "8px 16px", borderRadius: 8, border: "1px solid #334155", background: "transparent", color: "#94a3b8", cursor: "pointer", opacity: items.length < pageSize ? 0.4 : 1 }}>
            Next →
          </button>
        </div>
      )}
    </div>
  );
}
