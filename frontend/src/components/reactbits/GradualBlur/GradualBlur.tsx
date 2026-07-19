import React, { useEffect, useMemo, useRef, useState } from "react";
import "./GradualBlur.css";

type BlurPosition = "top" | "bottom" | "left" | "right";
type BlurCurve = "linear" | "bezier" | "ease-in" | "ease-out" | "ease-in-out";
type BlurTarget = "parent" | "page";
type BlurPreset =
  | BlurPosition
  | "subtle"
  | "intense"
  | "smooth"
  | "sharp"
  | "header"
  | "footer"
  | "sidebar"
  | "page-header"
  | "page-footer";

interface GradualBlurProps {
  position?: BlurPosition;
  strength?: number;
  height?: string;
  width?: string;
  divCount?: number;
  exponential?: boolean;
  zIndex?: number;
  animated?: boolean | "scroll";
  duration?: string;
  easing?: string;
  opacity?: number;
  curve?: BlurCurve;
  responsive?: boolean;
  target?: BlurTarget;
  preset?: BlurPreset;
  hoverIntensity?: number;
  onAnimationComplete?: () => void;
  className?: string;
  style?: React.CSSProperties;
  mobileHeight?: string;
  tabletHeight?: string;
  desktopHeight?: string;
  mobileWidth?: string;
  tabletWidth?: string;
  desktopWidth?: string;
}

type GradualBlurConfig = Required<Omit<GradualBlurProps, "preset" | "hoverIntensity" | "onAnimationComplete" | "width" | "mobileHeight" | "tabletHeight" | "desktopHeight" | "mobileWidth" | "tabletWidth" | "desktopWidth">> &
  Pick<GradualBlurProps, "width" | "hoverIntensity" | "onAnimationComplete" | "mobileHeight" | "tabletHeight" | "desktopHeight" | "mobileWidth" | "tabletWidth" | "desktopWidth">;

const DEFAULT_CONFIG: GradualBlurConfig = {
  position: "bottom",
  strength: 2,
  height: "6rem",
  width: undefined,
  divCount: 5,
  exponential: false,
  zIndex: 1000,
  animated: false,
  duration: "0.3s",
  easing: "ease-out",
  opacity: 1,
  curve: "linear",
  responsive: false,
  target: "parent",
  className: "",
  style: {},
  hoverIntensity: undefined,
  onAnimationComplete: undefined,
  mobileHeight: undefined,
  tabletHeight: undefined,
  desktopHeight: undefined,
  mobileWidth: undefined,
  tabletWidth: undefined,
  desktopWidth: undefined,
};

const PRESETS: Record<BlurPreset, Partial<GradualBlurConfig>> = {
  top: { position: "top", height: "6rem" },
  bottom: { position: "bottom", height: "6rem" },
  left: { position: "left", height: "6rem" },
  right: { position: "right", height: "6rem" },
  subtle: { height: "4rem", strength: 1, opacity: 0.8, divCount: 3 },
  intense: { height: "10rem", strength: 4, divCount: 8, exponential: true },
  smooth: { height: "8rem", curve: "bezier", divCount: 10 },
  sharp: { height: "5rem", curve: "linear", divCount: 4 },
  header: { position: "top", height: "8rem", curve: "ease-out" },
  footer: { position: "bottom", height: "8rem", curve: "ease-out" },
  sidebar: { position: "left", height: "6rem", strength: 2.5 },
  "page-header": { position: "top", height: "10rem", target: "page", strength: 3 },
  "page-footer": { position: "bottom", height: "10rem", target: "page", strength: 3 },
};

const CURVE_FUNCTIONS: Record<BlurCurve, (progress: number) => number> = {
  linear: (progress) => progress,
  bezier: (progress) => progress * progress * (3 - 2 * progress),
  "ease-in": (progress) => progress * progress,
  "ease-out": (progress) => 1 - (1 - progress) ** 2,
  "ease-in-out": (progress) => (progress < 0.5 ? 2 * progress * progress : 1 - (-2 * progress + 2) ** 2 / 2),
};

function mergeConfigs(...configs: Partial<GradualBlurConfig>[]): GradualBlurConfig {
  return configs.reduce<GradualBlurConfig>((acc, config) => ({ ...acc, ...config }), { ...DEFAULT_CONFIG });
}

const getGradientDirection = (position: BlurPosition) =>
  ({
    top: "to top",
    bottom: "to bottom",
    left: "to left",
    right: "to right",
  })[position] || "to bottom";

function debounce(fn: () => void, wait: number) {
  let timeoutId: number | undefined;
  return () => {
    window.clearTimeout(timeoutId);
    timeoutId = window.setTimeout(fn, wait);
  };
}

function useResponsiveDimension(responsive: boolean, config: GradualBlurConfig, key: "height" | "width") {
  const [value, setValue] = useState(config[key]);

  useEffect(() => {
    if (!responsive || typeof window === "undefined") return;
    const calc = () => {
      const width = window.innerWidth;
      let nextValue = config[key];
      const suffix = key[0].toUpperCase() + key.slice(1);
      if (width <= 480 && config[`mobile${suffix}` as keyof GradualBlurConfig]) {
        nextValue = config[`mobile${suffix}` as keyof GradualBlurConfig] as string | undefined;
      } else if (width <= 768 && config[`tablet${suffix}` as keyof GradualBlurConfig]) {
        nextValue = config[`tablet${suffix}` as keyof GradualBlurConfig] as string | undefined;
      } else if (width <= 1024 && config[`desktop${suffix}` as keyof GradualBlurConfig]) {
        nextValue = config[`desktop${suffix}` as keyof GradualBlurConfig] as string | undefined;
      }
      setValue(nextValue);
    };
    const debounced = debounce(calc, 100);
    calc();
    window.addEventListener("resize", debounced);
    return () => window.removeEventListener("resize", debounced);
  }, [responsive, config, key]);

  return responsive ? value : config[key];
}

