import React from "react";
import styles from "./TagList.module.css";

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
    <div className={styles.root}>
      {visible.map((tag, i) => (
        <span key={i} className={styles.tag}>
          #{tag}
          {editable && (
            <button className={styles.removeBtn} onClick={() => removeTag(i)}>×</button>
          )}
        </span>
      ))}
      {hidden > 0 && !editable && (
        <span className={styles.overflow}>+{hidden} more</span>
      )}
      {editable && (
        <input
          value={inputVal}
          onChange={(e) => setInputVal(e.target.value)}
          onKeyDown={addTag}
          placeholder="Add tag…"
          className={styles.addInput}
        />
      )}
    </div>
  );
}
