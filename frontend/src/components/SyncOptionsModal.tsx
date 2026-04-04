import React, { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { X, RefreshCw, Star, FolderOpen, ChevronDown, ChevronUp, Loader } from "lucide-react";
import { getAlbums } from "../services/api";
import type { SyncScope, ImmichAlbum } from "../types";

interface Props {
  onClose: () => void;
  onConfirm: (scope: SyncScope, albumIds?: string[]) => void;
  isLoading?: boolean;
}

const CARD_STYLE: React.CSSProperties = {
  background: "#1e293b",
  border: "1px solid #334155",
  borderRadius: 10,
  padding: "14px 16px",
  cursor: "pointer",
  transition: "border-color 0.15s",
  userSelect: "none",
};

const SELECTED_CARD_STYLE: React.CSSProperties = {
  ...CARD_STYLE,
  border: "1px solid #3b82f6",
  background: "#1e3a5f",
};

export default function SyncOptionsModal({ onClose, onConfirm, isLoading = false }: Props) {
  const [scope, setScope] = useState<SyncScope>("all");
  const [selectedAlbumIds, setSelectedAlbumIds] = useState<Set<string>>(new Set());
  const [albumSearchQuery, setAlbumSearchQuery] = useState("");
  const [albumsExpanded, setAlbumsExpanded] = useState(true);

  const { data: albums = [], isLoading: albumsLoading } = useQuery<ImmichAlbum[]>({
    queryKey: ["albums"],
    queryFn: getAlbums,
  });

  const filteredAlbums = albums.filter((a) =>
    a.albumName.toLowerCase().includes(albumSearchQuery.toLowerCase())
  );

  const toggleAlbum = (id: string) => {
    setSelectedAlbumIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) {
        next.delete(id);
      } else {
        next.add(id);
      }
      return next;
    });
  };

  const handleConfirm = () => {
    if (scope === "albums") {
      onConfirm(scope, Array.from(selectedAlbumIds));
    } else {
      onConfirm(scope);
    }
  };

  const isConfirmDisabled =
    isLoading || (scope === "albums" && selectedAlbumIds.size === 0);

  return (
    <div
      style={{
        position: "fixed",
        inset: 0,
        background: "rgba(0,0,0,0.6)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        zIndex: 1000,
      }}
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <div
        style={{
          background: "#0f172a",
          border: "1px solid #334155",
          borderRadius: 14,
          width: "min(520px, calc(100vw - 32px))",
          maxHeight: "80vh",
          display: "flex",
          flexDirection: "column",
          overflow: "hidden",
        }}
      >
        {/* Header */}
        <div
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            padding: "18px 20px",
            borderBottom: "1px solid #1e293b",
            flexShrink: 0,
          }}
        >
          <div>
            <h2 style={{ margin: 0, fontSize: 16, fontWeight: 700, color: "#f1f5f9" }}>
              Sync Options
            </h2>
            <p style={{ margin: "2px 0 0", fontSize: 12, color: "#64748b" }}>
              Choose what to sync from Immich
            </p>
          </div>
          <button
            onClick={onClose}
            style={{
              background: "none",
              border: "none",
              cursor: "pointer",
              color: "#64748b",
              padding: 4,
              display: "flex",
              alignItems: "center",
            }}
          >
            <X size={18} />
          </button>
        </div>

        {/* Scrollable body */}
        <div style={{ padding: "18px 20px", overflowY: "auto", flex: 1 }}>
          {/* Scope options */}
          <div style={{ display: "flex", flexDirection: "column", gap: 10, marginBottom: 20 }}>
            {/* All photos */}
            <div
              style={scope === "all" ? SELECTED_CARD_STYLE : CARD_STYLE}
              onClick={() => setScope("all")}
            >
              <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                <div
                  style={{
                    width: 32,
                    height: 32,
                    borderRadius: 8,
                    background: scope === "all" ? "#1e40af" : "#1e293b",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    flexShrink: 0,
                    border: "1px solid #334155",
                  }}
                >
                  <RefreshCw size={15} color={scope === "all" ? "#93c5fd" : "#64748b"} />
                </div>
                <div>
                  <div style={{ fontSize: 14, fontWeight: 600, color: "#f1f5f9" }}>All Photos &amp; Videos</div>
                  <div style={{ fontSize: 12, color: "#64748b", marginTop: 2 }}>
                    Sync every asset in your Immich library
                  </div>
                </div>
                <div
                  style={{
                    marginLeft: "auto",
                    width: 16,
                    height: 16,
                    borderRadius: "50%",
                    border: `2px solid ${scope === "all" ? "#3b82f6" : "#475569"}`,
                    background: scope === "all" ? "#3b82f6" : "transparent",
                    flexShrink: 0,
                  }}
                />
              </div>
            </div>

            {/* Favorites */}
            <div
              style={scope === "favorites" ? SELECTED_CARD_STYLE : CARD_STYLE}
              onClick={() => setScope("favorites")}
            >
              <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                <div
                  style={{
                    width: 32,
                    height: 32,
                    borderRadius: 8,
                    background: scope === "favorites" ? "#78350f" : "#1e293b",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    flexShrink: 0,
                    border: "1px solid #334155",
                  }}
                >
                  <Star size={15} color={scope === "favorites" ? "#fbbf24" : "#64748b"} />
                </div>
                <div>
                  <div style={{ fontSize: 14, fontWeight: 600, color: "#f1f5f9" }}>Favourites Only</div>
                  <div style={{ fontSize: 12, color: "#64748b", marginTop: 2 }}>
                    Sync only assets you have marked as favourite
                  </div>
                </div>
                <div
                  style={{
                    marginLeft: "auto",
                    width: 16,
                    height: 16,
                    borderRadius: "50%",
                    border: `2px solid ${scope === "favorites" ? "#3b82f6" : "#475569"}`,
                    background: scope === "favorites" ? "#3b82f6" : "transparent",
                    flexShrink: 0,
                  }}
                />
              </div>
            </div>

            {/* Albums */}
            <div
              style={scope === "albums" ? SELECTED_CARD_STYLE : CARD_STYLE}
              onClick={() => setScope("albums")}
            >
              <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                <div
                  style={{
                    width: 32,
                    height: 32,
                    borderRadius: 8,
                    background: scope === "albums" ? "#1e3a5f" : "#1e293b",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    flexShrink: 0,
                    border: "1px solid #334155",
                  }}
                >
                  <FolderOpen size={15} color={scope === "albums" ? "#60a5fa" : "#64748b"} />
                </div>
                <div>
                  <div style={{ fontSize: 14, fontWeight: 600, color: "#f1f5f9" }}>Specific Albums</div>
                  <div style={{ fontSize: 12, color: "#64748b", marginTop: 2 }}>
                    Choose one or more albums to sync
                  </div>
                </div>
                <div
                  style={{
                    marginLeft: "auto",
                    width: 16,
                    height: 16,
                    borderRadius: "50%",
                    border: `2px solid ${scope === "albums" ? "#3b82f6" : "#475569"}`,
                    background: scope === "albums" ? "#3b82f6" : "transparent",
                    flexShrink: 0,
                  }}
                />
              </div>
            </div>
          </div>

          {/* Album picker — only when "albums" scope is selected */}
          {scope === "albums" && (
            <div
              style={{
                border: "1px solid #334155",
                borderRadius: 10,
                overflow: "hidden",
              }}
            >
              <div
                style={{
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "space-between",
                  padding: "10px 14px",
                  background: "#1e293b",
                  cursor: "pointer",
                }}
                onClick={() => setAlbumsExpanded((v) => !v)}
              >
                <span style={{ fontSize: 13, fontWeight: 600, color: "#94a3b8" }}>
                  Albums
                  {selectedAlbumIds.size > 0 && (
                    <span
                      style={{
                        marginLeft: 8,
                        fontSize: 11,
                        background: "#1e40af",
                        color: "#93c5fd",
                        borderRadius: 6,
                        padding: "1px 7px",
                      }}
                    >
                      {selectedAlbumIds.size} selected
                    </span>
                  )}
                </span>
                {albumsExpanded ? (
                  <ChevronUp size={14} color="#64748b" />
                ) : (
                  <ChevronDown size={14} color="#64748b" />
                )}
              </div>

              {albumsExpanded && (
                <>
                  <div style={{ padding: "10px 14px", borderTop: "1px solid #1e293b" }}>
                    <input
                      type="text"
                      placeholder="Search albums…"
                      value={albumSearchQuery}
                      onChange={(e) => setAlbumSearchQuery(e.target.value)}
                      style={{
                        width: "100%",
                        boxSizing: "border-box",
                        background: "#0f172a",
                        border: "1px solid #334155",
                        borderRadius: 6,
                        padding: "7px 10px",
                        fontSize: 13,
                        color: "#f1f5f9",
                        outline: "none",
                      }}
                    />
                  </div>

                  <div
                    style={{
                      maxHeight: 220,
                      overflowY: "auto",
                      borderTop: "1px solid #1e293b",
                    }}
                  >
                    {albumsLoading ? (
                      <div
                        style={{
                          display: "flex",
                          alignItems: "center",
                          justifyContent: "center",
                          gap: 8,
                          padding: 20,
                          color: "#64748b",
                          fontSize: 13,
                        }}
                      >
                        <Loader size={14} style={{ animation: "spin 1s linear infinite" }} />
                        Loading albums…
                      </div>
                    ) : filteredAlbums.length === 0 ? (
                      <div
                        style={{
                          padding: 20,
                          textAlign: "center",
                          color: "#64748b",
                          fontSize: 13,
                        }}
                      >
                        {albums.length === 0 ? "No albums found in Immich" : "No albums match your search"}
                      </div>
                    ) : (
                      filteredAlbums.map((album) => {
                        const selected = selectedAlbumIds.has(album.id);
                        return (
                          <div
                            key={album.id}
                            onClick={() => toggleAlbum(album.id)}
                            style={{
                              display: "flex",
                              alignItems: "center",
                              gap: 10,
                              padding: "9px 14px",
                              cursor: "pointer",
                              background: selected ? "rgba(59,130,246,0.1)" : "transparent",
                              borderBottom: "1px solid #1e293b",
                              transition: "background 0.1s",
                            }}
                          >
                            <div
                              style={{
                                width: 16,
                                height: 16,
                                borderRadius: 4,
                                border: `2px solid ${selected ? "#3b82f6" : "#475569"}`,
                                background: selected ? "#3b82f6" : "transparent",
                                flexShrink: 0,
                                display: "flex",
                                alignItems: "center",
                                justifyContent: "center",
                              }}
                            >
                              {selected && (
                                <svg width="9" height="7" viewBox="0 0 9 7" fill="none">
                                  <path d="M1 3.5L3.5 6L8 1" stroke="white" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
                                </svg>
                              )}
                            </div>
                            <span style={{ fontSize: 13, color: "#e2e8f0", flex: 1, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                              {album.albumName}
                            </span>
                            <span style={{ fontSize: 11, color: "#64748b", flexShrink: 0 }}>
                              {album.assetCount.toLocaleString()} assets
                            </span>
                          </div>
                        );
                      })
                    )}
                  </div>
                </>
              )}
            </div>
          )}
        </div>

        {/* Footer */}
        <div
          style={{
            padding: "14px 20px",
            borderTop: "1px solid #1e293b",
            display: "flex",
            justifyContent: "flex-end",
            gap: 10,
            flexShrink: 0,
          }}
        >
          <button
            onClick={onClose}
            style={{
              padding: "8px 18px",
              borderRadius: 8,
              border: "1px solid #334155",
              background: "transparent",
              color: "#94a3b8",
              fontSize: 13,
              fontWeight: 500,
              cursor: "pointer",
            }}
          >
            Cancel
          </button>
          <button
            onClick={handleConfirm}
            disabled={isConfirmDisabled}
            style={{
              padding: "8px 18px",
              borderRadius: 8,
              border: "none",
              background: isConfirmDisabled ? "#1e293b" : "#1e40af",
              color: isConfirmDisabled ? "#475569" : "white",
              fontSize: 13,
              fontWeight: 600,
              cursor: isConfirmDisabled ? "not-allowed" : "pointer",
              display: "flex",
              alignItems: "center",
              gap: 6,
            }}
          >
            {isLoading ? (
              <Loader size={13} style={{ animation: "spin 1s linear infinite" }} />
            ) : (
              <RefreshCw size={13} />
            )}
            {isLoading ? "Starting…" : "Start Sync"}
          </button>
        </div>
      </div>
    </div>
  );
}
