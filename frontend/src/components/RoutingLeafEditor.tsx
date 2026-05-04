import React, { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  getRoutingPromptPreview,
  listRoutingExamples,
  addRoutingExample,
  deleteRoutingExample,
} from "../services/api";
import type { RoutingNode, PrivacyAction } from "../types";

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

const TAB_DEFS: { key: TabKey; label: string }[] = [
  { key: "general", label: "General" },
  { key: "matching", label: "Matching" },
  { key: "automation", label: "Automation" },
  { key: "privacy", label: "Privacy" },
  { key: "quality", label: "Quality" },
  { key: "metadata", label: "Metadata" },
  { key: "writeback", label: "Writeback" },
  { key: "examples", label: "Examples" },
  { key: "advanced", label: "Advanced AI" },
];

type TabKey =
  | "general"
  | "matching"
  | "automation"
  | "privacy"
  | "quality"
  | "metadata"
  | "writeback"
  | "examples"
  | "advanced";

const PRIVACY_FLAGS: { key: string; label: string }[] = [
  { key: "faces_visible", label: "Faces visible" },
  { key: "children_visible", label: "Children visible" },
  { key: "address_visible", label: "Address visible" },
  { key: "documents_visible", label: "Documents visible" },
  { key: "license_plate_visible", label: "License plate visible" },
  { key: "private_info_visible", label: "Private/sensitive content" },
];

const PRIVACY_ACTIONS: PrivacyAction[] = ["allow", "tag", "review", "reject"];

const PRESETS: Record<string, Partial<RoutingNode>> = {
  conservative: {
    auto_apply_enabled: false,
    auto_apply_threshold: 0.98,
    review_below_threshold: 0.95,
  },
  balanced: {
    auto_apply_enabled: true,
    auto_apply_threshold: 0.95,
    review_below_threshold: 0.85,
  },
  aggressive: {
    auto_apply_enabled: true,
    auto_apply_threshold: 0.85,
    review_below_threshold: 0.7,
  },
  manual: {
    auto_apply_enabled: false,
    auto_apply_threshold: 1.0,
    review_below_threshold: null,
  },
  general_album: {
    destination_type: "immich_album",
    auto_apply_enabled: true,
    auto_apply_threshold: 0.9,
    minimum_quality: "usable",
  },
  high_quality_album: {
    destination_type: "immich_album",
    auto_apply_enabled: true,
    auto_apply_threshold: 0.95,
    minimum_quality: "high",
    allow_blurry: false,
    allow_dark: false,
    allow_screenshot: false,
  },
  trash_candidate: {
    destination_type: "immich_trash",
    auto_apply_enabled: false,
    auto_apply_threshold: 0.98,
  },
  review_only: {
    destination_type: "review_only",
    auto_apply_enabled: false,
  },
};

interface Props {
  node: RoutingNode;
  onSave: (data: Partial<RoutingNode>) => void;
  saving: boolean;
}

