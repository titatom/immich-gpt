import React, { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  getImmichSettings,
  saveImmichSettings,
  getProviders,
  upsertProvider,
  deleteProvider,
  testProvider,
  getProviderModels,
  getBehaviourSettings,
  saveBehaviourSettings,
  getHealth,
} from "../services/api";
import type { ProviderConfig } from "../types";
import { CheckCircle, AlertTriangle, Plus, Trash2, Pencil, Heart, Github, Scale } from "lucide-react";

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

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div style={{ marginBottom: 32 }}>
      <h2 style={{ fontSize: 16, fontWeight: 700, color: "#f1f5f9", marginBottom: 16 }}>{title}</h2>
      <div style={{ background: "#1e293b", border: "1px solid #334155", borderRadius: 12, padding: 24 }}>
        {children}
      </div>
    </div>
  );
}

interface TestResult {
  connected?: boolean;
  asset_count?: number;
  error?: string;
}

interface AxiosLikeError {
  response?: { data?: { detail?: string } };
  message: string;
}

function ImmichSection() {
  const qc = useQueryClient();
  const { data: settings } = useQuery({ queryKey: ["immich-settings"], queryFn: getImmichSettings });
  const [url, setUrl] = React.useState(settings?.immich_url || "");
  const [apiKey, setApiKey] = React.useState("");
  const [saveResult, setSaveResult] = React.useState<TestResult | null>(null);

  const saveMut = useMutation({
    mutationFn: () => saveImmichSettings(url, apiKey),
    onSuccess: (data) => {
      setSaveResult(data);
      qc.invalidateQueries({ queryKey: ["immich-settings"] });
    },
    onError: (e: AxiosLikeError) => setSaveResult({ error: e.response?.data?.detail || e.message }),
  });

  return (
    <Section title="Immich Connection">
      <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 20, padding: "12px 16px", borderRadius: 8, background: settings?.connected ? "rgba(34,197,94,0.06)" : "rgba(239,68,68,0.06)" }}>
        {settings?.connected
          ? <CheckCircle size={16} color="#22c55e" />
          : <AlertTriangle size={16} color="#ef4444" />}
        <span style={{ fontSize: 13, color: settings?.connected ? "#86efac" : "#fca5a5" }}>
          {settings?.connected
            ? `Connected — ${settings.asset_count?.toLocaleString()} assets`
            : settings?.error || "Not connected"}
        </span>
      </div>

      <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
        <div>
          <label style={{ fontSize: 12, color: "#64748b", display: "block", marginBottom: 4 }}>Immich URL</label>
          <input value={url} onChange={(e) => setUrl(e.target.value)} placeholder="http://immich.local:2283" style={inputStyle} />
          <div style={{ fontSize: 11, color: "#475569", marginTop: 4 }}>
            Settings saved here are stored in the database and override env vars.
          </div>
        </div>

        <div>
          <label style={{ fontSize: 12, color: "#64748b", display: "block", marginBottom: 4 }}>API Key</label>
          <input value={apiKey} onChange={(e) => setApiKey(e.target.value)} type="password" placeholder="Leave blank to keep existing key" style={inputStyle} />
        </div>

        <div style={{ display: "flex", gap: 8 }}>
          <button
            onClick={() => saveMut.mutate()}
            disabled={!url || saveMut.isPending}
            style={{ padding: "8px 20px", borderRadius: 8, border: "none", background: "#1e40af", color: "white", fontSize: 13, fontWeight: 600, cursor: "pointer" }}
          >
            {saveMut.isPending ? "Saving…" : "Save & Test"}
          </button>
        </div>

        {saveResult && (
          <div style={{
            padding: "10px 14px", borderRadius: 8,
            background: saveResult.connected ? "rgba(34,197,94,0.08)" : "rgba(239,68,68,0.08)",
            border: `1px solid ${saveResult.connected ? "#16a34a30" : "#dc262630"}`,
            fontSize: 13,
            color: saveResult.connected ? "#86efac" : "#fca5a5",
          }}>
            {saveResult.connected
              ? `✓ Connected — ${saveResult.asset_count?.toLocaleString()} assets`
              : `✗ ${saveResult.error || "Connection failed"}`}
          </div>
        )}
      </div>
    </Section>
  );
}

