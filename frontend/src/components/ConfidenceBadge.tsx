import React from "react";

interface Props {
  confidence?: number;
}

export default function ConfidenceBadge({ confidence }: Props) {
  if (confidence === undefined || confidence === null) return null;
  const pct = Math.round(confidence * 100);
  const color =
    pct >= 80 ? "#22c55e" :
    pct >= 60 ? "#f59e0b" :
    "#ef4444";

  return (
    <span style={{
      display: "inline-flex",
      alignItems: "center",
      gap: 4,
      fontSize: 12,
      fontWeight: 700,
      color,
      background: `${color}18`,
      padding: "2px 8px",
      borderRadius: 6,
    }}>
      {pct}%
    </span>
  );
}
