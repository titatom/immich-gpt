import React from "react";
import styles from "./BrandLogo.module.css";

type BrandLogoProps = {
  variant?: "stacked" | "inline";
  size?: "sidebar" | "auth" | number;
  subtitle?: string;
  showSubtitle?: boolean;
  alt?: string;
  className?: string;
  style?: React.CSSProperties;
};

const DEFAULT_SUBTITLE = "Review-first AI library organization";

function resolveSize(size: BrandLogoProps["size"]): string {
  if (typeof size === "number") {
    return `${size}px`;
  }
  if (size === "sidebar") {
    return "150px";
  }
  if (size === "auth") {
    return "220px";
  }
  return "200px";
}

export default function BrandLogo({
  variant = "stacked",
  size = "auth",
  subtitle = DEFAULT_SUBTITLE,
  showSubtitle = true,
  alt = "Immich GPT logo",
  className = "",
  style,
}: BrandLogoProps) {
  return (
    <div
      className={[
        styles.root,
        variant === "inline" ? styles.inline : styles.stacked,
        className,
      ].join(" ").trim()}
      style={{ "--brand-logo-size": resolveSize(size), ...style } as React.CSSProperties}
    >
      <img src="/logo.png" alt={alt} className={styles.mark} />
      {showSubtitle && subtitle && <div className={styles.subtitle}>{subtitle}</div>}
    </div>
  );
}
