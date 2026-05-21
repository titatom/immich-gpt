import React from "react";
import { useQuery } from "@tanstack/react-query";
import { useSearchParams } from "react-router-dom";
import {
  getAssets, getAssetCount, getThumbnailUrl,
} from "../services/api";
import type { Asset } from "../types";
  Search, Image as ImageIcon, ArrowUp, ArrowDown, ArrowUpDown,
  X, Star, Archive, ExternalLink, Camera, MapPin, Tag, Calendar, Clock,
} from "lucide-react";

const PAGE_SIZE = 50;

type SortKey = "date" | "filename" | "location" | "tags" | "type";
type SortDir = "asc" | "desc";

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

function AssetDetailPanel({ asset, onClose }: { asset: Asset; onClose: () => void }) {
  const [imgError, setImgError] = React.useState(false);

  React.useEffect(() => {
    const handler = (e: KeyboardEvent) => { if (e.key === "Escape") onClose(); };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [onClose]);

  const location = [asset.city, asset.country].filter(Boolean).join(", ");

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
            {asset.original_filename || asset.immich_id}
          </div>
          <button onClick={onClose} style={{ background: "none", border: "none", cursor: "pointer", color: "#64748b", padding: 4 }}>
            <X size={18} />
          </button>
        </div>

        <div style={{ flex: 1, overflowY: "auto" }}>
          <div style={{ background: "#000", position: "relative", aspectRatio: "16/9", overflow: "hidden", flexShrink: 0 }}>
            {imgError ? (
              <div style={{ width: "100%", height: "100%", display: "flex", alignItems: "center", justifyContent: "center" }}>
                <ImageIcon size={48} color="#334155" />
              </div>
            ) : (
              <img
                src={getThumbnailUrl(asset.id, "preview")}
                alt={asset.original_filename || ""}
                decoding="async"
                onError={() => setImgError(true)}
                style={{ width: "100%", height: "100%", objectFit: "contain", display: "block" }}
              />
            )}
            <div style={{ position: "absolute", top: 8, left: 8, display: "flex", gap: 6 }}>
              {asset.is_favorite && (
                <span style={{ background: "rgba(0,0,0,0.6)", borderRadius: 6, padding: "3px 7px", display: "flex", alignItems: "center", gap: 4 }}>
                  <Star size={11} color="#fbbf24" fill="#fbbf24" />
                </span>
              )}
              {asset.is_archived && (
                <span style={{ background: "rgba(0,0,0,0.6)", borderRadius: 6, padding: "3px 7px", display: "flex", alignItems: "center", gap: 4 }}>
                  <Archive size={11} color="#94a3b8" />
                </span>
              )}
              {asset.is_external_library && (
                <span style={{ background: "rgba(0,0,0,0.6)", borderRadius: 6, padding: "3px 7px", display: "flex", alignItems: "center", gap: 4 }}>
                  <ExternalLink size={11} color="#94a3b8" />
                </span>
              )}
            </div>
            {asset.asset_type && (
              <span style={{
                position: "absolute", bottom: 8, right: 8,
                background: "rgba(0,0,0,0.6)", borderRadius: 6, padding: "3px 8px",
                fontSize: 11, fontWeight: 600, color: "#38bdf8",
              }}>
                {asset.asset_type}
              </span>
            )}
          </div>

          <div style={{ padding: "16px 20px" }}>
            <div style={{ fontSize: 11, fontWeight: 700, color: "#475569", textTransform: "uppercase", letterSpacing: "0.06em", marginBottom: 8 }}>
              Metadata
            </div>
            <MetaRow icon={<Calendar size={13} />} label="Date taken" value={asset.file_created_at ? new Date(asset.file_created_at).toLocaleString() : null} />
            <MetaRow icon={<MapPin size={13} />} label="Location" value={location || null} />
            <MetaRow icon={<Camera size={13} />} label="Camera" value={[asset.camera_make, asset.camera_model].filter(Boolean).join(" ") || null} />
            {asset.description && <MetaRow icon={<Tag size={13} />} label="Description" value={asset.description} />}
            {(asset.tags ?? []).length > 0 && (
              <MetaRow
                icon={<Tag size={13} />}
                label="Tags"
                value={
                  <div style={{ display: "flex", gap: 5, flexWrap: "wrap", marginTop: 2 }}>
                    {(asset.tags ?? []).map((t) => (
                      <span key={t} style={{ fontSize: 11, background: "#1e293b", border: "1px solid #334155", borderRadius: 5, padding: "2px 8px", color: "#94a3b8" }}>
                        {t}
                      </span>
                    ))}
                  </div>
                }
              />
            )}
            {(asset.album_ids ?? []).length > 0 && (
              <MetaRow icon={<Tag size={13} />} label="Albums" value={`${asset.album_ids!.length} album${asset.album_ids!.length !== 1 ? "s" : ""}`} />
            )}
            <MetaRow icon={<Tag size={13} />} label="MIME type" value={asset.mime_type ?? null} />
            <MetaRow icon={<Clock size={13} />} label="Synced at" value={asset.synced_at ? new Date(asset.synced_at).toLocaleString() : null} />
            <MetaRow icon={<Tag size={13} />} label="Immich ID" value={
              <span style={{ fontFamily: "monospace", fontSize: 11, color: "#64748b" }}>{asset.immich_id}</span>
            } />
          </div>
        </div>
      </div>
    </>
  );
}