export default function RoutingLeafEditor({ node, onSave, saving }: Props) {
  const [tab, setTab] = useState<TabKey>("general");
  // Keyed by node.id at the parent level — re-mounts on selection change,
  // so we initialise from `node` once per mount.
  const [form, setForm] = useState<RoutingNode>(node);

  const set = <K extends keyof RoutingNode>(k: K, v: RoutingNode[K]) =>
    setForm((f) => ({ ...f, [k]: v }));

  const setPrivacy = (flag: string, action: PrivacyAction) => {
    setForm((f) => ({
      ...f,
      privacy_rules: { ...f.privacy_rules, [flag]: action },
    }));
  };

  const applyPreset = (key: string) => {
    const preset = PRESETS[key];
    if (!preset) return;
    setForm((f) => ({ ...f, ...preset }));
  };

  const saveDraft = () => {
    const payload: Partial<RoutingNode> = {
      name: form.name,
      description: form.description,
      enabled: form.enabled,
      priority: form.priority,
      destination_type: form.destination_type,
      immich_album_name: form.immich_album_name,
      create_album_if_missing: form.create_album_if_missing,
      auto_apply_enabled: form.auto_apply_enabled,
      auto_apply_threshold: form.auto_apply_threshold,
      review_below_threshold: form.review_below_threshold,
      exclusive: form.exclusive,
      allow_secondary: form.allow_secondary,
      minimum_quality: form.minimum_quality,
      allow_blurry: form.allow_blurry,
      allow_dark: form.allow_dark,
      allow_screenshot: form.allow_screenshot,
      allow_duplicate: form.allow_duplicate,
      suggest_description: form.suggest_description,
      suggest_tags: form.suggest_tags,
      suggest_location: form.suggest_location,
      suggest_caption: form.suggest_caption,
      write_description: form.write_description,
      write_tags: form.write_tags,
      write_location: form.write_location,
      custom_prompt_enabled: form.custom_prompt_enabled,
      custom_prompt: form.custom_prompt,
      positive_criteria: form.positive_criteria,
      negative_criteria: form.negative_criteria,
      privacy_rules: form.privacy_rules,
    };
    onSave(payload);
  };

  return (
    <div style={{ padding: 20 }}>
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 12 }}>
        <div>
          <div style={{ fontSize: 11, color: "#64748b" }}>{form.path}</div>
          <h2 style={{ fontSize: 18, fontWeight: 700, color: "#f1f5f9", margin: "2px 0 0" }}>
            {form.name}
          </h2>
        </div>
        <button
          onClick={saveDraft}
          disabled={saving}
          style={{
            padding: "8px 18px", borderRadius: 8, border: "none",
            background: "#1e40af", color: "white", fontSize: 13, fontWeight: 600,
            cursor: saving ? "wait" : "pointer", opacity: saving ? 0.6 : 1,
          }}
        >
          {saving ? "Saving…" : "Save"}
        </button>
      </div>

      <div style={{ display: "flex", gap: 4, marginBottom: 14, borderBottom: "1px solid #1e293b" }}>
        {TAB_DEFS.map((t) => (
          <button
            key={t.key}
            onClick={() => setTab(t.key)}
            style={{
              padding: "7px 12px", border: "none", borderRadius: 0,
              background: "transparent",
              color: tab === t.key ? "#38bdf8" : "#94a3b8",
              borderBottom: tab === t.key ? "2px solid #38bdf8" : "2px solid transparent",
              fontSize: 12, fontWeight: 600, cursor: "pointer",
            }}
          >
            {t.label}
          </button>
        ))}
      </div>

      {tab === "general" && (
        <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
          <Field label="Name">
            <input value={form.name} onChange={(e) => set("name", e.target.value)} style={inputStyle} />
          </Field>
          <Field label="Path preview">
            <input value={form.path} disabled style={{ ...inputStyle, opacity: 0.6 }} />
          </Field>
          <Field label="Description">
            <textarea
              rows={3}
              value={form.description ?? ""}
              onChange={(e) => set("description", e.target.value)}
              style={{ ...inputStyle, resize: "vertical" }}
            />
          </Field>
          <Row>
            <Field label="Priority">
              <input
                type="number"
                value={form.priority}
                onChange={(e) => set("priority", parseInt(e.target.value) || 100)}
                style={inputStyle}
              />
            </Field>
            <Toggle
              label="Enabled"
              checked={form.enabled}
              onChange={(v) => set("enabled", v)}
            />
          </Row>
          <Row>
            <Toggle
              label="Exclusive (no secondaries)"
              checked={form.exclusive}
              onChange={(v) => set("exclusive", v)}
            />
            <Toggle
              label="Allow as secondary"
              checked={form.allow_secondary}
              onChange={(v) => set("allow_secondary", v)}
            />
          </Row>
          <Toggle
            label="Is leaf (selectable destination)"
            checked={form.is_leaf}
            onChange={(v) => set("is_leaf", v)}
          />
        </div>
      )}

      {tab === "matching" && (
        <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
          <CriteriaList
            label="What belongs here? (positive criteria)"
            items={form.positive_criteria}
            onChange={(items) => set("positive_criteria", items)}
          />
          <CriteriaList
            label="What does NOT belong here? (negative criteria)"
            items={form.negative_criteria}
            onChange={(items) => set("negative_criteria", items)}
          />
        </div>
      )}

      {tab === "automation" && (
        <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
          <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
            <PresetButton onClick={() => applyPreset("conservative")}>Conservative</PresetButton>
            <PresetButton onClick={() => applyPreset("balanced")}>Balanced</PresetButton>
            <PresetButton onClick={() => applyPreset("aggressive")}>Aggressive</PresetButton>
            <PresetButton onClick={() => applyPreset("manual")}>Manual only</PresetButton>
          </div>
          <Toggle
            label="Auto-apply enabled"
            checked={form.auto_apply_enabled}
            onChange={(v) => set("auto_apply_enabled", v)}
          />
          <Field label="Auto-apply confidence threshold">
            <input
              type="number" min={0} max={1} step={0.01}
              value={form.auto_apply_threshold}
              onChange={(e) => set("auto_apply_threshold", parseFloat(e.target.value) || 0)}
              style={inputStyle}
            />
          </Field>
          <Field label="Require review below confidence">
            <input
              type="number" min={0} max={1} step={0.01}
              value={form.review_below_threshold ?? ""}
              onChange={(e) =>
                set("review_below_threshold", e.target.value ? parseFloat(e.target.value) : null)
              }
              style={inputStyle}
            />
          </Field>
        </div>
      )}

      {tab === "privacy" && (
        <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
          {PRIVACY_FLAGS.map((p) => (
            <div key={p.key} style={{ display: "grid", gridTemplateColumns: "1fr auto", alignItems: "center", gap: 10 }}>
              <div style={{ fontSize: 13, color: "#e2e8f0" }}>{p.label}</div>
              <select
                value={(form.privacy_rules[p.key] ?? "allow") as string}
                onChange={(e) => setPrivacy(p.key, e.target.value as PrivacyAction)}
                style={{ ...inputStyle, width: 140 }}
              >
                {PRIVACY_ACTIONS.map((a) => (
                  <option key={a} value={a}>{a}</option>
                ))}
              </select>
            </div>
          ))}
        </div>
      )}

      {tab === "quality" && (
        <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
          <Field label="Minimum quality">
            <select
              value={form.minimum_quality}
              onChange={(e) => set("minimum_quality", e.target.value as RoutingNode["minimum_quality"])}
              style={inputStyle}
            >
              <option value="any">Any</option>
              <option value="usable">Usable</option>
              <option value="high">High</option>
            </select>
          </Field>
          <Toggle label="Allow blurry" checked={form.allow_blurry} onChange={(v) => set("allow_blurry", v)} />
          <Toggle label="Allow dark" checked={form.allow_dark} onChange={(v) => set("allow_dark", v)} />
          <Toggle label="Allow screenshots" checked={form.allow_screenshot} onChange={(v) => set("allow_screenshot", v)} />
          <Toggle label="Allow duplicates" checked={form.allow_duplicate} onChange={(v) => set("allow_duplicate", v)} />
        </div>
      )}

      {tab === "metadata" && (
        <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
          <Toggle label="Suggest description" checked={form.suggest_description} onChange={(v) => set("suggest_description", v)} />
          <Toggle label="Suggest tags" checked={form.suggest_tags} onChange={(v) => set("suggest_tags", v)} />
          <Toggle label="Suggest location" checked={form.suggest_location} onChange={(v) => set("suggest_location", v)} />
          <Toggle label="Suggest caption" checked={form.suggest_caption} onChange={(v) => set("suggest_caption", v)} />
          <hr style={{ border: 0, borderTop: "1px solid #1e293b" }} />
          <Toggle label="Write description" checked={form.write_description} onChange={(v) => set("write_description", v)} />
          <Toggle label="Write tags" checked={form.write_tags} onChange={(v) => set("write_tags", v)} />
          <Toggle label="Write location" checked={form.write_location} onChange={(v) => set("write_location", v)} />
        </div>
      )}

      {tab === "writeback" && (
        <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
          <Field label="Destination type">
            <select
              value={form.destination_type}
              onChange={(e) => set("destination_type", e.target.value as RoutingNode["destination_type"])}
              style={inputStyle}
            >
              <option value="virtual">Virtual (no Immich action)</option>
              <option value="immich_album">Immich album</option>
              <option value="immich_trash">Immich trash</option>
              <option value="review_only">Review only</option>
            </select>
          </Field>
          {form.destination_type === "immich_album" && (
            <>
              <Field label="Album name">
                <input
                  value={form.immich_album_name ?? ""}
                  onChange={(e) => set("immich_album_name", e.target.value)}
                  style={inputStyle}
                  placeholder={form.path}
                />
              </Field>
              <Toggle
                label="Create album if missing"
                checked={form.create_album_if_missing}
                onChange={(v) => set("create_album_if_missing", v)}
              />
            </>
          )}
          {form.destination_type === "immich_trash" && (
            <div style={{
              padding: "10px 14px", borderRadius: 8,
              background: "rgba(239,68,68,0.06)", border: "1px solid rgba(239,68,68,0.2)",
              color: "#fca5a5", fontSize: 12, lineHeight: 1.6,
            }}>
              This destination can move assets to Immich trash after approval.
              Auto-apply is disabled by default for safety.
            </div>
          )}
        </div>
      )}

      {tab === "examples" && <ExamplesTab nodeId={form.id} />}

      {tab === "advanced" && <AdvancedAITab form={form} setForm={setForm} />}
    </div>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div>
      <label style={{ fontSize: 11, color: "#64748b", display: "block", marginBottom: 4 }}>{label}</label>
      {children}
    </div>
  );
}