interface ProviderForm {
  provider_name: string;
  api_key: string;
  model_name: string;
  base_url: string;
  enabled: boolean;
  is_default: boolean;
}

function ModelPickerForm({
  form,
  setForm,
  inputStyle: _inputStyle,
  isEditing,
}: {
  form: ProviderForm;
  setForm: React.Dispatch<React.SetStateAction<ProviderForm>>;
  inputStyle: React.CSSProperties;
  isEditing?: boolean;
}) {
  const { data: models } = useQuery({
    queryKey: ["provider-models", form.provider_name, form.base_url],
    queryFn: () => getProviderModels(form.provider_name),
    enabled: form.provider_name === "ollama" || form.provider_name === "openrouter",
    retry: false,
  });

  const providerLabels: Record<string, string> = {
    openai: "OpenAI",
    ollama: "Ollama",
    openrouter: "OpenRouter",
  };

  return (
    <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12, marginBottom: 12 }}>
      <div>
        <label style={{ fontSize: 12, color: "#64748b", display: "block", marginBottom: 4 }}>Provider</label>
        {isEditing ? (
          <div style={{ ..._inputStyle, display: "flex", alignItems: "center", gap: 6, opacity: 0.7, cursor: "not-allowed" }}>
            <span style={{ fontSize: 13, color: "#94a3b8" }}>{providerLabels[form.provider_name] ?? form.provider_name}</span>
            <span style={{ fontSize: 11, color: "#475569", marginLeft: "auto" }}>locked</span>
          </div>
        ) : (
          <select
            value={form.provider_name}
            onChange={(e) => {
              const p = e.target.value;
              const defaultModel = p === "ollama" ? "llava" : p === "openrouter" ? "openai/gpt-4o" : "gpt-4o";
              setForm((f) => ({ ...f, provider_name: p, model_name: defaultModel, api_key: "" }));
            }}
            style={_inputStyle}
          >
            <option value="openai">OpenAI</option>
            <option value="ollama">Ollama</option>
            <option value="openrouter">OpenRouter</option>
          </select>
        )}
      </div>
      <div>
        <label style={{ fontSize: 12, color: "#64748b", display: "block", marginBottom: 4 }}>Model</label>
        {models && models.length > 0 ? (
          <select value={form.model_name} onChange={(e) => setForm((f) => ({ ...f, model_name: e.target.value }))} style={_inputStyle}>
            {models.map((m) => <option key={m.id} value={m.id}>{m.name}</option>)}
          </select>
        ) : (
          <input
            value={form.model_name}
            onChange={(e) => setForm((f) => ({ ...f, model_name: e.target.value }))}
            style={_inputStyle}
            placeholder={form.provider_name === "ollama" ? "llava" : form.provider_name === "openrouter" ? "openai/gpt-4o" : "gpt-4o"}
          />
        )}
      </div>
    </div>
  );
}

const EMPTY_FORM: ProviderForm = {
  provider_name: "openai",
  api_key: "",
  model_name: "gpt-4o",
  base_url: "",
  enabled: true,
  is_default: true,
};

