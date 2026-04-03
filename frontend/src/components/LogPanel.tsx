import React, { useRef, useEffect } from "react";

interface Props {
  lines?: string[];
  maxHeight?: number;
}

export default function LogPanel({ lines = [], maxHeight = 200 }: Props) {
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (ref.current) {
      ref.current.scrollTop = ref.current.scrollHeight;
    }
  }, [lines]);

  return (
    <div
      ref={ref}
      style={{
        background: "#0f172a",
        border: "1px solid #1e293b",
        borderRadius: 8,
        padding: "12px 16px",
        maxHeight,
        overflowY: "auto",
        fontFamily: "monospace",
        fontSize: 12,
        lineHeight: 1.6,
        color: "#64748b",
      }}
    >
      {lines.length === 0 ? (
        <span style={{ color: "#334155" }}>No logs yet.</span>
      ) : (
        lines.map((line, i) => (
          <div
            key={i}
            style={{
              color: line.includes("✗") || line.includes("error") || line.includes("Error")
                ? "#f87171"
                : line.includes("✓") || line.includes("completed") || line.includes("Completed")
                ? "#86efac"
                : "#64748b",
            }}
          >
            {line}
          </div>
        ))
      )}
    </div>
  );
}
