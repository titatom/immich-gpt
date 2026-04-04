import React from "react";
import { useQuery } from "@tanstack/react-query";
import { useSearchParams } from "react-router-dom";
import { getAssets, getAssetCount, getThumbnailUrl } from "../services/api";
import type { Asset } from "../types";
import { Search, Image as ImageIcon } from "lucide-react";

const PAGE_SIZE = 50;

function AssetCard({ asset }: { asset: Asset }) {
  const [imgError, setImgError] = React.useState(false);
  return (
    <div style={{
      background: "#1e293b",
      border: "1px solid #334155",
      borderRadius: 10,
      overflow: "hidden",
    }}>
      <div style={{
        width: "100%",
        aspectRatio: "1",
        background: "#0f172a",
        position: "relative",
        overflow: "hidden",
      }}>
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
          {asset.city && (
            <span style={{ fontSize: 10, color: "#64748b" }}>{asset.city}{asset.country ? `, ${asset.country}` : ""}</span>
          )}
        </div>
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
  const [searchInput, setSearchInput] = React.useState(search);

  function setParam(key: string, value: string) {
    setSearchParams((prev) => {
      const next = new URLSearchParams(prev);
      if (value) next.set(key, value);
      else next.delete(key);
      if (key !== "page") next.set("page", "1");
      return next;
    });
  }

  const { data: assets = [], isLoading } = useQuery({
    queryKey: ["assets", page, assetType],
    queryFn: () => getAssets({ page, page_size: PAGE_SIZE, asset_type: assetType || undefined }),
  });

  const { data: countData } = useQuery({
    queryKey: ["asset-count"],
    queryFn: getAssetCount,
  });

  const totalPages = countData ? Math.ceil(countData.count / PAGE_SIZE) : 1;

  // Client-side filename filter (no full-text search endpoint yet)
  const filtered = search
    ? assets.filter((a) =>
        (a.original_filename || "").toLowerCase().includes(search.toLowerCase()) ||
        (a.description || "").toLowerCase().includes(search.toLowerCase())
      )
    : assets;

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
      <div style={{ display: "flex", gap: 10, marginBottom: 20, flexWrap: "wrap" }}>
        <div style={{ position: "relative", flex: "1 1 240px" }}>
          <Search size={14} color="#64748b" style={{ position: "absolute", left: 10, top: "50%", transform: "translateY(-50%)" }} />
          <input
            value={searchInput}
            onChange={(e) => setSearchInput(e.target.value)}
            onKeyDown={(e) => { if (e.key === "Enter") setParam("q", searchInput); }}
            onBlur={() => setParam("q", searchInput)}
            placeholder="Search filename or description…"
            style={{
              width: "100%",
              paddingLeft: 32,
              padding: "8px 12px 8px 32px",
              background: "#1e293b",
              border: "1px solid #334155",
              borderRadius: 8,
              color: "#f1f5f9",
              fontSize: 13,
              outline: "none",
              boxSizing: "border-box",
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

      {isLoading ? (
        <div style={{ color: "#64748b", textAlign: "center", padding: 64 }}>Loading…</div>
      ) : filtered.length === 0 ? (
        <div style={{ textAlign: "center", padding: 64, color: "#64748b" }}>No assets found.</div>
      ) : (
        <>
          <div style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fill, minmax(160px, 1fr))",
            gap: 12,
            marginBottom: 24,
          }}>
            {filtered.map((a) => <AssetCard key={a.id} asset={a} />)}
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
