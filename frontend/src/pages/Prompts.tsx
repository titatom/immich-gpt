import React, { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { getPrompts, createPrompt, updatePrompt, deletePrompt, getBuckets } from "../services/api";
import type { PromptTemplate } from "../types";
import { Plus, Edit2, Trash2, ToggleLeft, ToggleRight } from "lucide-react";

const PROMPT_TYPES = [
  { value: "global_classification", label: "Global Classification" },
  { value: "bucket_classification", label: "Bucket Classification" },
  { value: "description_generation", label: "Description Generation" },
  { value: "tags_generation", label: "Tags Generation" },
  { value: "review_guidance", label: "Review Guidance" },
];

const inputStyle: React.CSSProperties = {
  background: "#1e293b",
  border: "1px solid #334155",
  borderRadius: 8,
  color: "#f1f5f9",
  fontSize: 13,
  padding: "8px 12px",
  outline: "none",
  width: "100%",
};

interface PromptFormProps {
  initial?: Partial<PromptTemplate>;
  buckets: Array<{ id: string; name: string }>;
  onSave: (data: Partial<PromptTemplate>) => void;
  onCancel: () => void;
  loading?: boolean;
}

function PromptForm({ initial, buckets, onSave, onCancel, loading }: PromptFormProps) {
  const [form, setForm] = useState<Partial<PromptTemplate>>({
    prompt_type: initial?.prompt_type ?? "global_classification",
    name: initial?.name ?? "",
    content: initial?.content ?? "",
    enabled: initial?.enabled ?? true,
    bucket_id: initial?.bucket_id,
  });

  const set = (k: keyof PromptTemplate, v: any) => setForm((f) => ({ ...f, [k]: v }));

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
          <label style={{ fontSize: 12, color: "#64748b", display: "block", marginBottom: 4 }}>Type</label>
          <select
            value={form.prompt_type}
            onChange={(e) => set("prompt_type", e.target.value)}
            style={inputStyle}
          >
            {PROMPT_TYPES.map((t) => <option key={t.value} value={t.value}>{t.label}</option>)}
          </select>
        </div>
        <div>
          <label style={{ fontSize: 12, color: "#64748b", display: "block", marginBottom: 4 }}>Name</label>
          <input value={form.name} onChange={(e) => set("name", e.target.value)} style={inputStyle} />
        </div>
      </div>

      {form.prompt_type === "bucket_classification" && (
        <div style={{ marginBottom: 16 }}>
          <label style={{ fontSize: 12, color: "#64748b", display: "block", marginBottom: 4 }}>Bucket</label>
          <select
            value={form.bucket_id || ""}
            onChange={(e) => set("bucket_id", e.target.value || undefined)}
            style={inputStyle}
          >
            <option value="">Select bucket...</option>
            {buckets.map((b) => <option key={b.id} value={b.id}>{b.name}</option>)}
          </select>
        </div>
      )}

      <div style={{ marginBottom: 16 }}>
        <label style={{ fontSize: 12, color: "#64748b", display: "block", marginBottom: 4 }}>
          Prompt Content
          <span style={{ marginLeft: 8, fontSize: 11, color: "#475569" }}>v{(initial?.version || 0) + 1}</span>
        </label>
        <textarea
          value={form.content}
          onChange={(e) => set("content", e.target.value)}
          rows={6}
          style={{ ...inputStyle, resize: "vertical", lineHeight: 1.6 }}
          placeholder="Write your prompt here..."
        />
      </div>

      <div style={{ display: "flex", gap: 8 }}>
        <button
          onClick={() => onSave(form)}
          disabled={!form.name || !form.content || loading}
          style={{
            padding: "8px 20px", borderRadius: 8, border: "none",
            background: "#1e40af", color: "white", fontSize: 13,
            fontWeight: 600, cursor: "pointer",
          }}
        >
          {loading ? "Saving..." : "Save Prompt"}
        </button>
        <button onClick={onCancel} style={{ padding: "8px 16px", borderRadius: 8, border: "1px solid #334155", background: "transparent", color: "#64748b", fontSize: 13, cursor: "pointer" }}>
          Cancel
        </button>
      </div>
    </div>
  );
}

