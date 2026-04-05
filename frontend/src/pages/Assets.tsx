import React from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useSearchParams } from "react-router-dom";
import {
  getAssets, getAssetCount, getAllAssetIds, getAssetDetail, getThumbnailUrl,
  getBuckets, reclassifyAssets,
} from "../services/api";
import type { Asset, AssetDetail, Bucket } from "../types";
import {
  Search, Image as ImageIcon, ArrowUp, ArrowDown, ArrowUpDown,
  X, Star, Archive, ExternalLink, Camera, MapPin, Tag, Calendar,
  CheckCircle, Clock, XCircle, AlertCircle, RefreshCw,
} from "lucide-react";
import { useNavigate } from "react-router-dom";

const PAGE_SIZE = 50;

type SortKey = "date" | "filename" | "location" | "tags" | "album" | "type" | "bucket";
type SortDir = "asc" | "desc";

function sortAssets(assets: Asset[], key: SortKey, dir: SortDir, classificationMap?: Record<string, string>): Asset[] {
  const factor = dir === "asc" ? 1 : -1;
  return [...assets].sort((a, b) => {
    let va: string;
    let vb: string;
    switch (key) {
      case "date":     va = a.file_created_at ?? a.created_at ?? ""; vb = b.file_created_at ?? b.created_at ?? ""; break;
      case "filename": va = a.original_filename ?? ""; vb = b.original_filename ?? ""; break;
      case "location": va = [a.city, a.country].filter(Boolean).join(", "); vb = [b.city, b.country].filter(Boolean).join(", "); break;
      case "tags":     va = (a.tags ?? []).join(", "); vb = (b.tags ?? []).join(", "); break;
      case "album":    va = (a.album_ids ?? []).join(","); vb = (b.album_ids ?? []).join(","); break;
      case "type":     va = a.asset_type ?? ""; vb = b.asset_type ?? ""; break;
      case "bucket":   va = classificationMap?.[a.id] ?? ""; vb = classificationMap?.[b.id] ?? ""; break;
      default:         va = ""; vb = "";
    }
    if (!va && vb) return 1;
    if (va && !vb) return -1;
    if (!va && !vb) return 0;
    return factor * va.localeCompare(vb);
  });
}

const SORT_LABELS: Record<SortKey, string> = {
  date: "Date", filename: "Filename", location: "Location",
  tags: "Tags", album: "Album", type: "Type", bucket: "Bucket",
};

function SortHeader({ label, sortKey, current, dir, onChange }: {
  label: string; sortKey: SortKey; current: SortKey; dir: SortDir; onChange: (k: SortKey) => void;
}) {
  const active = current === sortKey;
  return (
    <button onClick={() => onChange(sortKey)} style={{
      display: "flex", alignItems: "center", gap: 4,
      background: active ? "rgba(56,189,248,0.08)" : "transparent",
      border: "none", cursor: "pointer",
      color: active ? "#38bdf8" : "#64748b",
      fontSize: 12, fontWeight: active ? 600 : 400, padding: "4px 8px", borderRadius: 6,
    }}>
      {label}
      {active ? (dir === "asc" ? <ArrowUp size={11} /> : <ArrowDown size={11} />) : <ArrowUpDown size={11} />}
    </button>
  );
}

function confidenceColor(c?: number) {
  if (!c) return "#64748b";
  if (c >= 0.8) return "#22c55e";
  if (c >= 0.6) return "#f59e0b";
  return "#ef4444";
}

function classificationStatusIcon(status?: string) {
  if (status === "approved") return <CheckCircle size={13} color="#22c55e" />;
  if (status === "rejected") return <XCircle size={13} color="#ef4444" />;
  if (status === "pending_review") return <Clock size={13} color="#f59e0b" />;
  return <AlertCircle size={13} color="#64748b" />;
}