function AssetCard({ asset, onClick }: { asset: Asset; onClick: () => void }) {
  const [imgError, setImgError] = React.useState(false);
  const location = [asset.city, asset.country].filter(Boolean).join(", ");
  return (
    <div
      onClick={onClick}
      style={{
        background: "#1e293b",
        border: "1px solid #334155",
        borderRadius: 10, overflow: "hidden", cursor: "pointer",
        transition: "border-color 0.15s", position: "relative",
      }}
      onMouseEnter={(e) => { e.currentTarget.style.borderColor = "#38bdf8"; }}
      onMouseLeave={(e) => { e.currentTarget.style.borderColor = "#334155"; }}
    >
      <div style={{ width: "100%", aspectRatio: "1", background: "#0f172a", position: "relative", overflow: "hidden" }}>
        {imgError ? (
          <div style={{ width: "100%", height: "100%", display: "flex", alignItems: "center", justifyContent: "center" }}>
            <ImageIcon size={28} color="#334155" />
          </div>
        ) : (
          <img
            src={getThumbnailUrl(asset.id)}
            alt={asset.original_filename || ""}
            loading="lazy"
            decoding="async"
            onError={() => setImgError(true)}
            style={{ width: "100%", height: "100%", objectFit: "cover", display: "block" }}
          />
        )}
        {asset.is_favorite && (
          <Star size={12} color="#fbbf24" fill="#fbbf24" style={{ position: "absolute", top: 6, right: 6 }} />
        )}
      </div>
      <div style={{ padding: "8px 10px" }}>
        <div style={{ fontSize: 11, color: "#94a3b8", fontWeight: 500, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
          {asset.original_filename || asset.immich_id}
        </div>
        <div style={{ display: "flex", gap: 5, marginTop: 3, flexWrap: "wrap" }}>
          {asset.asset_type && (
            <span style={{ fontSize: 9, background: "#0ea5e918", color: "#38bdf8", border: "1px solid #0ea5e930", borderRadius: 4, padding: "1px 5px" }}>
              {asset.asset_type}
            </span>
          )}
          {location && <span style={{ fontSize: 9, color: "#64748b" }}>{location}</span>}
        </div>
      </div>
    </div>
  );
}

export default function Assets() {
  const [searchParams, setSearchParams] = useSearchParams();
  const [selectedAssetId, setSelectedAssetId] = React.useState<string | null>(null);

  const page = parseInt(searchParams.get("page") || "1", 10);
  const assetType = searchParams.get("type") || "";
  const search = searchParams.get("q") || "";
  const sortKey = (searchParams.get("sort") as SortKey) || "date";
  const sortDir = (searchParams.get("dir") as SortDir) || "desc";
  const [searchInput, setSearchInput] = React.useState(search);
  React.useEffect(() => { setSearchInput(search); }, [search]);

  function setParam(key: string, value: string) {
    setSearchParams((prev) => {
      const next = new URLSearchParams(prev);
      if (value) next.set(key, value); else next.delete(key);
      if (key !== "page") next.set("page", "1");
      return next;
    });
  }

  function setSort(key: SortKey) {
    if (key === sortKey) {
      setSearchParams((prev) => {
        const next = new URLSearchParams(prev);
        next.set("dir", sortDir === "asc" ? "desc" : "asc");
        return next;
      });
    } else {
      setSearchParams((prev) => {
        const next = new URLSearchParams(prev);
        next.set("sort", key);
        next.set("dir", "desc");
        return next;
      });
    }
  }

  const queryParams = {
    page,
    page_size: PAGE_SIZE,
    asset_type: assetType || undefined,
    q: search || undefined,
    sort: sortKey,
    dir: sortDir,
  };

  const countQueryParams = {
    asset_type: assetType || undefined,
    q: search || undefined,
  };

  const { data: assets = [], isLoading, isError: assetsError } = useQuery<Asset[]>({
    queryKey: ["assets", queryParams],
    queryFn: () => getAssets(queryParams),
  });

  const { data: countData } = useQuery<{ count: number }>({
    queryKey: ["asset-count", countQueryParams],
    queryFn: () => getAssetCount(countQueryParams),
  });

  const total = countData?.count ?? 0;
  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE));
  const selected = assets.find((a) => a.id === selectedAssetId);

  function submitSearch(e: React.FormEvent) {
    e.preventDefault();
    setParam("q", searchInput.trim());
  }

  return (
    <div style={{ padding: "32px 40px", maxWidth: 1400, margin: "0 auto" }}>
      <div style={{ marginBottom: 20 }}>
        <h1 style={{ fontSize: 24, fontWeight: 700, color: "#f1f5f9", margin: 0 }}>Assets</h1>
        <p style={{ fontSize: 14, color: "#64748b", margin: "4px 0 0" }}>
          Browse synced Immich assets. Routing decisions live under{" "}
          <a href="/routing/plans" style={{ color: "#38bdf8" }}>Routing plans</a>.
        </p>
      </div>

      <div style={{ display: "flex", flexWrap: "wrap", gap: 8, alignItems: "center", marginBottom: 16 }}>
        <form onSubmit={submitSearch} style={{ flex: "1 1 240px", display: "flex", alignItems: "center", gap: 6, background: "#1e293b", border: "1px solid #334155", borderRadius: 8, padding: "6px 10px" }}>
          <Search size={14} color="#64748b" />
          <input
            value={searchInput}
            onChange={(e) => setSearchInput(e.target.value)}
            placeholder="Search filename, description, location…"
            style={{ flex: 1, background: "transparent", border: "none", outline: "none", color: "#e2e8f0", fontSize: 13 }}
          />
        </form>
        <select
          value={assetType}
          onChange={(e) => setParam("type", e.target.value)}
          style={{ padding: "8px 12px", borderRadius: 8, background: "#1e293b", border: "1px solid #334155", color: "#e2e8f0", fontSize: 13 }}
        >
          <option value="">Any type</option>
          <option value="IMAGE">Image</option>
          <option value="VIDEO">Video</option>
        </select>
        <div style={{ display: "flex", gap: 4, alignItems: "center" }}>
          <SortHeader label="Date" sortKey="date" current={sortKey} dir={sortDir} onChange={setSort} />
          <SortHeader label="Filename" sortKey="filename" current={sortKey} dir={sortDir} onChange={setSort} />
          <SortHeader label="Location" sortKey="location" current={sortKey} dir={sortDir} onChange={setSort} />
          <SortHeader label="Type" sortKey="type" current={sortKey} dir={sortDir} onChange={setSort} />
        </div>
      </div>

      {isLoading ? (
        <div style={{ padding: 40, textAlign: "center", color: "#64748b" }}>Loading assets…</div>
      ) : assetsError ? (
        <div style={{ padding: 60, textAlign: "center", color: "#fca5a5", fontSize: 13 }}>Failed to load assets.</div>
      ) : assets.length === 0 ? (
        <div style={{ padding: 60, textAlign: "center", color: "#64748b", fontSize: 13 }}>
          No assets match the current filter. Sync your Immich library from the dashboard.
        </div>
      ) : (
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(160px, 1fr))", gap: 12 }}>
          {assets.map((asset) => (
            <AssetCard
              key={asset.id}
              asset={asset}
              onClick={() => setSelectedAssetId(asset.id)}
            />
          ))}
        </div>
      )}

      {totalPages > 1 && (
        <div style={{ display: "flex", justifyContent: "center", gap: 6, marginTop: 24 }}>
          <button
            onClick={() => setParam("page", String(Math.max(1, page - 1)))}
            disabled={page <= 1}
            style={{ padding: "5px 12px", borderRadius: 6, border: "1px solid #334155", background: "transparent", color: "#94a3b8", cursor: page > 1 ? "pointer" : "not-allowed", fontSize: 12, opacity: page > 1 ? 1 : 0.4 }}
          >
            Previous
          </button>
          <span style={{ fontSize: 12, color: "#64748b", padding: "5px 12px" }}>
            Page {page} of {totalPages} · {total.toLocaleString()} total
          </span>
          <button
            onClick={() => setParam("page", String(Math.min(totalPages, page + 1)))}
            disabled={page >= totalPages}
            style={{ padding: "5px 12px", borderRadius: 6, border: "1px solid #334155", background: "transparent", color: "#94a3b8", cursor: page < totalPages ? "pointer" : "not-allowed", fontSize: 12, opacity: page < totalPages ? 1 : 0.4 }}
          >
            Next
          </button>
        </div>
      )}

      {selected && (
        <AssetDetailPanel
          asset={selected}
          onClose={() => setSelectedAssetId(null)}
        />
      )}
    </div>
  );
}