function ProviderFormPanel({
  form,
  setForm,
  isEditing,
  isPending,
  onSave,
  onCancel,
}: {
  form: ProviderForm;
  setForm: React.Dispatch<React.SetStateAction<ProviderForm>>;
  isEditing: boolean;
  isPending: boolean;
  onSave: () => void;
  onCancel: () => void;
}) {
  return (
    <div style={{ marginTop: 20 }}>
      <ModelPickerForm form={form} setForm={setForm} inputStyle={inputStyle} isEditing={isEditing} />

      {form.provider_name !== "ollama" && (
        <div style={{ marginBottom: 12 }}>
          <label style={{ fontSize: 12, color: "#64748b", display: "block", marginBottom: 4 }}>API Key</label>
          <input
            type="password"
            value={form.api_key}
            onChange={(e) => setForm((f) => ({ ...f, api_key: e.target.value }))}
            style={inputStyle}
            placeholder={isEditing ? "Leave blank to keep existing key" : form.provider_name === "openrouter" ? "sk-or-..." : "sk-..."}
          />
        </div>
      )}

      {form.provider_name === "ollama" && (
        <div style={{ marginBottom: 12 }}>
          <label style={{ fontSize: 12, color: "#64748b", display: "block", marginBottom: 4 }}>Base URL</label>
          <input value={form.base_url} onChange={(e) => setForm((f) => ({ ...f, base_url: e.target.value }))} style={inputStyle} placeholder="http://localhost:11434" />
          <div style={{ fontSize: 11, color: "#475569", marginTop: 4 }}>
            Ollama is self-hosted and does not require an API key.
          </div>
        </div>
      )}
      {form.provider_name === "openrouter" && (
        <div style={{ marginBottom: 12, padding: "10px 14px", background: "#0f172a", borderRadius: 8, border: "1px solid #334155" }}>
          <div style={{ fontSize: 12, color: "#64748b" }}>
            OpenRouter uses <code style={{ background: "#1e293b", padding: "1px 4px", borderRadius: 3 }}>https://openrouter.ai/api/v1</code> automatically — no Base URL needed.
          </div>
          <div style={{ fontSize: 11, color: "#475569", marginTop: 6 }}>
            After saving, the model picker will load all available OpenRouter models. You can type a model ID (e.g. <code style={{ background: "#1e293b", padding: "1px 4px", borderRadius: 3 }}>openai/gpt-4o</code>, <code style={{ background: "#1e293b", padding: "1px 4px", borderRadius: 3 }}>anthropic/claude-3.5-sonnet</code>) or save first to browse.
          </div>
        </div>
      )}

      <div style={{ display: "flex", gap: 8, alignItems: "center", marginBottom: 12 }}>
        <label style={{ display: "flex", alignItems: "center", gap: 6, cursor: "pointer" }}>
          <input type="checkbox" checked={form.is_default} onChange={(e) => setForm((f) => ({ ...f, is_default: e.target.checked }))} />
          <span style={{ fontSize: 13, color: "#94a3b8" }}>Set as default</span>
        </label>
        <label style={{ display: "flex", alignItems: "center", gap: 6, cursor: "pointer" }}>
          <input type="checkbox" checked={form.enabled} onChange={(e) => setForm((f) => ({ ...f, enabled: e.target.checked }))} />
          <span style={{ fontSize: 13, color: "#94a3b8" }}>Enabled</span>
        </label>
      </div>

      <div style={{ display: "flex", gap: 8 }}>
        <button
          onClick={onSave}
          disabled={isPending}
          style={{ padding: "8px 20px", borderRadius: 8, border: "none", background: "#1e40af", color: "white", fontSize: 13, fontWeight: 600, cursor: "pointer" }}
        >
          {isPending ? "Saving..." : isEditing ? "Update Provider" : "Save Provider"}
        </button>
        <button onClick={onCancel} style={{ padding: "8px 16px", borderRadius: 8, border: "1px solid #334155", background: "transparent", color: "#64748b", fontSize: 13, cursor: "pointer" }}>
          Cancel
        </button>
      </div>
    </div>
  );
}

