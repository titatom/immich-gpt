import React from "react";
import styles from "./ConfidenceBadge.module.css";

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
    <span
      className={styles.badge}
      style={{ color, background: `${color}18` }}
    >
      {pct}%
    </span>
  );
}
