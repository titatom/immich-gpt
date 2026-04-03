import React, { useState } from "react";
import { Image } from "lucide-react";
import { getThumbnailUrl } from "../services/api";

interface Props {
  assetId: string;
  size?: number;
  onClick?: () => void;
  className?: string;
}

export default function Thumbnail({ assetId, size = 80, onClick }: Props) {
  const [error, setError] = useState(false);
  const [loaded, setLoaded] = useState(false);

  if (error) {
    return (
      <div style={{
        width: size,
        height: size,
        background: "#1e293b",
        borderRadius: 8,
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        flexShrink: 0,
        border: "1px solid #334155",
      }}>
        <Image size={size / 3} color="#475569" />
      </div>
    );
  }

  return (
    <div
      style={{
        width: size,
        height: size,
        borderRadius: 8,
        overflow: "hidden",
        flexShrink: 0,
        background: "#1e293b",
        cursor: onClick ? "pointer" : "default",
        border: "1px solid #334155",
        position: "relative",
      }}
      onClick={onClick}
    >
      {!loaded && (
        <div style={{
          position: "absolute",
          inset: 0,
          background: "#1e293b",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
        }}>
          <Image size={size / 3} color="#334155" />
        </div>
      )}
      <img
        src={getThumbnailUrl(assetId)}
        alt=""
        onLoad={() => setLoaded(true)}
        onError={() => setError(true)}
        style={{
          width: "100%",
          height: "100%",
          objectFit: "cover",
          display: loaded ? "block" : "none",
        }}
      />
    </div>
  );
}