function useIntersectionObserver(ref: React.RefObject<HTMLDivElement | null>, shouldObserve = false) {
  const [isVisible, setIsVisible] = useState(!shouldObserve);

  useEffect(() => {
    if (!shouldObserve || !ref.current) return;
    const observer = new IntersectionObserver(([entry]) => setIsVisible(entry.isIntersecting), { threshold: 0.1 });
    observer.observe(ref.current);
    return () => observer.disconnect();
  }, [ref, shouldObserve]);

  return isVisible;
}

function GradualBlur(props: GradualBlurProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [isHovered, setIsHovered] = useState(false);

  const config = useMemo<GradualBlurConfig>(() => {
    const presetConfig = props.preset && PRESETS[props.preset] ? PRESETS[props.preset] : {};
    return mergeConfigs(presetConfig, props as Partial<GradualBlurConfig>);
  }, [props]);

  const responsiveHeight = useResponsiveDimension(config.responsive, config, "height");
  const responsiveWidth = useResponsiveDimension(config.responsive, config, "width");
  const isVisible = useIntersectionObserver(containerRef, config.animated === "scroll");

  const blurDivs = useMemo(() => {
    const divs = [];
    const increment = 100 / config.divCount;
    const currentStrength = isHovered && config.hoverIntensity ? config.strength * config.hoverIntensity : config.strength;
    const curveFunc = CURVE_FUNCTIONS[config.curve] || CURVE_FUNCTIONS.linear;

    for (let i = 1; i <= config.divCount; i += 1) {
      let progress = i / config.divCount;
      progress = curveFunc(progress);
      const blurValue = config.exponential ? 2 ** (progress * 4) * 0.0625 * currentStrength : 0.0625 * (progress * config.divCount + 1) * currentStrength;
      const p1 = Math.round((increment * i - increment) * 10) / 10;
      const p2 = Math.round(increment * i * 10) / 10;
      const p3 = Math.round((increment * i + increment) * 10) / 10;
      const p4 = Math.round((increment * i + increment * 2) * 10) / 10;
      let gradient = `transparent ${p1}%, black ${p2}%`;
      if (p3 <= 100) gradient += `, black ${p3}%`;
      if (p4 <= 100) gradient += `, transparent ${p4}%`;
      const direction = getGradientDirection(config.position);

      divs.push(
        <div
          key={i}
          style={{
            position: "absolute",
            inset: "0",
            maskImage: `linear-gradient(${direction}, ${gradient})`,
            WebkitMaskImage: `linear-gradient(${direction}, ${gradient})`,
            backdropFilter: `blur(${blurValue.toFixed(3)}rem)`,
            WebkitBackdropFilter: `blur(${blurValue.toFixed(3)}rem)`,
            opacity: config.opacity,
            transition: config.animated && config.animated !== "scroll" ? `backdrop-filter ${config.duration} ${config.easing}` : undefined,
          }}
        />,
      );
    }

    return divs;
  }, [config, isHovered]);

  const containerStyle = useMemo(() => {
    const isVertical = ["top", "bottom"].includes(config.position);
    const isHorizontal = ["left", "right"].includes(config.position);
    const isPageTarget = config.target === "page";
    const baseStyle: React.CSSProperties = {
      position: isPageTarget ? "fixed" : "absolute",
      pointerEvents: config.hoverIntensity ? "auto" : "none",
      opacity: isVisible ? 1 : 0,
      transition: config.animated ? `opacity ${config.duration} ${config.easing}` : undefined,
      zIndex: isPageTarget ? config.zIndex + 100 : config.zIndex,
      ...config.style,
    };

    if (isVertical) {
      baseStyle.height = responsiveHeight;
      baseStyle.width = responsiveWidth || "100%";
      baseStyle[config.position] = 0;
      baseStyle.left = 0;
      baseStyle.right = 0;
    } else if (isHorizontal) {
      baseStyle.width = responsiveWidth || responsiveHeight;
      baseStyle.height = "100%";
      baseStyle[config.position] = 0;
      baseStyle.top = 0;
      baseStyle.bottom = 0;
    }

    return baseStyle;
  }, [config, responsiveHeight, responsiveWidth, isVisible]);

  useEffect(() => {
    if (isVisible && config.animated === "scroll" && config.onAnimationComplete) {
      const milliseconds = parseFloat(config.duration) * 1000;
      const timeoutId = window.setTimeout(() => config.onAnimationComplete?.(), milliseconds);
      return () => window.clearTimeout(timeoutId);
    }
  }, [isVisible, config]);

  return (
    <div
      ref={containerRef}
      className={`gradual-blur ${config.target === "page" ? "gradual-blur-page" : "gradual-blur-parent"} ${config.className}`}
      style={containerStyle}
      onMouseEnter={config.hoverIntensity ? () => setIsHovered(true) : undefined}
      onMouseLeave={config.hoverIntensity ? () => setIsHovered(false) : undefined}
    >
      <div className="gradual-blur-inner">{blurDivs}</div>
    </div>
  );
}

export default React.memo(GradualBlur);