function ProvidersSection() {
  const qc = useQueryClient();
  const { data: providers = [] } = useQuery({ queryKey: ["providers"], queryFn: getProviders });
  const [showAdd, setShowAdd] = useState(false);
  const [editingName, setEditingName] = useState<string | null>(null);
  const [form, setForm] = useState<ProviderForm>(EMPTY_FORM);
  const [testResults, setTestResults] = useState<Record<string, TestResult>>({});

  function openAdd() {
    setEditingName(null);
    setForm(EMPTY_FORM);
    setShowAdd(true);
  }

  function openEdit(p: ProviderConfig) {
    setEditingName(p.provider_name);
    setForm({
      provider_name: p.provider_name,
      api_key: "",
      model_name: p.model_name || "",
      base_url: p.base_url || "",
      enabled: p.enabled,
      is_default: p.is_default,
    });
    setShowAdd(true);
  }

  function closeForm() {
    setShowAdd(false);
    setEditingName(null);
    setForm(EMPTY_FORM);
  }

  const upsertMut = useMutation({
    mutationFn: upsertProvider,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["providers"] });
      closeForm();
    },
  });

  const deleteMut = useMutation({
    mutationFn: deleteProvider,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["providers"] }),
  });

  const testMut = useMutation({
    mutationFn: testProvider,
    onSuccess: (data, name) => setTestResults((r) => ({ ...r, [name]: data })),
    onError: (e: AxiosLikeError, name) => setTestResults((r) => ({ ...r, [name]: { error: e.message } })),
  });

  const isEditing = editingName !== null;

  return (
    <Section title="AI Providers">
      {providers.map((p: ProviderConfig) => (
        <div key={p.id} style={{ display: "flex", alignItems: "center", gap: 12, padding: "12px 0", borderBottom: "1px solid #334155" }}>
          <div style={{
            width: 40, height: 40, borderRadius: 8, background: "#0f172a",
            display: "flex", alignItems: "center", justifyContent: "center",
            fontSize: 12, fontWeight: 700, color: "#38bdf8", textTransform: "uppercase",
          }}>
            {p.provider_name.slice(0, 2)}
          </div>
          <div style={{ flex: 1 }}>
            <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
              <span style={{ fontSize: 14, fontWeight: 600, color: "#f1f5f9" }}>
                {p.provider_name}
              </span>
              {p.is_default && (
                <span style={{ fontSize: 11, color: "#22c55e", background: "rgba(34,197,94,0.1)", borderRadius: 4, padding: "1px 6px" }}>
                  Default
                </span>
              )}
              {!p.enabled && (
                <span style={{ fontSize: 11, color: "#475569", background: "#0f172a", border: "1px solid #334155", borderRadius: 4, padding: "1px 6px" }}>
                  Disabled
                </span>
              )}
            </div>
            <div style={{ fontSize: 12, color: "#64748b" }}>
              {p.model_name}
              {p.base_url && ` — ${p.base_url}`}
              {p.has_api_key && " — API key set"}
            </div>
            {testResults[p.provider_name] && (
              <div style={{ fontSize: 12, color: testResults[p.provider_name].connected ? "#86efac" : "#fca5a5" }}>
                {testResults[p.provider_name].connected
                  ? "✓ Connected"
                  : `✗ ${testResults[p.provider_name].error || "Connection failed"}`}
              </div>
            )}
          </div>
          <div style={{ display: "flex", gap: 6 }}>
            <button
              onClick={() => testMut.mutate(p.provider_name)}
              style={{ padding: "6px 12px", borderRadius: 6, border: "1px solid #334155", background: "transparent", color: "#64748b", fontSize: 12, cursor: "pointer" }}
            >
              Test
            </button>
            <button
              onClick={() => openEdit(p)}
              title="Edit provider"
              style={{ padding: "6px 8px", borderRadius: 6, border: "1px solid #334155", background: "transparent", color: "#38bdf8", cursor: "pointer" }}
            >
              <Pencil size={13} />
            </button>
            <button
              onClick={() => {
                if (confirm(`Remove ${p.provider_name}?`)) deleteMut.mutate(p.provider_name);
              }}
              style={{ padding: "6px 8px", borderRadius: 6, border: "1px solid #334155", background: "transparent", color: "#ef4444", cursor: "pointer" }}
            >
              <Trash2 size={13} />
            </button>
          </div>
        </div>
      ))}

      {providers.length === 0 && !showAdd && (
        <div style={{ fontSize: 14, color: "#64748b", textAlign: "center", padding: 16 }}>
          No providers configured. Add OpenAI, OpenRouter, or Ollama to get started.
        </div>
      )}

      {showAdd ? (
        <ProviderFormPanel
          form={form}
          setForm={setForm}
          isEditing={isEditing}
          isPending={upsertMut.isPending}
          onSave={() => upsertMut.mutate(form)}
          onCancel={closeForm}
        />
      ) : (
        <button
          onClick={openAdd}
          style={{ marginTop: 16, display: "flex", alignItems: "center", gap: 6, padding: "8px 16px", borderRadius: 8, border: "1px dashed #334155", background: "transparent", color: "#64748b", fontSize: 13, cursor: "pointer" }}
        >
          <Plus size={14} /> Add Provider
        </button>
      )}
    </Section>
  );
}