function Row({ children }: { children: React.ReactNode }) {
  return <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>{children}</div>;
}

function Toggle({ label, checked, onChange }: { label: string; checked: boolean; onChange: (v: boolean) => void }) {
  return (
    <label style={{ display: "flex", alignItems: "center", gap: 8, cursor: "pointer", fontSize: 13, color: "#e2e8f0" }}>
      <input type="checkbox" checked={!!checked} onChange={(e) => onChange(e.target.checked)} />
      <span>{label}</span>
    </label>
  );
}

function PresetButton({ children, onClick }: { children: React.ReactNode; onClick: () => void }) {
  return (
    <button
      onClick={onClick}
      style={{
        padding: "5px 11px", borderRadius: 6,
        border: "1px solid #334155", background: "#1e293b",
        color: "#cbd5e1", fontSize: 11, cursor: "pointer",
      }}
    >
      {children}
    </button>
  );
}

function CriteriaList({ label, items, onChange }: { label: string; items: string[]; onChange: (v: string[]) => void }) {
  const [draft, setDraft] = useState("");
  const arr = items ?? [];

  const add = () => {
    if (!draft.trim()) return;
    onChange([...arr, draft.trim()]);
    setDraft("");
  };

  const remove = (i: number) => onChange(arr.filter((_, j) => j !== i));

  return (
    <div>
      <label style={{ fontSize: 11, color: "#64748b", display: "block", marginBottom: 4 }}>{label}</label>
      <div style={{ display: "flex", flexDirection: "column", gap: 6, marginBottom: 8 }}>
        {arr.map((c, i) => (
          <div key={i} style={{
            display: "flex", alignItems: "center", gap: 8,
            background: "#1e293b", border: "1px solid #334155",
            borderRadius: 6, padding: "6px 10px",
          }}>
            <span style={{ flex: 1, fontSize: 13, color: "#e2e8f0" }}>{c}</span>
            <button
              onClick={() => remove(i)}
              style={{ background: "transparent", border: "none", color: "#ef4444", cursor: "pointer" }}
            >
              ×
            </button>
          </div>
        ))}
      </div>
      <div style={{ display: "flex", gap: 6 }}>
        <input
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && add()}
          placeholder="Add criterion…"
          style={{ ...inputStyle, flex: 1 }}
        />
        <button
          onClick={add}
          style={{
            padding: "0 14px", borderRadius: 6, border: "none",
            background: "#334155", color: "#f1f5f9", fontSize: 12, cursor: "pointer",
          }}
        >
          Add
        </button>
      </div>
    </div>
  );
}

