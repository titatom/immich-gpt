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
} from "../services/api";
import type { ProviderConfig } from "../types";
import { CheckCircle, AlertTriangle, Plus, Trash2 } from "lucide-react";

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
}: {
  form: ProviderForm;
  setForm: React.Dispatch<React.SetStateAction<ProviderForm>>;
  inputStyle: React.CSSProperties;
}) {
  const { data: models } = useQuery({
    queryKey: ["provider-models", form.provider_name, form.base_url],
    queryFn: () => getProviderModels(form.provider_name),
    enabled: form.provider_name === "ollama" || form.provider_name === "openrouter",
    retry: false,
  });

  return (
    <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12, marginBottom: 12 }}>
      <div>
        <label style={{ fontSize: 12, color: "#64748b", display: "block", marginBottom: 4 }}>Provider</label>
        <select value={form.provider_name} onChange={(e) => setForm((f) => ({ ...f, provider_name: e.target.value }))} style={_inputStyle}>
          <option value="openai">OpenAI</option>
          <option value="ollama">Ollama</option>
          <option value="openrouter">OpenRouter</option>
        </select>
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

function ProvidersSection() {
  const qc = useQueryClient();
  const { data: providers = [] } = useQuery({ queryKey: ["providers"], queryFn: getProviders });
  const [showAdd, setShowAdd] = useState(false);
  const [form, setForm] = useState({
    provider_name: "openai",
    api_key: "",
    model_name: "gpt-4o",
    base_url: "",
    enabled: true,
    is_default: true,
  });
  const [testResults, setTestResults] = useState<Record<string, TestResult>>({});

  const upsertMut = useMutation({
    mutationFn: upsertProvider,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["providers"] });
      setShowAdd(false);
      setForm({ provider_name: "openai", api_key: "", model_name: "gpt-4o", base_url: "", enabled: true, is_default: true });
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
                {testResults[p.provider_name].connected ? "✓ Connected" : `✗ ${testResults[p.provider_name].error}`}
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
          No providers configured. Add OpenAI to get started.
        </div>
      )}

      {showAdd ? (
        <div style={{ marginTop: 20 }}>
          <ModelPickerForm form={form} setForm={setForm} inputStyle={inputStyle} />

          <div style={{ marginBottom: 12 }}>
            <label style={{ fontSize: 12, color: "#64748b", display: "block", marginBottom: 4 }}>API Key</label>
            <input
              type="password"
              value={form.api_key}
              onChange={(e) => setForm((f) => ({ ...f, api_key: e.target.value }))}
              style={inputStyle}
              placeholder="sk-..."
            />
          </div>

          {(form.provider_name === "ollama" || form.provider_name === "openrouter") && (
            <div style={{ marginBottom: 12 }}>
              <label style={{ fontSize: 12, color: "#64748b", display: "block", marginBottom: 4 }}>Base URL</label>
              <input value={form.base_url} onChange={(e) => setForm((f) => ({ ...f, base_url: e.target.value }))} style={inputStyle} placeholder="http://..." />
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
              onClick={() => upsertMut.mutate(form)}
              disabled={upsertMut.isPending}
              style={{ padding: "8px 20px", borderRadius: 8, border: "none", background: "#1e40af", color: "white", fontSize: 13, fontWeight: 600, cursor: "pointer" }}
            >
              {upsertMut.isPending ? "Saving..." : "Save Provider"}
            </button>
            <button onClick={() => setShowAdd(false)} style={{ padding: "8px 16px", borderRadius: 8, border: "1px solid #334155", background: "transparent", color: "#64748b", fontSize: 13, cursor: "pointer" }}>
              Cancel
            </button>
          </div>
        </div>
      ) : (
        <button
          onClick={() => setShowAdd(true)}
          style={{ marginTop: 16, display: "flex", alignItems: "center", gap: 6, padding: "8px 16px", borderRadius: 8, border: "1px dashed #334155", background: "transparent", color: "#64748b", fontSize: 13, cursor: "pointer" }}
        >
          <Plus size={14} /> Add Provider
        </button>
      )}
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
      <ProvidersSection />

      {/* Environment info */}
      <div style={{ background: "#1e293b", border: "1px solid #334155", borderRadius: 12, padding: 20 }}>
        <h3 style={{ fontSize: 14, fontWeight: 600, color: "#94a3b8", margin: "0 0 12px" }}>
          Environment Variables
        </h3>
        <div style={{ fontSize: 12, color: "#475569", lineHeight: 1.8, fontFamily: "monospace" }}>
          <div>IMMICH_URL=http://immich.local:2283</div>
          <div>IMMICH_API_KEY=your-api-key</div>
          <div>OPENAI_API_KEY=sk-...</div>
          <div>OPENAI_MODEL=gpt-4o</div>
          <div>REDIS_URL=redis://redis:6379/0</div>
        </div>
        <div style={{ fontSize: 12, color: "#475569", marginTop: 12 }}>
          Set these in your <code style={{ background: "#0f172a", padding: "1px 4px", borderRadius: 3 }}>.env</code> file or Docker environment.
        </div>
      </div>
    </div>
  );
}
