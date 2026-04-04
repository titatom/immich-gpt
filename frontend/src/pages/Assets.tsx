import React from "react";
import { useQuery } from "@tanstack/react-query";
import { useSearchParams } from "react-router-dom";
import { getAssets, getAssetCount, getThumbnailUrl } from "../services/api";
import type { Asset } from "../types";
import { Search, Image as ImageIcon, ArrowUp, ArrowDown, ArrowUpDown } from "lucide-react";

const PAGE_SIZE = 50;

type SortKey = "date" | "filename" | "location" | "tags" | "album" | "type";
type SortDir = "asc" | "desc";

function sortAssets(assets: Asset[], key: SortKey, dir: SortDir): Asset[] {
  const factor = dir === "asc" ? 1 : -1;
  return [...assets].sort((a, b) => {
    let va: string;
    let vb: string;
    switch (key) {
      case "date":
        va = a.file_created_at ?? a.created_at ?? "";
        vb = b.file_created_at ?? b.created_at ?? "";
        break;
      case "filename":
        va = a.original_filename ?? "";
        vb = b.original_filename ?? "";
        break;
      case "location":
        va = [a.city, a.country].filter(Boolean).join(", ");
        vb = [b.city, b.country].filter(Boolean).join(", ");
        break;
      case "tags":
        va = (a.tags ?? []).join(", ");
        vb = (b.tags ?? []).join(", ");
        break;
      case "album":
        va = (a.album_ids ?? []).join(",");
        vb = (b.album_ids ?? []).join(",");
        break;
      case "type":
        va = a.asset_type ?? "";
        vb = b.asset_type ?? "";
        break;
      default:
        va = "";
        vb = "";
    }
    if (!va && vb) return 1;
    if (va && !vb) return -1;
    if (!va && !vb) return 0;
    return factor * va.localeCompare(vb);
  });
}

const SORT_LABELS: Record<SortKey, string> = {
  date: "Date",
  filename: "Filename",
  location: "Location",
  tags: "Tags",
  album: "Album",
  type: "Type",
};

function SortHeader({ label, sortKey, current, dir, onChange }: {
  label: string; sortKey: SortKey;
  current: SortKey; dir: SortDir;
  onChange: (k: SortKey) => void;
}) {
  const active = current === sortKey;
  return (
    <button
      onClick={() => onChange(sortKey)}
      style={{
        display: "flex", alignItems: "center", gap: 4,
        background: active ? "rgba(56,189,248,0.08)" : "transparent",
        border: "none", cursor: "pointer",
        color: active ? "#38bdf8" : "#64748b",
        fontSize: 12, fontWeight: active ? 600 : 400, padding: "4px 8px",
        borderRadius: 6,
      }}
    >
      {label}
      {active
        ? (dir === "asc" ? <ArrowUp size={11} /> : <ArrowDown size={11} />)
        : <ArrowUpDown size={11} />}
    </button>
  );
}

function AssetCard({ asset }: { asset: Asset }) {
  const [imgError, setImgError] = React.useState(false);
  const location = [asset.city, asset.country].filter(Boolean).join(", ");
  return (
    <div style={{ background: "#1e293b", border: "1px solid #334155", borderRadius: 10, overflow: "hidden" }}>
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
        {(asset.album_ids ?? []).length > 0 && (
          <div style={{ fontSize: 10, color: "#475569", marginTop: 2 }}>
            {asset.album_ids!.length} album{asset.album_ids!.length !== 1 ? "s" : ""}
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

  const page = parseInt(searchParams.get("page") || "1", 10);
  const assetType = searchParams.get("type") || "";
  const search = searchParams.get("q") || "";
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

  const { data: assets = [], isLoading } = useQuery({
    queryKey: ["assets", page, assetType],
    queryFn: () => getAssets({ page, page_size: PAGE_SIZE, asset_type: assetType || undefined }),
  });

  const { data: countData } = useQuery({ queryKey: ["asset-count"], queryFn: getAssetCount });

  const totalPages = countData ? Math.ceil(countData.count / PAGE_SIZE) : 1;

  // Client-side filter then sort
  const filtered = search
    ? assets.filter((a) =>
        (a.original_filename || "").toLowerCase().includes(search.toLowerCase()) ||
        (a.description || "").toLowerCase().includes(search.toLowerCase()) ||
        (a.city || "").toLowerCase().includes(search.toLowerCase()) ||
        (a.tags || []).some((t) => t.toLowerCase().includes(search.toLowerCase()))
      )
    : assets;

  const sorted = sortAssets(filtered, sortKey, sortDir);

  return (
    <div style={{ padding: "32px 40px" }}>
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 24 }}>
        <div>
          <h1 style={{ fontSize: 24, fontWeight: 700, color: "#f1f5f9", margin: 0 }}>Assets</h1>
          <p style={{ fontSize: 14, color: "#64748b", margin: "4px 0 0" }}>
            {countData ? `${countData.count.toLocaleString()} synced assets` : "Loading…"}
          </p>
        </div>
      </div>

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
      </div>

      {/* Sort bar */}
      <div style={{ display: "flex", gap: 4, marginBottom: 16, alignItems: "center", flexWrap: "wrap" }}>
        <span style={{ fontSize: 12, color: "#475569", marginRight: 4 }}>Sort:</span>
        {(Object.keys(SORT_LABELS) as SortKey[]).map((k) => (
          <SortHeader key={k} label={SORT_LABELS[k]} sortKey={k} current={sortKey} dir={sortDir} onChange={handleSort} />
        ))}
      </div>

      {isLoading ? (
        <div style={{ color: "#64748b", textAlign: "center", padding: 64 }}>Loading…</div>
      ) : sorted.length === 0 ? (
        <div style={{ textAlign: "center", padding: 64, color: "#64748b" }}>No assets found.</div>
      ) : (
        <>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(160px, 1fr))", gap: 12, marginBottom: 24 }}>
            {sorted.map((a) => <AssetCard key={a.id} asset={a} />)}
          </div>

          {/* Pagination */}
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
    </div>
  );
}