function BehaviourSection() {
  const qc = useQueryClient();
  const { data: behaviour } = useQuery({
    queryKey: ["behaviour-settings"],
    queryFn: getBehaviourSettings,
  });

  const [allowNewTags, setAllowNewTags] = React.useState<boolean | undefined>(undefined);
  const [allowNewAlbums, setAllowNewAlbums] = React.useState<boolean | undefined>(undefined);
  const [saved, setSaved] = React.useState(false);

  React.useEffect(() => {
    if (behaviour) {
      setAllowNewTags(behaviour.allow_new_tags);
      setAllowNewAlbums(behaviour.allow_new_albums);
    }
  }, [behaviour]);

  const saveMut = useMutation({
    mutationFn: () => saveBehaviourSettings({
      allow_new_tags: allowNewTags ?? true,
      allow_new_albums: allowNewAlbums ?? true,
    }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["behaviour-settings"] });
      setSaved(true);
      setTimeout(() => setSaved(false), 2000);
    },
  });

  const effectiveTags = allowNewTags ?? behaviour?.allow_new_tags ?? true;
  const effectiveAlbums = allowNewAlbums ?? behaviour?.allow_new_albums ?? true;

  return (
    <Section title="AI Behaviour">
      <div style={{ display: "flex", flexDirection: "column", gap: 24 }}>
        {/* Tags behaviour */}
        <div>
          <div style={{ fontSize: 14, fontWeight: 600, color: "#f1f5f9", marginBottom: 8 }}>Tag Creation</div>
          <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
            <label style={{ display: "flex", alignItems: "flex-start", gap: 12, cursor: "pointer" }}>
              <input
                type="radio"
                name="tag_mode"
                checked={effectiveTags}
                onChange={() => setAllowNewTags(true)}
                style={{ marginTop: 2 }}
              />
              <div>
                <div style={{ fontSize: 13, color: "#f1f5f9", fontWeight: 500 }}>Allow AI to create new tags</div>
                <div style={{ fontSize: 12, color: "#64748b", marginTop: 2 }}>
                  The AI can suggest any tag names, including ones that don't yet exist in Immich.
                </div>
              </div>
            </label>
            <label style={{ display: "flex", alignItems: "flex-start", gap: 12, cursor: "pointer" }}>
              <input
                type="radio"
                name="tag_mode"
                checked={!effectiveTags}
                onChange={() => setAllowNewTags(false)}
                style={{ marginTop: 2 }}
              />
              <div>
                <div style={{ fontSize: 13, color: "#f1f5f9", fontWeight: 500 }}>Only use existing tags</div>
                <div style={{ fontSize: 12, color: "#64748b", marginTop: 2 }}>
                  The AI will only select from tags already present on the asset. No new tag names will be created.
                </div>
              </div>
            </label>
          </div>
        </div>

        <div style={{ borderTop: "1px solid #334155" }} />

        {/* Album behaviour */}
        <div>
          <div style={{ fontSize: 14, fontWeight: 600, color: "#f1f5f9", marginBottom: 8 }}>Album / Sub-album Creation</div>
          <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
            <label style={{ display: "flex", alignItems: "flex-start", gap: 12, cursor: "pointer" }}>
              <input
                type="radio"
                name="album_mode"
                checked={effectiveAlbums}
                onChange={() => setAllowNewAlbums(true)}
                style={{ marginTop: 2 }}
              />
              <div>
                <div style={{ fontSize: 13, color: "#f1f5f9", fontWeight: 500 }}>Allow AI to suggest new albums</div>
                <div style={{ fontSize: 12, color: "#64748b", marginTop: 2 }}>
                  The AI can suggest sub-album names freely, including creating new albums when writing back to Immich.
                </div>
              </div>
            </label>
            <label style={{ display: "flex", alignItems: "flex-start", gap: 12, cursor: "pointer" }}>
              <input
                type="radio"
                name="album_mode"
                checked={!effectiveAlbums}
                onChange={() => setAllowNewAlbums(false)}
                style={{ marginTop: 2 }}
              />
              <div>
                <div style={{ fontSize: 13, color: "#f1f5f9", fontWeight: 500 }}>Only use existing albums</div>
                <div style={{ fontSize: 12, color: "#64748b", marginTop: 2 }}>
                  The AI will only suggest sub-albums that already exist in Immich. New album names will not be used.
                </div>
              </div>
            </label>
          </div>
        </div>

        <div>
          <button
            onClick={() => saveMut.mutate()}
            disabled={saveMut.isPending || allowNewTags === undefined}
            style={{
              padding: "8px 20px", borderRadius: 8, border: "none",
              background: saved ? "#16a34a" : "#1e40af",
              color: "white", fontSize: 13, fontWeight: 600, cursor: "pointer",
              transition: "background 0.2s",
            }}
          >
            {saveMut.isPending ? "Saving…" : saved ? "Saved!" : "Save Behaviour Settings"}
          </button>
        </div>
      </div>
    </Section>
  );
}