function ExamplesTab({ nodeId }: { nodeId: string }) {
  const qc = useQueryClient();
  const { data: examples = [] } = useQuery({
    queryKey: ["routing-examples", nodeId],
    queryFn: () => listRoutingExamples(nodeId),
  });

  const [type, setType] = useState<"positive" | "negative">("positive");
  const [note, setNote] = useState("");

  const addMut = useMutation({
    mutationFn: () => addRoutingExample(nodeId, { example_type: type, note }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["routing-examples", nodeId] });
      setNote("");
    },
  });

  const delMut = useMutation({
    mutationFn: (id: string) => deleteRoutingExample(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["routing-examples", nodeId] }),
  });

  const positives = examples.filter((e) => e.example_type === "positive");
  const negatives = examples.filter((e) => e.example_type === "negative");

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
      <div style={{
        display: "flex", gap: 8, alignItems: "center",
        padding: 10, borderRadius: 8, background: "#1e293b", border: "1px solid #334155",
      }}>
        <select
          value={type}
          onChange={(e) => setType(e.target.value as "positive" | "negative")}
          style={{ ...inputStyle, width: 120 }}
        >
          <option value="positive">Positive</option>
          <option value="negative">Negative</option>
        </select>
        <input
          value={note}
          onChange={(e) => setNote(e.target.value)}
          placeholder="Description / filename / note"
          style={{ ...inputStyle, flex: 1 }}
        />
        <button
          onClick={() => addMut.mutate()}
          disabled={!note.trim() || addMut.isPending}
          style={{
            padding: "8px 14px", borderRadius: 6, border: "none",
            background: "#1e40af", color: "white", fontSize: 12, cursor: "pointer",
            opacity: !note.trim() ? 0.5 : 1,
          }}
        >
          Add
        </button>
      </div>

      <ExampleSection title="Positive examples" items={positives} onDelete={(id) => delMut.mutate(id)} />
      <ExampleSection title="Negative examples" items={negatives} onDelete={(id) => delMut.mutate(id)} />
    </div>
  );
}