export default function Prompts() {
  const qc = useQueryClient();
  const [showCreate, setShowCreate] = useState(false);
  const [editId, setEditId] = useState<string | null>(null);
  const [typeFilter, setTypeFilter] = useState("");

  const { data: prompts = [] } = useQuery({ queryKey: ["prompts", typeFilter], queryFn: () => getPrompts(typeFilter ? { prompt_type: typeFilter } : undefined) });
  const { data: buckets = [] } = useQuery({ queryKey: ["buckets"], queryFn: getBuckets });

  const createMut = useMutation({
    mutationFn: createPrompt,
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["prompts"] }); setShowCreate(false); },
  });

  const updateMut = useMutation({
    mutationFn: ({ id, data }: { id: string; data: Partial<PromptTemplate> }) => updatePrompt(id, data),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["prompts"] }); setEditId(null); },
  });

  const deleteMut = useMutation({
    mutationFn: deletePrompt,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["prompts"] }),
  });

  const toggleMut = useMutation({
    mutationFn: ({ id, enabled }: { id: string; enabled: boolean }) => updatePrompt(id, { enabled }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["prompts"] }),
  });

  const typeLabel = (t: string) => PROMPT_TYPES.find((p) => p.value === t)?.label || t;

  return (
    <div style={{ padding: "32px 40px", maxWidth: 860 }}>
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 24 }}>
        <div>
          <h1 style={{ fontSize: 24, fontWeight: 700, color: "#f1f5f9", margin: 0 }}>Prompts</h1>
          <p style={{ fontSize: 14, color: "#64748b", margin: "4px 0 0" }}>
            AI prompt templates — first-class settings
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
          <Plus size={15} /> New Prompt
        </button>
      </div>

      {/* Filter */}
      <div style={{ marginBottom: 20 }}>
        <select
          value={typeFilter}
          onChange={(e) => setTypeFilter(e.target.value)}
          style={{
            background: "#1e293b",
            border: "1px solid #334155",
            color: "#94a3b8",
            borderRadius: 8,
            padding: "7px 12px",
            fontSize: 13,
          }}
        >
          <option value="">All types</option>
          {PROMPT_TYPES.map((t) => <option key={t.value} value={t.value}>{t.label}</option>)}
        </select>
      </div>

      {showCreate && (
        <PromptForm
          buckets={buckets}
          onSave={(data) => createMut.mutate(data)}
          onCancel={() => setShowCreate(false)}
          loading={createMut.isPending}
        />
      )}

      <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
        {prompts.map((prompt) => (
          <div key={prompt.id}>
            {editId === prompt.id ? (
              <PromptForm
                initial={prompt}
                buckets={buckets}
                onSave={(data) => updateMut.mutate({ id: prompt.id, data })}
                onCancel={() => setEditId(null)}
                loading={updateMut.isPending}
              />
            ) : (
              <div style={{
                background: "#1e293b",
                border: "1px solid #334155",
                borderRadius: 10,
                padding: "14px 18px",
                opacity: prompt.enabled ? 1 : 0.5,
              }}>
                <div style={{ display: "flex", alignItems: "flex-start", gap: 12 }}>
                  <div style={{ flex: 1 }}>
                    <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 6, flexWrap: "wrap" }}>
                      <span style={{ fontSize: 14, fontWeight: 600, color: "#f1f5f9" }}>{prompt.name}</span>
                      <span style={{
                        fontSize: 11, color: "#a78bfa",
                        background: "rgba(167,139,250,0.1)",
                        border: "1px solid rgba(167,139,250,0.2)",
                        borderRadius: 4, padding: "1px 6px",
                      }}>
                        {typeLabel(prompt.prompt_type)}
                      </span>
                      <span style={{ fontSize: 11, color: "#475569" }}>v{prompt.version}</span>
                      {!prompt.enabled && (
                        <span style={{ fontSize: 11, color: "#475569", background: "#0f172a", border: "1px solid #334155", borderRadius: 4, padding: "1px 6px" }}>
                          Disabled
                        </span>
                      )}
                    </div>
                    <div style={{
                      fontSize: 12, color: "#64748b",
                      background: "#0f172a", borderRadius: 6,
                      padding: "8px 12px",
                      lineHeight: 1.6,
                      maxHeight: 80,
                      overflow: "hidden",
                      textOverflow: "ellipsis",
                    }}>
                      {prompt.content}
                    </div>
                  </div>

                  <div style={{ display: "flex", gap: 6, flexShrink: 0 }}>
                    <button
                      onClick={() => toggleMut.mutate({ id: prompt.id, enabled: !prompt.enabled })}
                      style={{ padding: "6px 10px", borderRadius: 6, border: "1px solid #334155", background: "transparent", color: "#64748b", cursor: "pointer" }}
                      title={prompt.enabled ? "Disable" : "Enable"}
                    >
                      {prompt.enabled ? <ToggleRight size={14} color="#22c55e" /> : <ToggleLeft size={14} />}
                    </button>
                    <button
                      onClick={() => setEditId(prompt.id)}
                      style={{ padding: "6px 10px", borderRadius: 6, border: "1px solid #334155", background: "transparent", color: "#64748b", cursor: "pointer" }}
                    >
                      <Edit2 size={13} />
                    </button>
                    <button
                      onClick={() => {
                        if (confirm(`Delete prompt "${prompt.name}"?`)) deleteMut.mutate(prompt.id);
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