function MetaRow({ icon, label, value }: { icon: React.ReactNode; label: string; value: React.ReactNode }) {
  if (!value) return null;
  return (
    <div style={{ display: "flex", gap: 10, alignItems: "flex-start", padding: "7px 0", borderBottom: "1px solid #1e293b" }}>
      <div style={{ color: "#475569", flexShrink: 0, marginTop: 1 }}>{icon}</div>
      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{ fontSize: 11, color: "#475569", fontWeight: 500, marginBottom: 2 }}>{label}</div>
        <div style={{ fontSize: 13, color: "#e2e8f0", wordBreak: "break-word" }}>{value}</div>
      </div>
    </div>
  );
}

function AssetDetailPanel({
  assetId,
  onClose,
  onReclassify,
}: {
  assetId: string;
  onClose: () => void;
  onReclassify: (ids: string[]) => void;
}) {
  const { data, isLoading } = useQuery<AssetDetail>({
    queryKey: ["asset-detail", assetId],
    queryFn: () => getAssetDetail(assetId),
  });

  const [imgError, setImgError] = React.useState(false);

  React.useEffect(() => {
    const handler = (e: KeyboardEvent) => { if (e.key === "Escape") onClose(); };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [onClose]);

  const cls = data?.classification;
  const meta = data?.metadata_suggestion;

  const effectiveBucket = cls?.override_bucket_name ?? cls?.suggested_bucket_name;
  const location = data ? [data.city, data.country].filter(Boolean).join(", ") : "";

  return (
    <>
      <div onClick={onClose} style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,0.55)", zIndex: 200 }} />
      <div style={{
        position: "fixed", top: 0, right: 0, bottom: 0,
        width: "min(480px, 100vw)",
        background: "#0f172a", borderLeft: "1px solid #334155",
        zIndex: 201, display: "flex", flexDirection: "column", overflow: "hidden",
      }}>
        <div style={{
          display: "flex", alignItems: "center", justifyContent: "space-between",
          padding: "16px 20px", borderBottom: "1px solid #1e293b", flexShrink: 0,
        }}>
          <div style={{ fontSize: 14, fontWeight: 600, color: "#f1f5f9", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap", flex: 1, marginRight: 12 }}>
            {data?.original_filename || data?.immich_id || "Asset Detail"}
          </div>
          <div style={{ display: "flex", gap: 6, flexShrink: 0 }}>
            {data && (
              <button
                onClick={() => onReclassify([assetId])}
                title="Re-classify this asset"
                style={{
                  display: "flex", alignItems: "center", gap: 5,
                  padding: "5px 10px", borderRadius: 6, border: "1px solid #334155",
                  background: "transparent", color: "#7c3aed", cursor: "pointer", fontSize: 12,
                }}
              >
                <RefreshCw size={12} /> Re-classify
              </button>
            )}
            <button onClick={onClose} style={{ background: "none", border: "none", cursor: "pointer", color: "#64748b", padding: 4 }}>
              <X size={18} />
            </button>
          </div>
        </div>

        <div style={{ flex: 1, overflowY: "auto" }}>
          {isLoading ? (
            <div style={{ padding: 40, textAlign: "center", color: "#64748b" }}>Loading…</div>
          ) : !data ? (
            <div style={{ padding: 40, textAlign: "center", color: "#64748b" }}>Asset not found.</div>
          ) : (
            <>
              <div style={{ background: "#000", position: "relative", aspectRatio: "16/9", overflow: "hidden", flexShrink: 0 }}>
                {imgError ? (
                  <div style={{ width: "100%", height: "100%", display: "flex", alignItems: "center", justifyContent: "center" }}>
                    <ImageIcon size={48} color="#334155" />
                  </div>
                ) : (
                  <img
                    src={getThumbnailUrl(data.id, "preview")}
                    alt={data.original_filename || ""}
                    onError={() => setImgError(true)}
                    style={{ width: "100%", height: "100%", objectFit: "contain", display: "block" }}
                  />
                )}
                <div style={{ position: "absolute", top: 8, left: 8, display: "flex", gap: 6 }}>
                  {data.is_favorite && (
                    <span style={{ background: "rgba(0,0,0,0.6)", borderRadius: 6, padding: "3px 7px", display: "flex", alignItems: "center", gap: 4 }}>
                      <Star size={11} color="#fbbf24" fill="#fbbf24" />
                    </span>
                  )}
                  {data.is_archived && (
                    <span style={{ background: "rgba(0,0,0,0.6)", borderRadius: 6, padding: "3px 7px", display: "flex", alignItems: "center", gap: 4 }}>
                      <Archive size={11} color="#94a3b8" />
                    </span>
                  )}
                  {data.is_external_library && (
                    <span style={{ background: "rgba(0,0,0,0.6)", borderRadius: 6, padding: "3px 7px", display: "flex", alignItems: "center", gap: 4 }}>
                      <ExternalLink size={11} color="#94a3b8" />
                    </span>
                  )}
                </div>
                {data.asset_type && (
                  <span style={{
                    position: "absolute", bottom: 8, right: 8,
                    background: "rgba(0,0,0,0.6)", borderRadius: 6, padding: "3px 8px",
                    fontSize: 11, fontWeight: 600, color: "#38bdf8",
                  }}>
                    {data.asset_type}
                  </span>
                )}
              </div>

              <div style={{ padding: "16px 20px", borderBottom: "1px solid #1e293b" }}>
                <div style={{ fontSize: 11, fontWeight: 700, color: "#475569", textTransform: "uppercase", letterSpacing: "0.06em", marginBottom: 10 }}>
                  Classification
                </div>
                {cls ? (
                  <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                    <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                      {classificationStatusIcon(cls.status)}
                      <div>
                        <div style={{ fontSize: 12, color: "#64748b" }}>
                          {cls.override_bucket_name ? "Approved bucket" : "Suggested bucket"}
                        </div>
                        <div style={{ fontSize: 14, fontWeight: 600, color: "#38bdf8" }}>
                          {effectiveBucket ?? <span style={{ color: "#475569" }}>—</span>}
                        </div>
                      </div>
                      <span style={{
                        marginLeft: "auto", fontSize: 11, fontWeight: 600,
                        padding: "2px 8px", borderRadius: 6,
                        background: cls.status === "approved" ? "rgba(34,197,94,0.12)" :
                                    cls.status === "rejected" ? "rgba(239,68,68,0.12)" :
                                    cls.status === "pending_review" ? "rgba(245,158,11,0.12)" : "rgba(100,116,139,0.12)",
                        color: cls.status === "approved" ? "#22c55e" :
                               cls.status === "rejected" ? "#ef4444" :
                               cls.status === "pending_review" ? "#f59e0b" : "#64748b",
                      }}>
                        {cls.status?.replace("_", " ") ?? "unknown"}
                      </span>
                    </div>
                    {cls.confidence !== undefined && cls.confidence !== null && (
                      <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                        <div style={{ flex: 1, height: 5, background: "#1e293b", borderRadius: 3, overflow: "hidden" }}>
                          <div style={{ height: "100%", width: `${Math.round(cls.confidence * 100)}%`, background: confidenceColor(cls.confidence), borderRadius: 3, transition: "width 0.3s" }} />
                        </div>
                        <span style={{ fontSize: 12, color: confidenceColor(cls.confidence), fontWeight: 600, flexShrink: 0 }}>
                          {Math.round(cls.confidence * 100)}%
                        </span>
                      </div>
                    )}
                    {cls.subalbum_suggestion && (
                      <div style={{ fontSize: 12, color: "#94a3b8" }}>
                        Sub-album: <span style={{ color: "#60a5fa" }}>{cls.subalbum_suggestion}</span>
                      </div>
                    )}
                    {cls.explanation && (
                      <div style={{ fontSize: 12, color: "#94a3b8", background: "#1e293b", borderRadius: 6, padding: "8px 12px", lineHeight: 1.6 }}>
                        {cls.explanation}
                      </div>
                    )}
                    {cls.provider_name && (
                      <div style={{ fontSize: 11, color: "#475569" }}>via {cls.provider_name}</div>
                    )}
                  </div>
                ) : (
                  <div style={{ fontSize: 13, color: "#475569" }}>
                    Not classified yet. Run AI Classification to analyse this asset.
                  </div>
                )}
              </div>

              {meta && (meta.description_suggestion || (meta.tags ?? []).length > 0) && (
                <div style={{ padding: "16px 20px", borderBottom: "1px solid #1e293b" }}>
                  <div style={{ fontSize: 11, fontWeight: 700, color: "#475569", textTransform: "uppercase", letterSpacing: "0.06em", marginBottom: 10 }}>
                    AI Metadata Suggestion
                    {meta.writeback_status && (
                      <span style={{
                        marginLeft: 8, fontSize: 10, fontWeight: 600, padding: "1px 7px", borderRadius: 5,
                        background: meta.writeback_status === "written" ? "rgba(34,197,94,0.12)" : "rgba(100,116,139,0.12)",
                        color: meta.writeback_status === "written" ? "#22c55e" : "#64748b",
                      }}>
                        {meta.writeback_status}
                      </span>
                    )}
                  </div>
                  {meta.description_suggestion && (
                    <div style={{ fontSize: 13, color: "#cbd5e1", lineHeight: 1.6, marginBottom: 8 }}>
                      {meta.description_suggestion}
                    </div>
                  )}
                  {(meta.tags ?? []).length > 0 && (
                    <div style={{ display: "flex", gap: 5, flexWrap: "wrap" }}>
                      {(meta.tags ?? []).map((t) => (
                        <span key={t} style={{ fontSize: 11, background: "#1e293b", border: "1px solid #334155", borderRadius: 5, padding: "2px 8px", color: "#94a3b8" }}>
                          {t}
                        </span>
                      ))}
                    </div>
                  )}
                </div>
              )}

              <div style={{ padding: "16px 20px" }}>
                <div style={{ fontSize: 11, fontWeight: 700, color: "#475569", textTransform: "uppercase", letterSpacing: "0.06em", marginBottom: 8 }}>
                  Metadata
                </div>
                <MetaRow icon={<Calendar size={13} />} label="Date taken" value={data.file_created_at ? new Date(data.file_created_at).toLocaleString() : null} />
                <MetaRow icon={<MapPin size={13} />} label="Location" value={location || null} />
                <MetaRow icon={<Camera size={13} />} label="Camera" value={[data.camera_make, data.camera_model].filter(Boolean).join(" ") || null} />
                {data.description && <MetaRow icon={<Tag size={13} />} label="Description" value={data.description} />}
                {(data.tags ?? []).length > 0 && (
                  <MetaRow
                    icon={<Tag size={13} />}
                    label="Tags"
                    value={
                      <div style={{ display: "flex", gap: 5, flexWrap: "wrap", marginTop: 2 }}>
                        {(data.tags ?? []).map((t) => (
                          <span key={t} style={{ fontSize: 11, background: "#1e293b", border: "1px solid #334155", borderRadius: 5, padding: "2px 8px", color: "#94a3b8" }}>
                            {t}
                          </span>
                        ))}
                      </div>
                    }
                  />
                )}
                {(data.album_ids ?? []).length > 0 && (
                  <MetaRow icon={<Tag size={13} />} label="Albums" value={`${data.album_ids!.length} album${data.album_ids!.length !== 1 ? "s" : ""}`} />
                )}
                <MetaRow icon={<Tag size={13} />} label="MIME type" value={data.mime_type ?? null} />
                <MetaRow icon={<Clock size={13} />} label="Synced at" value={data.synced_at ? new Date(data.synced_at).toLocaleString() : null} />
                <MetaRow icon={<Tag size={13} />} label="Immich ID" value={
                  <span style={{ fontFamily: "monospace", fontSize: 11, color: "#64748b" }}>{data.immich_id}</span>
                } />
              </div>
            </>
          )}
        </div>
      </div>
    </>
  );
}

function AssetCard({
  asset, onClick, selected, onSelect,
}: {
  asset: Asset; onClick: () => void; selected: boolean; onSelect: (e: React.MouseEvent) => void;
}) {
  const [imgError, setImgError] = React.useState(false);
  const location = [asset.city, asset.country].filter(Boolean).join(", ");
  return (
    <div
      onClick={onClick}
      style={{
        background: selected ? "rgba(56,189,248,0.07)" : "#1e293b",
        border: `1px solid ${selected ? "#38bdf8" : "#334155"}`,
        borderRadius: 10, overflow: "hidden", cursor: "pointer",
        transition: "border-color 0.15s", position: "relative",
      }}
      onMouseEnter={(e) => { if (!selected) e.currentTarget.style.borderColor = "#38bdf8"; }}
      onMouseLeave={(e) => { if (!selected) e.currentTarget.style.borderColor = "#334155"; }}
    >
      {/* Selection checkbox */}
      <div
        onClick={onSelect}
        style={{
          position: "absolute", top: 6, left: 6, zIndex: 10,
          width: 20, height: 20, borderRadius: 5,
          background: selected ? "#38bdf8" : "rgba(0,0,0,0.5)",
          border: `2px solid ${selected ? "#38bdf8" : "rgba(255,255,255,0.3)"}`,
          display: "flex", alignItems: "center", justifyContent: "center",
          cursor: "pointer",
        }}
      >
        {selected && <CheckCircle size={14} color="#0f172a" />}
      </div>

      <div style={{ width: "100%", aspectRatio: "1", background: "#0f172a", position: "relative", overflow: "hidden" }}>
        {imgError ? (
          <div style={{ width: "100%", height: "100%", display: "flex", alignItems: "center", justifyContent: "center" }}>
            <ImageIcon size={28} color="#334155" />
          </div>
        ) : (
          <img
            src={getThumbnailUrl(asset.id)}
            alt={asset.original_filename || ""}
            onError={() => setImgError(true)}
            style={{ width: "100%", height: "100%", objectFit: "cover", display: "block" }}
          />
        )}
        {asset.is_favorite && (
          <Star size={12} color="#fbbf24" fill="#fbbf24" style={{ position: "absolute", top: 6, right: 6 }} />
        )}
      </div>
      <div style={{ padding: "10px 12px" }}>
        <div style={{ fontSize: 12, color: "#94a3b8", fontWeight: 500, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
          {asset.original_filename || asset.immich_id}
        </div>
        <div style={{ display: "flex", gap: 6, marginTop: 4, flexWrap: "wrap" }}>
          {asset.asset_type && (
            <span style={{ fontSize: 10, background: "#0ea5e918", color: "#38bdf8", border: "1px solid #0ea5e930", borderRadius: 4, padding: "1px 6px" }}>
              {asset.asset_type}
            </span>
          )}
          {location && <span style={{ fontSize: 10, color: "#64748b" }}>{location}</span>}
        </div>
        {(asset.tags ?? []).length > 0 && (
          <div style={{ fontSize: 10, color: "#64748b", marginTop: 3, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
            {asset.tags!.slice(0, 3).join(", ")}{asset.tags!.length > 3 ? " …" : ""}
          </div>
        )}
        {asset.description && (
          <div style={{ fontSize: 11, color: "#64748b", marginTop: 4, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
            {asset.description}
          </div>
        )}
      </div>
    </div>
  );
}

export default function Assets() {
  const [searchParams, setSearchParams] = useSearchParams();
  const [selectedAssetId, setSelectedAssetId] = React.useState<string | null>(null);
  const [selectedIds, setSelectedIds] = React.useState<Set<string>>(new Set());
  const [selectAllPages, setSelectAllPages] = React.useState(false);
  const [loadingAllIds, setLoadingAllIds] = React.useState(false);
  const [reclassifyMessage, setReclassifyMessage] = React.useState<string | null>(null);
  const qc = useQueryClient();
  const navigate = useNavigate();

  const page = parseInt(searchParams.get("page") || "1", 10);
  const assetType = searchParams.get("type") || "";
  const search = searchParams.get("q") || "";
  const bucketFilter = searchParams.get("bucket") || "";
  const sortKey = (searchParams.get("sort") as SortKey) || "date";
  const sortDir = (searchParams.get("dir") as SortDir) || "desc";
  const [searchInput, setSearchInput] = React.useState(search);

  function setParam(key: string, value: string) {
    setSearchParams((prev) => {
      const next = new URLSearchParams(prev);
      if (value) next.set(key, value); else next.delete(key);
      if (key !== "page") next.set("page", "1");
      return next;
    });
    setSelectedIds(new Set());
    setSelectAllPages(false);
  }

  function handleSort(key: SortKey) {
    if (key === sortKey) {
      setParam("dir", sortDir === "asc" ? "desc" : "asc");
    } else {
      setSearchParams((prev) => {
        const next = new URLSearchParams(prev);
        next.set("sort", key);
        next.set("dir", "asc");
        next.set("page", "1");
        return next;
      });
    }
  }

  // Server-side filters: asset_type, bucket_name
  const { data: assets = [], isLoading } = useQuery({
    queryKey: ["assets", page, assetType, bucketFilter],
    queryFn: () => getAssets({
      page,
      page_size: PAGE_SIZE,
      asset_type: assetType || undefined,
      bucket_name: bucketFilter || undefined,
    }),
  });

  const { data: countData } = useQuery({
    queryKey: ["asset-count", assetType, bucketFilter],
    queryFn: () => getAssetCount({
      asset_type: assetType || undefined,
      bucket_name: bucketFilter || undefined,
    }),
  });
  const totalPages = countData ? Math.ceil(countData.count / PAGE_SIZE) : 1;

  const { data: buckets = [] } = useQuery<Bucket[]>({
    queryKey: ["buckets"],
    queryFn: getBuckets,
  });

  const reclassifyMut = useMutation({
    mutationFn: (ids: string[]) => reclassifyAssets(ids, true),
    onSuccess: (data, ids) => {
      setReclassifyMessage(
        `Re-classification job started for ${ids.length} asset${ids.length !== 1 ? "s" : ""}. Job ID: ${data.job_id}`
      );
      setSelectedIds(new Set());
      setSelectAllPages(false);
      qc.invalidateQueries({ queryKey: ["jobs"] });
      setTimeout(() => setReclassifyMessage(null), 5000);
    },
  });

  // Client-side search filter only (server handles bucket/type)
  const filtered = search
    ? assets.filter((a) =>
        (a.original_filename || "").toLowerCase().includes(search.toLowerCase()) ||
        (a.description || "").toLowerCase().includes(search.toLowerCase()) ||
        (a.city || "").toLowerCase().includes(search.toLowerCase()) ||
        (a.tags || []).some((t) => t.toLowerCase().includes(search.toLowerCase()))
      )
    : assets;

  const sorted = sortAssets(filtered, sortKey, sortDir);

  function toggleSelect(id: string, e: React.MouseEvent) {
    e.stopPropagation();
    setSelectAllPages(false);
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id); else next.add(id);
      return next;
    });
  }

  function toggleSelectAll() {
    if (selectAllPages || selectedIds.size === sorted.length) {
      setSelectedIds(new Set());
      setSelectAllPages(false);
    } else {
      setSelectedIds(new Set(sorted.map((a) => a.id)));
    }
  }

  async function selectAcrossAllPages() {
    setLoadingAllIds(true);
    try {
      const result = await getAllAssetIds({
        asset_type: assetType || undefined,
        bucket_name: bucketFilter || undefined,
        q: search || undefined,
      });
      setSelectedIds(new Set(result.ids));
      setSelectAllPages(true);
    } finally {
      setLoadingAllIds(false);
    }
  }

  const allPageSelected = sorted.length > 0 && sorted.every((a) => selectedIds.has(a.id));
  const someSelected = selectedIds.size > 0;

  return (
    <div style={{ padding: "32px 40px" }}>
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 24 }}>
        <div>
          <h1 style={{ fontSize: 24, fontWeight: 700, color: "#f1f5f9", margin: 0 }}>Assets</h1>
          <p style={{ fontSize: 14, color: "#64748b", margin: "4px 0 0" }}>
            {countData ? `${countData.count.toLocaleString()} synced assets` : "Loading…"}
          </p>
        </div>
        {someSelected && (
          <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
            <span style={{ fontSize: 13, color: "#94a3b8" }}>{selectedIds.size} selected</span>
            <button
              onClick={() => reclassifyMut.mutate(Array.from(selectedIds))}
              disabled={reclassifyMut.isPending}
              style={{
                display: "flex", alignItems: "center", gap: 6,
                padding: "8px 16px", borderRadius: 8, border: "none",
                background: "#7c3aed", color: "white", fontSize: 13, fontWeight: 600,
                cursor: reclassifyMut.isPending ? "not-allowed" : "pointer",
                opacity: reclassifyMut.isPending ? 0.6 : 1,
              }}
            >
              <RefreshCw size={13} />
              {reclassifyMut.isPending ? "Starting…" : `Re-classify ${selectedIds.size}`}
            </button>
            <button
              onClick={() => { setSelectedIds(new Set()); setSelectAllPages(false); }}
              style={{ padding: "8px 12px", borderRadius: 8, border: "1px solid #334155", background: "transparent", color: "#64748b", fontSize: 13, cursor: "pointer" }}
            >
              Clear
            </button>
          </div>
        )}
      </div>

      {reclassifyMessage && (
        <div style={{
          marginBottom: 16, padding: "10px 16px", borderRadius: 8,
          background: "rgba(124,58,237,0.12)", border: "1px solid rgba(124,58,237,0.3)",
          fontSize: 13, color: "#c4b5fd",
          display: "flex", alignItems: "center", justifyContent: "space-between",
        }}>
          <span>{reclassifyMessage}</span>
          <button onClick={() => navigate("/jobs")} style={{ background: "none", border: "none", color: "#a78bfa", cursor: "pointer", fontSize: 12, textDecoration: "underline" }}>
            View Jobs
          </button>
        </div>
      )}

      {/* Filters */}
      <div style={{ display: "flex", gap: 10, marginBottom: 12, flexWrap: "wrap" }}>
        <div style={{ position: "relative", flex: "1 1 240px" }}>
          <Search size={14} color="#64748b" style={{ position: "absolute", left: 10, top: "50%", transform: "translateY(-50%)" }} />
          <input
            value={searchInput}
            onChange={(e) => setSearchInput(e.target.value)}
            onKeyDown={(e) => { if (e.key === "Enter") setParam("q", searchInput); }}
            onBlur={() => setParam("q", searchInput)}
            placeholder="Search filename, description, location, tags…"
            style={{
              width: "100%", paddingLeft: 32, padding: "8px 12px 8px 32px",
              background: "#1e293b", border: "1px solid #334155",
              borderRadius: 8, color: "#f1f5f9", fontSize: 13, outline: "none", boxSizing: "border-box",
            }}
          />
        </div>
        <select
          value={assetType}
          onChange={(e) => setParam("type", e.target.value)}
          style={{ background: "#1e293b", border: "1px solid #334155", color: "#94a3b8", borderRadius: 8, padding: "8px 12px", fontSize: 13 }}
        >
          <option value="">All types</option>
          <option value="IMAGE">Images</option>
          <option value="VIDEO">Videos</option>
        </select>
        <select
          value={bucketFilter}
          onChange={(e) => setParam("bucket", e.target.value)}
          style={{ background: "#1e293b", border: "1px solid #334155", color: "#94a3b8", borderRadius: 8, padding: "8px 12px", fontSize: 13 }}
        >
          <option value="">All buckets</option>
          {buckets.map((b) => (
            <option key={b.id} value={b.name}>{b.name}</option>
          ))}
        </select>
      </div>

      {/* Sort bar + select all */}
      <div style={{ display: "flex", gap: 4, marginBottom: 16, alignItems: "center", flexWrap: "wrap", justifyContent: "space-between" }}>
        <div style={{ display: "flex", gap: 4, alignItems: "center", flexWrap: "wrap" }}>
          <span style={{ fontSize: 12, color: "#475569", marginRight: 4 }}>Sort:</span>
          {(Object.keys(SORT_LABELS) as SortKey[]).map((k) => (
            <SortHeader key={k} label={SORT_LABELS[k]} sortKey={k} current={sortKey} dir={sortDir} onChange={handleSort} />
          ))}
        </div>
        {sorted.length > 0 && (
          <button
            onClick={toggleSelectAll}
            style={{
              fontSize: 12, color: "#64748b", background: "transparent", border: "1px solid #334155",
              borderRadius: 6, padding: "4px 10px", cursor: "pointer",
            }}
          >
            {(selectAllPages || allPageSelected) ? "Deselect all" : `Select all ${sorted.length}`}
          </button>
        )}
      </div>

      {/* Cross-page select-all banner */}
      {allPageSelected && !selectAllPages && countData && countData.count > sorted.length && (
        <div style={{
          marginBottom: 12, padding: "10px 16px", borderRadius: 8,
          background: "rgba(56,189,248,0.08)", border: "1px solid rgba(56,189,248,0.25)",
          fontSize: 13, color: "#7dd3fc",
          display: "flex", alignItems: "center", justifyContent: "space-between", gap: 12,
        }}>
          <span>All {sorted.length} assets on this page are selected.</span>
          <button
            onClick={selectAcrossAllPages}
            disabled={loadingAllIds}
            style={{ background: "none", border: "none", color: "#38bdf8", cursor: "pointer", fontSize: 13, fontWeight: 600, whiteSpace: "nowrap" }}
          >
            {loadingAllIds ? "Loading…" : `Select all ${countData.count.toLocaleString()} assets`}
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
          <span>All {selectedIds.size.toLocaleString()} matching assets are selected.</span>
          <button
            onClick={() => { setSelectedIds(new Set()); setSelectAllPages(false); }}
            style={{ background: "none", border: "none", color: "#38bdf8", cursor: "pointer", fontSize: 13, fontWeight: 600 }}
          >
            Clear selection
          </button>
        </div>
      )}

      {isLoading ? (
        <div style={{ color: "#64748b", textAlign: "center", padding: 64 }}>Loading…</div>
      ) : sorted.length === 0 ? (
        <div style={{ textAlign: "center", padding: 64, color: "#64748b" }}>No assets found.</div>
      ) : (
        <>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(160px, 1fr))", gap: 12, marginBottom: 24 }}>
            {sorted.map((a) => (
              <AssetCard
                key={a.id}
                asset={a}
                selected={selectedIds.has(a.id)}
                onSelect={(e) => toggleSelect(a.id, e)}
                onClick={() => setSelectedAssetId(a.id)}
              />
            ))}
          </div>

          <div style={{ display: "flex", gap: 8, justifyContent: "center", alignItems: "center" }}>
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

      {selectedAssetId && (
        <AssetDetailPanel
          assetId={selectedAssetId}
          onClose={() => setSelectedAssetId(null)}
          onReclassify={(ids) => {
            setSelectedAssetId(null);
            reclassifyMut.mutate(ids);
          }}
        />
      )}
    </div>
  );
}
