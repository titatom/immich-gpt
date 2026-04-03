import React, { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { getBuckets, createBucket, updateBucket, deleteBucket, getAlbums } from "../services/api";
import type { Bucket } from "../types";
import { Plus, Trash2, Edit2 } from "lucide-react";

const MAPPING_MODES = ["virtual", "immich_album", "parent_group"] as const;

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

  return (
    <div style={{
      background: "#0f172a",
      border: "1px solid #334155",
      borderRadius: 12,
      padding: 24,
      marginBottom: 16,
    }}>
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16, marginBottom: 16 }}>
        <div>
          <label style={{ fontSize: 12, color: "#64748b", display: "block", marginBottom: 4 }}>Name *</label>
          <input
            value={form.name}
            onChange={(e) => set("name", e.target.value)}
            style={{ width: "100%", ...inputStyle }}
          />
        </div>
        <div>
          <label style={{ fontSize: 12, color: "#64748b", display: "block", marginBottom: 4 }}>Priority</label>
          <input
            type="number"
            value={form.priority}
            onChange={(e) => set("priority", parseInt(e.target.value) || 100)}
            style={{ width: "100%", ...inputStyle }}
          />
        </div>
      </div>

      <div style={{ marginBottom: 16 }}>
        <label style={{ fontSize: 12, color: "#64748b", display: "block", marginBottom: 4 }}>Description</label>
        <input
          value={form.description}
          onChange={(e) => set("description", e.target.value)}
          style={{ width: "100%", ...inputStyle }}
        />
      </div>

      <div style={{ marginBottom: 16 }}>
        <label style={{ fontSize: 12, color: "#64748b", display: "block", marginBottom: 4 }}>Classification Prompt</label>
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
          <label style={{ fontSize: 12, color: "#64748b", display: "block", marginBottom: 4 }}>Mapping Mode</label>
          <select
            value={form.mapping_mode}
            onChange={(e) => set("mapping_mode", e.target.value)}
            style={{ width: "100%", ...inputStyle }}
          >
            {MAPPING_MODES.map((m) => <option key={m} value={m}>{m}</option>)}
          </select>
        </div>

        {form.mapping_mode === "immich_album" && (
          <div>
            <label style={{ fontSize: 12, color: "#64748b", display: "block", marginBottom: 4 }}>Immich Album</label>
            <select
              value={form.immich_album_id}
              onChange={(e) => set("immich_album_id", e.target.value)}
              style={{ width: "100%", ...inputStyle }}
            >
              <option value="">Select album...</option>
              {albums.map((a) => <option key={a.id} value={a.id}>{a.albumName}</option>)}
            </select>
          </div>
        )}

        <div>
          <label style={{ fontSize: 12, color: "#64748b", display: "block", marginBottom: 4 }}>Min Confidence</label>
          <input
            type="number"
            min="0" max="1" step="0.05"
            value={form.confidence_threshold ?? ""}
            onChange={(e) => set("confidence_threshold", e.target.value ? parseFloat(e.target.value) : undefined)}
            style={{ width: "100%", ...inputStyle }}
            placeholder="e.g. 0.8"
          />
        </div>
      </div>

      <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 16 }}>
        <label style={{ display: "flex", alignItems: "center", gap: 8, cursor: "pointer" }}>
          <input
            type="checkbox"
            checked={form.enabled}
            onChange={(e) => set("enabled", e.target.checked)}
          />
          <span style={{ fontSize: 13, color: "#94a3b8" }}>Enabled</span>
        </label>
      </div>

      <div style={{ display: "flex", gap: 8 }}>
        <button
          onClick={() => onSave(form)}
          disabled={!form.name || loading}
          style={{
            padding: "8px 20px", borderRadius: 8, border: "none",
            background: "#1e40af", color: "white", fontSize: 13,
            fontWeight: 600, cursor: !form.name || loading ? "not-allowed" : "pointer",
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

const inputStyle: React.CSSProperties = {
  background: "#1e293b",
  border: "1px solid #334155",
  borderRadius: 8,
  color: "#f1f5f9",
  fontSize: 13,
  padding: "8px 12px",
  outline: "none",
};

export default function Buckets() {
  const qc = useQueryClient();
  const [showCreate, setShowCreate] = useState(false);
  const [editId, setEditId] = useState<string | null>(null);

  const { data: buckets = [] } = useQuery({ queryKey: ["buckets"], queryFn: getBuckets });
  const { data: albums = [] } = useQuery({ queryKey: ["albums"], queryFn: getAlbums });

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
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 24 }}>
        <div>
          <h1 style={{ fontSize: 24, fontWeight: 700, color: "#f1f5f9", margin: 0 }}>Buckets</h1>
          <p style={{ fontSize: 14, color: "#64748b", margin: "4px 0 0" }}>
            AI classification categories
          </p>
        </div>
        <button
          onClick={() => setShowCreate(true)}
          style={{
            display: "flex", alignItems: "center", gap: 8,
            padding: "9px 18px", borderRadius: 8, border: "none",
            background: "#1e40af", color: "white", fontSize: 13,
            fontWeight: 600, cursor: "pointer",
          }}
        >
          <Plus size={15} /> New Bucket
        </button>
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
        {sortedBuckets.map((bucket) => (
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
                borderRadius: 10,
                padding: "14px 18px",
                opacity: bucket.enabled ? 1 : 0.5,
              }}>
                <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
                  <div style={{
                    width: 32, height: 32, borderRadius: 8,
                    background: "#0f172a",
                    display: "flex", alignItems: "center", justifyContent: "center",
                    fontSize: 13, fontWeight: 700, color: "#38bdf8",
                  }}>
                    {bucket.priority}
                  </div>

                  <div style={{ flex: 1 }}>
                    <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                      <span style={{ fontSize: 14, fontWeight: 600, color: "#f1f5f9" }}>{bucket.name}</span>
                      {!bucket.enabled && (
                        <span style={{ fontSize: 11, color: "#475569", background: "#1e293b", border: "1px solid #334155", borderRadius: 4, padding: "1px 6px" }}>
                          Disabled
                        </span>
                      )}
                      {bucket.mapping_mode !== "virtual" && (
                        <span style={{ fontSize: 11, color: "#38bdf8", background: "rgba(56,189,248,0.1)", borderRadius: 4, padding: "1px 6px" }}>
                          {bucket.mapping_mode}
                        </span>
                      )}
                    </div>
                    {bucket.description && (
                      <div style={{ fontSize: 12, color: "#64748b", marginTop: 2 }}>{bucket.description}</div>
                    )}
                  </div>

                  <div style={{ display: "flex", gap: 6 }}>
                    <button
                      onClick={() => setEditId(bucket.id)}
                      style={{ padding: "6px 10px", borderRadius: 6, border: "1px solid #334155", background: "transparent", color: "#64748b", cursor: "pointer" }}
                    >
                      <Edit2 size={13} />
                    </button>
                    <button
                      onClick={() => {
                        if (confirm(`Delete bucket "${bucket.name}"?`)) deleteMut.mutate(bucket.id);
                      }}
                      style={{ padding: "6px 10px", borderRadius: 6, border: "1px solid #334155", background: "transparent", color: "#ef4444", cursor: "pointer" }}
                    >
                      <Trash2 size={13} />
                    </button>
                  </div>
                </div>
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
