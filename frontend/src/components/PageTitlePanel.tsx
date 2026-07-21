import type { CSSProperties, ReactNode } from "react";
import { useEffect, useState } from "react";
import { AnimatedPageTitle } from "./AnimatedPageTitle";
import { GlowPanel } from "./GlowPanel";
import LineWaves from "./reactbits/LineWaves/LineWaves";
import "./PageTitlePanel.css";

interface PageTitlePanelProps {
  eyebrow?: string;
  title: string;
  subtitle?: ReactNode;
  titleAnimationKey: string;
  titleClassName?: string;
  subtitleClassName?: string;
  lineMode?: "static" | "animated";
  actions?: ReactNode;
  metadata?: ReactNode;
  className?: string;
  contentClassName?: string;
  backgroundImage?: string;
  backgroundPosition?: string;
  overlayStrength?: number;
}

export function PageTitlePanel({
  eyebrow,
  title,
  subtitle,
  titleAnimationKey,
  titleClassName = "text-3xl font-black leading-tight text-white md:text-5xl",
  subtitleClassName = "mt-4 max-w-3xl text-base leading-7 text-mist",
  lineMode = "static",
  actions,
  metadata,
  className = "",
  contentClassName = "",
  backgroundImage,
  backgroundPosition = "center",
  overlayStrength = 0.72,
}: PageTitlePanelProps) {
  const compactLines = useCompactTitleMotion();
  const panelStyle = {
    "--smp-page-title-image": backgroundImage ? `url("${backgroundImage}")` : "none",
    "--smp-page-title-position": backgroundPosition,
    "--smp-page-title-overlay": overlayStrength,
  } as CSSProperties;

  return (
    <GlowPanel
      as="header"
      variant="major"
      wrapperClassName={`smp-page-title-panel smp-page-title-panel--${lineMode}${backgroundImage ? " smp-page-title-panel--with-image" : ""}${className ? ` ${className}` : ""}`}
      className="smp-page-title-panel__inner"
      style={panelStyle}
    >
      {backgroundImage ? <div className="smp-page-title-panel__photo" aria-hidden="true" /> : null}
      <div className="smp-page-title-panel__lines" aria-hidden="true">
        {lineMode === "animated" ? (
          <LineWaves
            speed={0.16}
            innerLineCount={compactLines ? 16 : 28}
            outerLineCount={compactLines ? 20 : 34}
            warpIntensity={0.65}
            rotation={-35}
            edgeFadeWidth={0.12}
            colorCycleSpeed={0.3}
            brightness={compactLines ? 0.08 : 0.12}
            color1="#ef2b2d"
            color2="#7b1118"
            color3="#d4d4d8"
            enableMouseInteraction={!compactLines}
            mouseInfluence={0.4}
          />
        ) : null}
      </div>
      <div className="smp-page-title-panel__overlay" aria-hidden="true" />
      <div className={`smp-page-title-panel__content${contentClassName ? ` ${contentClassName}` : ""}`}>
        <div className="smp-page-title-panel__row">
          <div className="min-w-0">
            {eyebrow ? <p className="text-xs font-semibold uppercase tracking-[0.2em] text-red-200 md:text-sm">{eyebrow}</p> : null}
            <AnimatedPageTitle animationKey={titleAnimationKey} text={title} className={`mt-3 ${titleClassName}`} />
            {subtitle ? <div className={subtitleClassName}>{subtitle}</div> : null}
          </div>
          {actions ? <div className="smp-page-title-panel__actions">{actions}</div> : null}
        </div>
        {metadata ? <div className="smp-page-title-panel__metadata">{metadata}</div> : null}
      </div>
    </GlowPanel>
  );
}

function useCompactTitleMotion() {
  const [compact, setCompact] = useState(() => {
    if (typeof window === "undefined" || typeof window.matchMedia !== "function") return false;
    return window.matchMedia("(max-width: 767px)").matches;
  });

  useEffect(() => {
    if (typeof window.matchMedia !== "function") return;
    const media = window.matchMedia("(max-width: 767px)");
    const update = () => setCompact(media.matches);
    update();
    media.addEventListener("change", update);
    return () => media.removeEventListener("change", update);
  }, []);

  return compact;
}