const REPOSITORY_URL = "https://github.com/titatom/immich-gpt";
const DONATE_URL =
  "https://www.paypal.com/donate/?business=P9PZB949MYSD8&no_recurring=0&item_name=Thanks+for+helping+me+continuing+to+develop+this+app+%21&currency_code=CAD";

function AboutSection() {
  const { data: health } = useQuery({ queryKey: ["health"], queryFn: getHealth });

  const linkStyle: React.CSSProperties = {
    display: "inline-flex",
    alignItems: "center",
    gap: 7,
    padding: "8px 16px",
    borderRadius: 8,
    border: "1px solid #334155",
    background: "transparent",
    color: "#94a3b8",
    fontSize: 13,
    fontWeight: 500,
    textDecoration: "none",
    transition: "all 0.15s ease",
    cursor: "pointer",
  };

  return (
    <Section title="About">
      <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
        {/* Version row */}
        <div style={{ display: "flex", gap: 32, flexWrap: "wrap" }}>
          <div>
            <div style={{ fontSize: 11, color: "#475569", marginBottom: 3, textTransform: "uppercase", letterSpacing: "0.05em" }}>Version</div>
            <div style={{ fontSize: 14, color: "#f1f5f9", fontWeight: 600, fontFamily: "monospace" }}>
              {health?.version ?? "—"}
            </div>
          </div>
          <div>
            <div style={{ fontSize: 11, color: "#475569", marginBottom: 3, textTransform: "uppercase", letterSpacing: "0.05em" }}>License</div>
            <div style={{ fontSize: 14, color: "#f1f5f9", fontWeight: 600 }}>AGPL-3.0</div>
          </div>
          <div>
            <div style={{ fontSize: 11, color: "#475569", marginBottom: 3, textTransform: "uppercase", letterSpacing: "0.05em" }}>Author</div>
            <div style={{ fontSize: 14, color: "#f1f5f9", fontWeight: 600 }}>titatom</div>
          </div>
        </div>

        <div style={{ borderTop: "1px solid #334155" }} />

        {/* Links */}
        <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
          <a
            href={REPOSITORY_URL}
            target="_blank"
            rel="noreferrer"
            style={linkStyle}
            onMouseEnter={(e) => {
              (e.currentTarget as HTMLAnchorElement).style.color = "#f1f5f9";
              (e.currentTarget as HTMLAnchorElement).style.borderColor = "#64748b";
            }}
            onMouseLeave={(e) => {
              (e.currentTarget as HTMLAnchorElement).style.color = "#94a3b8";
              (e.currentTarget as HTMLAnchorElement).style.borderColor = "#334155";
            }}
          >
            <Github size={14} />
            Source Code
          </a>
          <a
            href={`${REPOSITORY_URL}/blob/main/LICENSE`}
            target="_blank"
            rel="noreferrer"
            style={linkStyle}
            onMouseEnter={(e) => {
              (e.currentTarget as HTMLAnchorElement).style.color = "#f1f5f9";
              (e.currentTarget as HTMLAnchorElement).style.borderColor = "#64748b";
            }}
            onMouseLeave={(e) => {
              (e.currentTarget as HTMLAnchorElement).style.color = "#94a3b8";
              (e.currentTarget as HTMLAnchorElement).style.borderColor = "#334155";
            }}
          >
            <Scale size={14} />
            License
          </a>
          <a
            href={DONATE_URL}
            target="_blank"
            rel="noreferrer"
            style={{
              ...linkStyle,
              background: "linear-gradient(135deg, rgba(245,158,11,0.15), rgba(239,68,68,0.12))",
              border: "1px solid rgba(245,158,11,0.35)",
              color: "#fbbf24",
            }}
            onMouseEnter={(e) => {
              (e.currentTarget as HTMLAnchorElement).style.background =
                "linear-gradient(135deg, rgba(245,158,11,0.28), rgba(239,68,68,0.22))";
              (e.currentTarget as HTMLAnchorElement).style.borderColor = "rgba(245,158,11,0.6)";
              (e.currentTarget as HTMLAnchorElement).style.color = "#fcd34d";
            }}
            onMouseLeave={(e) => {
              (e.currentTarget as HTMLAnchorElement).style.background =
                "linear-gradient(135deg, rgba(245,158,11,0.15), rgba(239,68,68,0.12))";
              (e.currentTarget as HTMLAnchorElement).style.borderColor = "rgba(245,158,11,0.35)";
              (e.currentTarget as HTMLAnchorElement).style.color = "#fbbf24";
            }}
          >
            <Heart size={14} style={{ fill: "currentColor" }} />
            Donate
          </a>
        </div>

        <div style={{ borderTop: "1px solid #334155" }} />

        {/* Environment variables */}
        <div>
          <div style={{ fontSize: 11, color: "#475569", marginBottom: 10, textTransform: "uppercase", letterSpacing: "0.05em" }}>
            Environment Variables
          </div>
          <div style={{ fontSize: 12, color: "#475569", lineHeight: 1.8, fontFamily: "monospace", background: "#0f172a", borderRadius: 8, padding: "12px 16px" }}>
            <div>IMMICH_URL=http://immich.local:2283</div>
            <div>IMMICH_API_KEY=your-api-key</div>
            <div>OPENAI_API_KEY=sk-...</div>
            <div>OPENAI_MODEL=gpt-4o</div>
            <div>REDIS_URL=redis://redis:6379/0</div>
          </div>
          <div style={{ fontSize: 12, color: "#475569", marginTop: 8 }}>
            Set these in your <code style={{ background: "#0f172a", padding: "1px 4px", borderRadius: 3 }}>.env</code> file or Docker environment.
          </div>
        </div>
      </div>
    </Section>
  );
}

export default function Settings() {
  return (
    <div style={{ padding: "32px 40px", maxWidth: 700 }}>
      <div style={{ marginBottom: 32 }}>
        <h1 style={{ fontSize: 24, fontWeight: 700, color: "#f1f5f9", margin: 0 }}>Settings</h1>
        <p style={{ fontSize: 14, color: "#64748b", margin: "4px 0 0" }}>
          Configure Immich connection and AI providers
        </p>
      </div>

      <ImmichSection />
      <BehaviourSection />
      <ProvidersSection />
      <AboutSection />
    </div>
  );
}