function ExampleSection({
  title, items, onDelete,
}: { title: string; items: { id: string; note?: string | null; created_at: string }[]; onDelete: (id: string) => void }) {
  return (
    <div>
      <div style={{ fontSize: 11, color: "#64748b", marginBottom: 6 }}>{title}</div>
      {items.length === 0 ? (
        <div style={{ fontSize: 12, color: "#475569" }}>None.</div>
      ) : (
        items.map((e) => (
          <div key={e.id} style={{
            display: "flex", alignItems: "center", gap: 8,
            padding: "6px 10px", borderRadius: 6, background: "#0f172a",
            marginBottom: 4, border: "1px solid #1e293b",
          }}>
            <span style={{ flex: 1, fontSize: 13, color: "#cbd5e1" }}>{e.note}</span>
            <button
              onClick={() => onDelete(e.id)}
              style={{ background: "transparent", border: "none", color: "#ef4444", cursor: "pointer" }}
            >×</button>
          </div>
        ))
      )}
    </div>
  );
}

function AdvancedAITab({ form, setForm }: { form: RoutingNode; setForm: React.Dispatch<React.SetStateAction<RoutingNode>> }) {
  const { data: preview } = useQuery({
    queryKey: ["prompt-preview", form.id],
    queryFn: () => getRoutingPromptPreview(form.id),
  });

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
      <Toggle
        label="Use additional custom instructions"
        checked={form.custom_prompt_enabled}
        onChange={(v) => setForm((f) => ({ ...f, custom_prompt_enabled: v }))}
      />
      {form.custom_prompt_enabled && (
        <Field label="Custom instructions (appended to compiled prompt)">
          <textarea
            rows={4}
            value={form.custom_prompt ?? ""}
            onChange={(e) => setForm((f) => ({ ...f, custom_prompt: e.target.value }))}
            style={{ ...inputStyle, resize: "vertical" }}
          />
        </Field>
      )}
      <div>
        <div style={{ fontSize: 11, color: "#64748b", marginBottom: 4 }}>Compiled prompt preview</div>
        <pre style={{
          background: "#0f172a", border: "1px solid #1e293b", borderRadius: 8,
          padding: 12, fontSize: 12, color: "#cbd5e1", whiteSpace: "pre-wrap",
          maxHeight: 400, overflowY: "auto",
        }}>
          {preview?.compiled_prompt ?? "Loading…"}
        </pre>
      </div>
    </div>
  );
}
