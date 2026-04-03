import React, { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  getReviewQueue,
  getReviewCount,
  getBuckets,
  approveAsset,
  rejectAsset,
  bulkReview,
  getThumbnailUrl,
} from "../services/api";
import type { ReviewItem, Bucket } from "../types";
import Thumbnail from "../components/Thumbnail";
import ConfidenceBadge from "../components/ConfidenceBadge";
import TagList from "../components/TagList";
import { CheckCircle, XCircle, ChevronDown, ChevronUp, Maximize2, Edit2 } from "lucide-react";

interface ReviewCardProps {
  item: ReviewItem;
  buckets: Bucket[];
  onApprove: (assetId: string, data: any) => void;
  onReject: (assetId: string) => void;
}

function ReviewCard({ item, buckets, onApprove, onReject }: ReviewCardProps) {
  const [expanded, setExpanded] = useState(false);
  const [editDescription, setEditDescription] = useState(item.description_suggestion || "");
  const [editTags, setEditTags] = useState<string[]>(item.tags_suggestion || []);
  const [selectedBucketId, setSelectedBucketId] = useState(item.suggested_bucket_id || "");
  const [lightbox, setLightbox] = useState(false);

  const handleApprove = () => {
    const bucket = buckets.find((b) => b.id === selectedBucketId);
    onApprove(item.asset_id, {
      approved_bucket_id: selectedBucketId || item.suggested_bucket_id,
      approved_bucket_name: bucket?.name || item.suggested_bucket_name,
      approved_description: editDescription,
      approved_tags: editTags,
      approved_subalbum: item.subalbum_suggestion,
      subalbum_approved: false,
      trigger_writeback: true,
    });
  };

  return (
    <div style={{
      background: "#1e293b",
      border: "1px solid #334155",
      borderRadius: 12,
      overflow: "hidden",
      marginBottom: 12,
    }}>
      {/* Header row */}
      <div style={{ display: "flex", gap: 16, padding: 16, alignItems: "flex-start" }}>
        {/* Thumbnail */}
        <Thumbnail
          assetId={item.asset_id}
          size={88}
          onClick={() => setLightbox(true)}
        />

        {/* Info */}
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap", marginBottom: 4 }}>
            <span style={{ fontSize: 13, fontWeight: 600, color: "#f1f5f9", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
              {item.original_filename || item.immich_id}
            </span>
            {item.file_created_at && (
              <span style={{ fontSize: 11, color: "#475569" }}>
                {new Date(item.file_created_at).toLocaleDateString()}
              </span>
            )}
            {item.city && <span style={{ fontSize: 11, color: "#475569" }}>{item.city}</span>}
          </div>

          {/* Bucket suggestion */}
          <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 8, flexWrap: "wrap" }}>
            <span style={{ fontSize: 11, color: "#64748b" }}>Bucket:</span>
            <select
              value={selectedBucketId}
              onChange={(e) => setSelectedBucketId(e.target.value)}
              style={{
                background: "#0f172a",
                border: "1px solid #334155",
                borderRadius: 6,
                color: "#38bdf8",
                fontSize: 12,
                fontWeight: 600,
                padding: "2px 8px",
                cursor: "pointer",
              }}
            >
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
              fontSize: 12,
              color: "#94a3b8",
              background: "#0f172a",
              borderRadius: 6,
              padding: "6px 10px",
              marginBottom: 8,
              lineHeight: 1.5,
            }}>
              {item.explanation}
            </div>
          )}

          {/* Tags preview */}
          <TagList tags={editTags} maxVisible={5} />
        </div>

        {/* Actions */}
        <div style={{ display: "flex", flexDirection: "column", gap: 6, flexShrink: 0 }}>
          <button
            onClick={handleApprove}
            style={{
              display: "flex", alignItems: "center", gap: 6,
              padding: "8px 14px", borderRadius: 8, border: "none",
              background: "#16a34a", color: "white", fontSize: 13,
              fontWeight: 600, cursor: "pointer",
            }}
          >
            <CheckCircle size={14} /> Approve
          </button>
          <button
            onClick={() => onReject(item.asset_id)}
            style={{
              display: "flex", alignItems: "center", gap: 6,
              padding: "8px 14px", borderRadius: 8, border: "1px solid #334155",
              background: "transparent", color: "#94a3b8", fontSize: 13,
              fontWeight: 500, cursor: "pointer",
            }}
          >
            <XCircle size={14} /> Reject
          </button>
          <button
            onClick={() => setExpanded(!expanded)}
            style={{
              display: "flex", alignItems: "center", gap: 6,
              padding: "6px 14px", borderRadius: 8, border: "1px solid #334155",
              background: "transparent", color: "#64748b", fontSize: 12,
              cursor: "pointer",
            }}
          >
            <Edit2 size={12} />
            {expanded ? "Less" : "Edit"}
            {expanded ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
          </button>
        </div>
      </div>

      {/* Expanded edit section */}
      {expanded && (
        <div style={{ padding: "0 16px 16px", borderTop: "1px solid #334155" }}>
          <div style={{ paddingTop: 16, display: "flex", flexDirection: "column", gap: 12 }}>
            {/* Description edit */}
            <div>
              <label style={{ fontSize: 12, color: "#64748b", fontWeight: 500, display: "block", marginBottom: 4 }}>
                Description
              </label>
              <textarea
                value={editDescription}
                onChange={(e) => setEditDescription(e.target.value)}
                rows={3}
                style={{
                  width: "100%",
                  background: "#0f172a",
                  border: "1px solid #334155",
                  borderRadius: 8,
                  color: "#f1f5f9",
                  fontSize: 13,
                  padding: "8px 12px",
                  resize: "vertical",
                  outline: "none",
                  lineHeight: 1.5,
                }}
              />
            </div>

            {/* Tags edit */}
            <div>
              <label style={{ fontSize: 12, color: "#64748b", fontWeight: 500, display: "block", marginBottom: 4 }}>
                Tags
              </label>
              <TagList tags={editTags} editable onChange={setEditTags} />
            </div>

            {/* Sub-album suggestion */}
            {item.subalbum_suggestion && (
              <div style={{ fontSize: 12, color: "#94a3b8" }}>
                Sub-album suggestion: <strong style={{ color: "#38bdf8" }}>{item.subalbum_suggestion}</strong>
              </div>
            )}

            {/* Metadata context */}
            <div style={{ fontSize: 11, color: "#475569", display: "flex", gap: 16, flexWrap: "wrap" }}>
              {item.camera_make && <span>Camera: {item.camera_make} {item.camera_model}</span>}
              {item.city && <span>Location: {item.city}, {item.country}</span>}
              {item.asset_type && <span>Type: {item.asset_type}</span>}
            </div>
          </div>
        </div>
      )}

      {/* Lightbox */}
      {lightbox && (
        <div
          onClick={() => setLightbox(false)}
          style={{
            position: "fixed",
            inset: 0,
            background: "rgba(0,0,0,0.85)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            zIndex: 1000,
            cursor: "pointer",
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

export default function Review() {
  const qc = useQueryClient();
  const [page, setPage] = useState(1);
  const [selectedBucketFilter, setSelectedBucketFilter] = useState("");
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const pageSize = 20;

  const { data: buckets = [] } = useQuery({
    queryKey: ["buckets"],
    queryFn: getBuckets,
  });

  const { data: items = [], isLoading } = useQuery({
    queryKey: ["review-queue", page, selectedBucketFilter],
    queryFn: () => getReviewQueue({
      page,
      page_size: pageSize,
      bucket_id: selectedBucketFilter || undefined,
    }),
    refetchInterval: 15_000,
  });

  const { data: countData } = useQuery<{ count: number }>({
    queryKey: ["review-count"],
    queryFn: () => getReviewCount(),
    refetchInterval: 10_000,
  });

  const approveMutation = useMutation({
    mutationFn: ({ assetId, data }: { assetId: string; data: any }) =>
      approveAsset(assetId, data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["review-queue"] });
      qc.invalidateQueries({ queryKey: ["review-count"] });
    },
  });

  const rejectMutation = useMutation({
    mutationFn: rejectAsset,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["review-queue"] });
      qc.invalidateQueries({ queryKey: ["review-count"] });
    },
  });

  const bulkMutation = useMutation({
    mutationFn: (action: "approve_all" | "reject_all") =>
      bulkReview({ asset_ids: Array.from(selected), action, trigger_writeback: true }),
    onSuccess: () => {
      setSelected(new Set());
      qc.invalidateQueries({ queryKey: ["review-queue"] });
      qc.invalidateQueries({ queryKey: ["review-count"] });
    },
  });

  const toggleSelect = (id: string) => {
    const s = new Set(selected);
    if (s.has(id)) s.delete(id);
    else s.add(id);
    setSelected(s);
  };

  const toggleSelectAll = () => {
    if (selected.size === items.length) setSelected(new Set());
    else setSelected(new Set(items.map((i) => i.asset_id)));
  };

  return (
    <div style={{ padding: "32px 40px", maxWidth: 960 }}>
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 24 }}>
        <div>
          <h1 style={{ fontSize: 24, fontWeight: 700, color: "#f1f5f9", margin: 0 }}>Review Queue</h1>
          <p style={{ fontSize: 14, color: "#64748b", margin: "4px 0 0" }}>
            {countData?.count ?? 0} items pending review
          </p>
        </div>

        <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
          {/* Bucket filter */}
          <select
            value={selectedBucketFilter}
            onChange={(e) => { setSelectedBucketFilter(e.target.value); setPage(1); }}
            style={{
              background: "#1e293b",
              border: "1px solid #334155",
              color: "#94a3b8",
              borderRadius: 8,
              padding: "7px 12px",
              fontSize: 13,
            }}
          >
            <option value="">All buckets</option>
            {buckets.map((b) => (
              <option key={b.id} value={b.id}>{b.name}</option>
            ))}
          </select>
        </div>
      </div>

      {/* Bulk actions */}
      {selected.size > 0 && (
        <div style={{
          display: "flex",
          alignItems: "center",
          gap: 12,
          padding: "10px 16px",
          background: "#1e293b",
          border: "1px solid #334155",
          borderRadius: 8,
          marginBottom: 16,
        }}>
          <span style={{ fontSize: 13, color: "#94a3b8" }}>{selected.size} selected</span>
          <button
            onClick={() => bulkMutation.mutate("approve_all")}
            style={{ padding: "6px 14px", borderRadius: 6, border: "none", background: "#16a34a", color: "white", fontSize: 12, fontWeight: 600, cursor: "pointer" }}
          >
            Approve All
          </button>
          <button
            onClick={() => bulkMutation.mutate("reject_all")}
            style={{ padding: "6px 14px", borderRadius: 6, border: "1px solid #334155", background: "transparent", color: "#94a3b8", fontSize: 12, cursor: "pointer" }}
          >
            Reject All
          </button>
          <button
            onClick={() => setSelected(new Set())}
            style={{ padding: "6px 14px", borderRadius: 6, border: "none", background: "transparent", color: "#64748b", fontSize: 12, cursor: "pointer" }}
          >
            Clear
          </button>
        </div>
      )}

      {/* Select all */}
      {items.length > 0 && (
        <div style={{ marginBottom: 8 }}>
          <button
            onClick={toggleSelectAll}
            style={{
              background: "transparent",
              border: "none",
              color: "#64748b",
              fontSize: 12,
              cursor: "pointer",
              padding: "4px 0",
            }}
          >
            {selected.size === items.length ? "Deselect all" : "Select all on page"}
          </button>
        </div>
      )}

      {isLoading ? (
        <div style={{ color: "#64748b", padding: 32, textAlign: "center" }}>Loading...</div>
      ) : items.length === 0 ? (
        <div style={{
          textAlign: "center",
          padding: 64,
          background: "#1e293b",
          borderRadius: 12,
          border: "1px solid #334155",
        }}>
          <CheckCircle size={40} color="#22c55e" style={{ marginBottom: 16 }} />
          <div style={{ fontSize: 18, fontWeight: 600, color: "#f1f5f9", marginBottom: 8 }}>
            All caught up!
          </div>
          <div style={{ fontSize: 14, color: "#64748b" }}>
            No items pending review. Run AI classification to generate suggestions.
          </div>
        </div>
      ) : (
        items.map((item) => (
          <div key={item.asset_id} style={{ position: "relative" }}>
            {/* Checkbox overlay */}
            <div style={{
              position: "absolute",
              top: 12,
              left: 12,
              zIndex: 1,
            }}>
              <input
                type="checkbox"
                checked={selected.has(item.asset_id)}
                onChange={() => toggleSelect(item.asset_id)}
                style={{ width: 16, height: 16, cursor: "pointer" }}
              />
            </div>
            <ReviewCard
              item={item}
              buckets={buckets}
              onApprove={(assetId, data) => approveMutation.mutate({ assetId, data })}
              onReject={(assetId) => rejectMutation.mutate(assetId)}
            />
          </div>
        ))
      )}

      {/* Pagination */}
      {items.length === pageSize && (
        <div style={{ display: "flex", gap: 8, justifyContent: "center", marginTop: 16 }}>
          <button
            onClick={() => setPage(Math.max(1, page - 1))}
            disabled={page === 1}
            style={{
              padding: "8px 16px", borderRadius: 8, border: "1px solid #334155",
              background: "transparent", color: "#94a3b8", cursor: "pointer",
              opacity: page === 1 ? 0.4 : 1,
            }}
          >
            ← Prev
          </button>
          <span style={{ padding: "8px 16px", color: "#64748b", fontSize: 13 }}>Page {page}</span>
          <button
            onClick={() => setPage(page + 1)}
            style={{
              padding: "8px 16px", borderRadius: 8, border: "1px solid #334155",
              background: "transparent", color: "#94a3b8", cursor: "pointer",
            }}
          >
            Next →
          </button>
        </div>
      )}
    </div>
  );
}
