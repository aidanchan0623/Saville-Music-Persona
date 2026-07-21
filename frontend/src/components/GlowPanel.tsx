import type { ComponentProps, CSSProperties, ElementType, ReactNode } from "react";
import BorderGlow from "./reactbits/BorderGlow/BorderGlow";
import "./GlowPanel.css";

type GlowPanelVariant = "major" | "card" | "row";
type GlowPanelElement = "section" | "article" | "div" | "header" | "p";

interface GlowPanelProps {
  children: ReactNode;
  as?: GlowPanelElement;
  variant?: GlowPanelVariant;
  className?: string;
  wrapperClassName?: string;
  lined?: boolean;
  selected?: boolean;
  style?: CSSProperties;
  "data-testid"?: string;
}

const VARIANT_CONFIG = {
  major: {
    glowMode: "full",
    edgeSensitivity: 35,
    glowColor: "0 90 62",
    backgroundColor: "#0d0d0f",
    borderRadius: 18,
    glowRadius: 14,
    glowIntensity: 0.28,
    coneSpread: 14,
    colors: ["#ff4a4d", "#8f1118", "#2b0709"],
    fillOpacity: 0.06,
  },
  card: {
    glowMode: "full",
    edgeSensitivity: 45,
    glowColor: "0 86 58",
    backgroundColor: "#111114",
    borderRadius: 14,
    glowRadius: 8,
    glowIntensity: 0.18,
    coneSpread: 12,
    colors: ["#ef2b2d", "#6f0b11", "#202024"],
    fillOpacity: 0.04,
  },
  row: {
    glowMode: "full",
    edgeSensitivity: 55,
    glowColor: "0 82 56",
    backgroundColor: "#0b0b0d",
    borderRadius: 10,
    glowRadius: 4,
    glowIntensity: 0.1,
    coneSpread: 8,
    colors: ["#ef2b2d", "#5a090e", "#18181b"],
    fillOpacity: 0.025,
  },
} satisfies Record<GlowPanelVariant, ComponentProps<typeof BorderGlow>>;

export function GlowPanel({
  children,
  as = "section",
  variant = "card",
  className = "",
  wrapperClassName = "",
  lined = false,
  selected = false,
  style,
  "data-testid": testId,
}: GlowPanelProps) {
  const Tag = as as ElementType;
  const panelClasses = [
    "smp-glow-panel",
    `smp-glow-panel--${variant}`,
    lined ? "smp-glow-panel--lined" : "",
    selected ? "smp-glow-panel--selected" : "",
    wrapperClassName,
  ].filter(Boolean).join(" ");

  return (
    <BorderGlow {...VARIANT_CONFIG[variant]} animated={false} className={panelClasses} style={style}>
      <Tag className={`smp-glow-panel__content${className ? ` ${className}` : ""}`} data-testid={testId}>
        {children}
      </Tag>
    </BorderGlow>
  );
}
