import React, { useRef, useEffect } from "react";
import styles from "./LogPanel.module.css";

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

  function lineClass(line: string) {
    if (line.includes("✗") || line.includes("error") || line.includes("Error")) return styles.lineError;
    if (line.includes("✓") || line.includes("completed") || line.includes("Completed")) return styles.lineSuccess;
    return styles.lineDefault;
  }

  return (
    <div ref={ref} className={styles.root} style={{ maxHeight }}>
      {lines.length === 0 ? (
        <span className={styles.empty}>No logs yet.</span>
      ) : (
        lines.map((line, i) => (
          <div key={i} className={lineClass(line)}>{line}</div>
        ))
      )}
    </div>
  );
}
