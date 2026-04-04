import React, { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { getBuckets, createBucket, updateBucket, deleteBucket, getAlbums, getBucketStats } from "../services/api";
import type { Bucket, BucketStat } from "../types";
import { Plus, Trash2, Edit2, Info } from "lucide-react";

const MAPPING_MODES = ["virtual", "immich_album", "parent_group"] as const;

const MAPPING_MODE_INFO: Record<string, { label: string; description: string }> = {
  virtual: {
    label: "Virtual",
    description:
      "Assets are classified into this bucket in immich-gpt only. No album is created or modified in Immich. Use this when you want AI classification for internal tracking without touching your Immich library.",
  },
  immich_album: {
    label: "Immich Album",
    description:
      "When a classification is approved, the asset is added to the selected Immich album. This writes directly to your Immich library. Choose an album below to map to. Ideal when you want AI to automatically organise photos into existing albums.",
  },
  parent_group: {
    label: "Parent Group",
    description:
      "Assets approved for this bucket are placed in a sub-album under the bucket name as a parent group. Useful for organising into a hierarchy like 'Travel / Paris', 'Travel / Tokyo'. The sub-album name comes from the AI suggestion or the review override.",
  },
};

function Tooltip({ text }: { text: string }) {
  const [show, setShow] = useState(false);
  return (
    <span style={{ position: "relative", display: "inline-flex", verticalAlign: "middle" }}>
      <Info
        size={13}
        color="#64748b"
        style={{ cursor: "help", marginLeft: 4 }}
        onMouseEnter={() => setShow(true)}
        onMouseLeave={() => setShow(false)}
      />
      {show && (
        <span style={{
          position: "absolute",
          bottom: "calc(100% + 6px)",
          left: "50%",
          transform: "translateX(-50%)",
          background: "#1e293b",
          border: "1px solid #334155",
          borderRadius: 8,
          padding: "10px 14px",
          fontSize: 12,
          color: "#cbd5e1",
          lineHeight: 1.5,
          width: 280,
          zIndex: 100,
          whiteSpace: "normal",
          pointerEvents: "none",
          boxShadow: "0 4px 20px rgba(0,0,0,0.4)",
        }}>
          {text}
        </span>
      )}
    </span>
  );
}

const inputStyle: React.CSSProperties = {
  background: "#1e293b", border: "1px solid #334155",
  borderRadius: 8, color: "#f1f5f9", fontSize: 13,
  padding: "8px 12px", outline: "none",
};

interface BucketFormProps {
  initial?: Partial<Bucket>;
  albums: Array<{ id: string; albumName: string }>;
  onSave: (data: Partial<Bucket>) => void;
  onCancel: () => void;
  loading?: boolean;
}

function BucketForm({ initial, albums, onSave, onCancel, loading }: BucketFormProps) {
  const [form, setForm] = useState<Partial<Bucket>>({
    name: initial?.name ?? "",
    description: initial?.description ?? "",
    enabled: initial?.enabled ?? true,
    priority: initial?.priority ?? 100,
    mapping_mode: initial?.mapping_mode ?? "virtual",
    immich_album_id: initial?.immich_album_id ?? "",
    classification_prompt: initial?.classification_prompt ?? "",
    confidence_threshold: initial?.confidence_threshold,
  });

  const set = (k: keyof Bucket, v: Bucket[keyof Bucket]) => setForm((f) => ({ ...f, [k]: v }));

  const modeInfo = MAPPING_MODE_INFO[form.mapping_mode ?? "virtual"];

  return (
    <div style={{ background: "#0f172a", border: "1px solid #334155", borderRadius: 12, padding: 24, marginBottom: 16 }}>
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16, marginBottom: 16 }}>
        <div>
          <label style={{ fontSize: 12, color: "#64748b", display: "block", marginBottom: 4 }}>Name *</label>
          <input value={form.name} onChange={(e) => set("name", e.target.value)} style={{ width: "100%", ...inputStyle }} />
        </div>
        <div>
          <label style={{ fontSize: 12, color: "#64748b", display: "block", marginBottom: 4 }}>
            Priority
            <Tooltip text="Lower numbers are checked first during classification. Set priority to control the order in which buckets compete for an asset." />
          </label>
          <input type="number" value={form.priority} onChange={(e) => set("priority", parseInt(e.target.value) || 100)} style={{ width: "100%", ...inputStyle }} />
        </div>
      </div>

      <div style={{ marginBottom: 16 }}>
        <label style={{ fontSize: 12, color: "#64748b", display: "block", marginBottom: 4 }}>Description</label>
        <input value={form.description} onChange={(e) => set("description", e.target.value)} style={{ width: "100%", ...inputStyle }} />
      </div>

      <div style={{ marginBottom: 16 }}>
        <label style={{ fontSize: 12, color: "#64748b", display: "block", marginBottom: 4 }}>
          Classification Prompt
          <Tooltip text="Describe what kind of assets belong in this bucket. The AI uses this to decide whether each asset matches. Be specific and include examples of what to include and exclude." />
        </label>
        <textarea
          value={form.classification_prompt}
          onChange={(e) => set("classification_prompt", e.target.value)}
          rows={4}
          style={{ width: "100%", ...inputStyle, resize: "vertical" }}
          placeholder="Describe what belongs in this bucket..."
        />
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 16, marginBottom: 16 }}>
        <div>
          <label style={{ fontSize: 12, color: "#64748b", display: "block", marginBottom: 4 }}>
            Mapping Mode
            <Tooltip text="Controls what happens after you approve a classification in the review queue." />
          </label>
          <select value={form.mapping_mode} onChange={(e) => set("mapping_mode", e.target.value)} style={{ width: "100%", ...inputStyle }}>
            {MAPPING_MODES.map((m) => <option key={m} value={m}>{MAPPING_MODE_INFO[m].label}</option>)}
          </select>
        </div>

        {form.mapping_mode === "immich_album" && (
          <div>
            <label style={{ fontSize: 12, color: "#64748b", display: "block", marginBottom: 4 }}>Immich Album</label>
            <select value={form.immich_album_id} onChange={(e) => set("immich_album_id", e.target.value)} style={{ width: "100%", ...inputStyle }}>
              <option value="">Select album...</option>
              {albums.map((a) => <option key={a.id} value={a.id}>{a.albumName}</option>)}
            </select>
          </div>
        )}

        <div>
          <label style={{ fontSize: 12, color: "#64748b", display: "block", marginBottom: 4 }}>
            Min Confidence
            <Tooltip text="AI classifications below this score will not be surfaced for review. Values between 0 and 1. Leave empty to review everything." />
          </label>
          <input
            type="number" min="0" max="1" step="0.05"
            value={form.confidence_threshold ?? ""}
            onChange={(e) => set("confidence_threshold", e.target.value ? parseFloat(e.target.value) : undefined)}
            style={{ width: "100%", ...inputStyle }} placeholder="e.g. 0.8"
          />
        </div>
      </div>

      {/* Mapping mode explanation box */}
      <div style={{
        background: "#0f172a", border: "1px solid #1e3a5f",
        borderRadius: 8, padding: "10px 14px", marginBottom: 16,
        fontSize: 12, color: "#94a3b8", lineHeight: 1.6,
      }}>
        <strong style={{ color: "#38bdf8" }}>{modeInfo.label}:</strong> {modeInfo.description}
      </div>

      <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 16 }}>
        <label style={{ display: "flex", alignItems: "center", gap: 8, cursor: "pointer" }}>
          <input type="checkbox" checked={form.enabled} onChange={(e) => set("enabled", e.target.checked)} />
          <span style={{ fontSize: 13, color: "#94a3b8" }}>Enabled</span>
        </label>
      </div>

      <div style={{ display: "flex", gap: 8 }}>
        <button
          onClick={() => onSave(form)}
          disabled={!form.name || loading}
          style={{
            padding: "8px 20px", borderRadius: 8, border: "none",
            background: "#1e40af", color: "white", fontSize: 13, fontWeight: 600,
            cursor: !form.name || loading ? "not-allowed" : "pointer",
            opacity: !form.name || loading ? 0.6 : 1,
          }}
        >
          {loading ? "Saving..." : "Save Bucket"}
        </button>
        <button onClick={onCancel} style={{ padding: "8px 16px", borderRadius: 8, border: "1px solid #334155", background: "transparent", color: "#64748b", fontSize: 13, cursor: "pointer" }}>
          Cancel
        </button>
      </div>
    </div>
  );
}

