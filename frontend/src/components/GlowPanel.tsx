import type { ComponentProps, ElementType, ReactNode } from "react";
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
  "data-testid"?: string;
}

const VARIANT_CONFIG = {
  major: {
    edgeSensitivity: 35,
    glowColor: "0 90 62",
    backgroundColor: "#0d0d0f",
    borderRadius: 18,
    glowRadius: 22,
    glowIntensity: 0.55,
    coneSpread: 20,
    colors: ["#ff4a4d", "#8f1118", "#2b0709"],
    fillOpacity: 0.12,
  },
  card: {
    edgeSensitivity: 45,
    glowColor: "0 86 58",
    backgroundColor: "#111114",
    borderRadius: 14,
    glowRadius: 12,
    glowIntensity: 0.38,
    coneSpread: 16,
    colors: ["#ef2b2d", "#6f0b11", "#202024"],
    fillOpacity: 0.08,
  },
  row: {
    edgeSensitivity: 55,
    glowColor: "0 82 56",
    backgroundColor: "#0b0b0d",
    borderRadius: 10,
    glowRadius: 6,
    glowIntensity: 0.22,
    coneSpread: 12,
    colors: ["#ef2b2d", "#5a090e", "#18181b"],
    fillOpacity: 0.04,
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
    <BorderGlow {...VARIANT_CONFIG[variant]} animated={false} className={panelClasses}>
      <Tag className={`smp-glow-panel__content${className ? ` ${className}` : ""}`} data-testid={testId}>
        {children}
      </Tag>
    </BorderGlow>
  );
}
