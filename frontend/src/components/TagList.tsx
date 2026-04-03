import React from "react";

interface Props {
  tags?: string[];
  editable?: boolean;
  onChange?: (tags: string[]) => void;
  maxVisible?: number;
}

export default function TagList({ tags = [], editable = false, onChange, maxVisible }: Props) {
  const [inputVal, setInputVal] = React.useState("");
  const visible = maxVisible ? tags.slice(0, maxVisible) : tags;
  const hidden = maxVisible ? tags.length - maxVisible : 0;

  const removeTag = (idx: number) => {
    if (onChange) onChange(tags.filter((_, i) => i !== idx));
  };

  const addTag = (e: React.KeyboardEvent) => {
    if ((e.key === "Enter" || e.key === ",") && inputVal.trim()) {
      e.preventDefault();
      const newTag = inputVal.trim().replace(/,$/, "");
      if (!tags.includes(newTag) && onChange) {
        onChange([...tags, newTag]);
      }
      setInputVal("");
    }
  };

  return (
    <div style={{ display: "flex", flexWrap: "wrap", gap: 6, alignItems: "center" }}>
      {visible.map((tag, i) => (
        <span
          key={i}
          style={{
            background: "#0ea5e918",
            color: "#38bdf8",
            border: "1px solid #0ea5e930",
            borderRadius: 6,
            padding: "2px 8px",
            fontSize: 12,
            display: "flex",
            alignItems: "center",
            gap: 4,
          }}
        >
          #{tag}
          {editable && (
            <button
              onClick={() => removeTag(i)}
              style={{
                background: "none",
                border: "none",
                cursor: "pointer",
                color: "#64748b",
                padding: 0,
                lineHeight: 1,
                fontSize: 14,
              }}
            >
              ×
            </button>
          )}
        </span>
      ))}
      {hidden > 0 && !editable && (
        <span style={{ fontSize: 12, color: "#64748b" }}>+{hidden} more</span>
      )}
      {editable && (
        <input
          value={inputVal}
          onChange={(e) => setInputVal(e.target.value)}
          onKeyDown={addTag}
          placeholder="Add tag..."
          style={{
            background: "transparent",
            border: "1px solid #334155",
            borderRadius: 6,
            padding: "2px 8px",
            fontSize: 12,
            color: "#94a3b8",
            outline: "none",
            width: 100,
          }}
        />
      )}
    </div>
  );
}