export default function Buckets() {
  const qc = useQueryClient();
  const [showCreate, setShowCreate] = useState(false);
  const [editId, setEditId] = useState<string | null>(null);

  const { data: buckets = [] } = useQuery({ queryKey: ["buckets"], queryFn: getBuckets });
  const { data: albums = [] } = useQuery({ queryKey: ["albums"], queryFn: getAlbums });
  const { data: stats = [] } = useQuery<BucketStat[]>({ queryKey: ["bucket-stats"], queryFn: getBucketStats });

  const statsByName: Record<string, BucketStat> = {};
  stats.forEach((s) => { statsByName[s.bucket_name] = s; });

  const createMut = useMutation({
    mutationFn: createBucket,
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["buckets"] }); setShowCreate(false); },
  });

  const updateMut = useMutation({
    mutationFn: ({ id, data }: { id: string; data: Partial<Bucket> }) => updateBucket(id, data),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["buckets"] }); setEditId(null); },
  });

  const deleteMut = useMutation({
    mutationFn: deleteBucket,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["buckets"] }),
  });

  const sortedBuckets = [...buckets].sort((a, b) => a.priority - b.priority);

  return (
    <div style={{ padding: "32px 40px", maxWidth: 860 }}>
      {/* Header */}
      <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", marginBottom: 20 }}>
        <div>
          <h1 style={{ fontSize: 24, fontWeight: 700, color: "#f1f5f9", margin: 0 }}>Buckets</h1>
          <p style={{ fontSize: 14, color: "#64748b", margin: "4px 0 0" }}>AI classification categories</p>
        </div>
        <button
          onClick={() => setShowCreate(true)}
          style={{
            display: "flex", alignItems: "center", gap: 8,
            padding: "9px 18px", borderRadius: 8, border: "none",
            background: "#1e40af", color: "white", fontSize: 13, fontWeight: 600, cursor: "pointer",
          }}
        >
          <Plus size={15} /> New Bucket
        </button>
      </div>

      {/* Intro paragraph */}
      <div style={{
        background: "#1e293b", border: "1px solid #334155", borderRadius: 10,
        padding: "14px 18px", marginBottom: 24, fontSize: 13, color: "#94a3b8", lineHeight: 1.7,
      }}>
        <strong style={{ color: "#f1f5f9" }}>What are buckets?</strong>{" "}
        Buckets are classification categories that the AI uses to sort your photos. Each bucket has a prompt
        that describes what belongs in it — for example, "family portraits", "landscapes", or "travel". When
        the AI classifies an asset, it scores each bucket and suggests the best match. You review and approve
        (or reject) those suggestions. On approval, the asset is mapped to an Immich album, placed in a
        sub-album group, or just tracked virtually — depending on the bucket's <em>mapping mode</em>.
      </div>

      {showCreate && (
        <BucketForm
          albums={albums}
          onSave={(data) => createMut.mutate(data)}
          onCancel={() => setShowCreate(false)}
          loading={createMut.isPending}
        />
      )}

      <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
        {sortedBuckets.map((bucket) => {
          const stat = statsByName[bucket.name];
          const approved = stat?.by_status["approved"] ?? 0;
          const pending = stat?.by_status["pending_review"] ?? 0;
          const total = stat?.total ?? 0;

          return (
            <div key={bucket.id}>
              {editId === bucket.id ? (
                <BucketForm
                  initial={bucket}
                  albums={albums}
                  onSave={(data) => updateMut.mutate({ id: bucket.id, data })}
                  onCancel={() => setEditId(null)}
                  loading={updateMut.isPending}
                />
              ) : (
                <div style={{
                  background: "#1e293b",
                  border: `1px solid ${bucket.enabled ? "#334155" : "#1e293b"}`,
                  borderRadius: 10, padding: "14px 18px",
                  opacity: bucket.enabled ? 1 : 0.5,
                }}>
                  <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
                    {/* Priority badge */}
                    <div style={{
                      width: 32, height: 32, borderRadius: 8, background: "#0f172a",
                      display: "flex", alignItems: "center", justifyContent: "center",
                      fontSize: 13, fontWeight: 700, color: "#38bdf8",
                    }}>
                      {bucket.priority}
                    </div>

                    {/* Name + tags */}
                    <div style={{ flex: 1 }}>
                      <div style={{ display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap" }}>
                        <span style={{ fontSize: 14, fontWeight: 600, color: "#f1f5f9" }}>{bucket.name}</span>
                        {!bucket.enabled && (
                          <span style={{ fontSize: 11, color: "#475569", border: "1px solid #334155", borderRadius: 4, padding: "1px 6px" }}>Disabled</span>
                        )}
                        {bucket.mapping_mode !== "virtual" && (
                          <span style={{ fontSize: 11, color: "#38bdf8", background: "rgba(56,189,248,0.1)", borderRadius: 4, padding: "1px 6px" }}>
                            {MAPPING_MODE_INFO[bucket.mapping_mode]?.label ?? bucket.mapping_mode}
                          </span>
                        )}
                      </div>
                      {bucket.description && (
                        <div style={{ fontSize: 12, color: "#64748b", marginTop: 2 }}>{bucket.description}</div>
                      )}
                    </div>

                    {/* Stats */}
                    {total > 0 && (
                      <div style={{ display: "flex", gap: 12, fontSize: 12, color: "#64748b", alignItems: "center" }}>
                        <span title="Total classified">{total} total</span>
                        {approved > 0 && <span style={{ color: "#22c55e" }}>✓ {approved}</span>}
                        {pending > 0 && <span style={{ color: "#f59e0b" }}>⏳ {pending}</span>}
                      </div>
                    )}

                    {/* Actions */}
                    <div style={{ display: "flex", gap: 6 }}>
                      <button
                        onClick={() => setEditId(bucket.id)}
                        style={{ padding: "6px 10px", borderRadius: 6, border: "1px solid #334155", background: "transparent", color: "#64748b", cursor: "pointer" }}
                        title="Edit"
                      >
                        <Edit2 size={13} />
                      </button>
                      <button
                        onClick={() => {
                          if (confirm(`Delete bucket "${bucket.name}"? This cannot be undone.`)) deleteMut.mutate(bucket.id);
                        }}
                        style={{ padding: "6px 10px", borderRadius: 6, border: "1px solid #334155", background: "transparent", color: "#ef4444", cursor: "pointer" }}
                        title="Delete"
                      >
                        <Trash2 size={13} />
                      </button>
                    </div>
                  </div>
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
