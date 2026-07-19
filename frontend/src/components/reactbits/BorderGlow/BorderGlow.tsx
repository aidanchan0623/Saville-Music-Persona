import { useCallback, useEffect, useRef, type CSSProperties, type ReactNode } from "react";
import "./BorderGlow.css";

interface BorderGlowProps {
  children?: ReactNode;
  className?: string;
  glowMode?: "full" | "directional";
  edgeSensitivity?: number;
  glowColor?: string;
  backgroundColor?: string;
  borderRadius?: number;
  glowRadius?: number;
  glowIntensity?: number;
  coneSpread?: number;
  animated?: boolean;
  colors?: string[];
  fillOpacity?: number;
}

function parseHSL(hslStr: string): { h: number; s: number; l: number } {
  const match = hslStr.match(/([\d.]+)\s*([\d.]+)%?\s*([\d.]+)%?/);
  if (!match) return { h: 0, s: 86, l: 58 };
  return { h: parseFloat(match[1]), s: parseFloat(match[2]), l: parseFloat(match[3]) };
}

function buildGlowVars(glowColor: string, intensity: number): Record<string, string> {
  const { h, s, l } = parseHSL(glowColor);
  const base = `${h}deg ${s}% ${l}%`;
  const opacities = [100, 60, 50, 40, 30, 20, 10];
  const keys = ["", "-60", "-50", "-40", "-30", "-20", "-10"];
  const vars: Record<string, string> = {};

  for (let i = 0; i < opacities.length; i += 1) {
    vars[`--glow-color${keys[i]}`] = `hsl(${base} / ${Math.min(opacities[i] * intensity, 100)}%)`;
  }

  return vars;
}

const GRADIENT_POSITIONS = ["80% 55%", "69% 34%", "8% 6%", "41% 38%", "86% 85%", "82% 18%", "51% 4%"];
const GRADIENT_KEYS = ["--gradient-one", "--gradient-two", "--gradient-three", "--gradient-four", "--gradient-five", "--gradient-six", "--gradient-seven"];
const COLOR_MAP = [0, 1, 2, 0, 1, 2, 1];

function buildGradientVars(colors: string[]): Record<string, string> {
  const palette = colors.length ? colors : ["#ef2b2d", "#7b1118", "#202024"];
  const vars: Record<string, string> = {};

  for (let i = 0; i < 7; i += 1) {
    const color = palette[Math.min(COLOR_MAP[i], palette.length - 1)];
    vars[GRADIENT_KEYS[i]] = `radial-gradient(at ${GRADIENT_POSITIONS[i]}, ${color} 0px, transparent 50%)`;
  }

  vars["--gradient-base"] = `linear-gradient(${palette[0]} 0 100%)`;
  return vars;
}

function easeOutCubic(value: number) {
  return 1 - Math.pow(1 - value, 3);
}

function easeInCubic(value: number) {
  return value * value * value;
}

interface AnimateOpts {
  start?: number;
  end?: number;
  duration?: number;
  delay?: number;
  ease?: (value: number) => number;
  onUpdate: (value: number) => void;
  onEnd?: () => void;
}

function animateValue({ start = 0, end = 100, duration = 1000, delay = 0, ease = easeOutCubic, onUpdate, onEnd }: AnimateOpts) {
  let frameId: number | null = null;
  let timeoutId: number | null = null;
  let cancelled = false;
  const startTime = performance.now() + delay;

  function tick() {
    if (cancelled) return;
    const elapsed = performance.now() - startTime;
    const progress = Math.min(elapsed / duration, 1);
    onUpdate(start + (end - start) * ease(progress));
    if (progress < 1) {
      frameId = requestAnimationFrame(tick);
    } else {
      onEnd?.();
    }
  }

  timeoutId = window.setTimeout(() => {
    frameId = requestAnimationFrame(tick);
  }, delay);

  return () => {
    cancelled = true;
    if (timeoutId !== null) window.clearTimeout(timeoutId);
    if (frameId !== null) cancelAnimationFrame(frameId);
  };
}

function prefersReducedMotion() {
  return typeof window !== "undefined" && typeof window.matchMedia === "function" && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
}

export default function BorderGlow({
  children,
  className = "",
  glowMode = "full",
  edgeSensitivity = 45,
  glowColor = "0 86 58",
  backgroundColor = "#111114",
  borderRadius = 14,
  glowRadius = 12,
  glowIntensity = 0.38,
  coneSpread = 16,
  animated = false,
  colors = ["#ef2b2d", "#6f0b11", "#202024"],
  fillOpacity = 0.08,
}: BorderGlowProps) {
  const cardRef = useRef<HTMLDivElement>(null);
  const canTrackPointerRef = useRef(false);

  const getCenterOfElement = useCallback((el: HTMLElement) => {
    const { width, height } = el.getBoundingClientRect();
    return [width / 2, height / 2];
  }, []);

  const getEdgeProximity = useCallback(
    (el: HTMLElement, x: number, y: number) => {
      const [centerX, centerY] = getCenterOfElement(el);
      const deltaX = x - centerX;
      const deltaY = y - centerY;
      let scaleX = Infinity;
      let scaleY = Infinity;

      if (deltaX !== 0) scaleX = centerX / Math.abs(deltaX);
      if (deltaY !== 0) scaleY = centerY / Math.abs(deltaY);

      return Math.min(Math.max(1 / Math.min(scaleX, scaleY), 0), 1);
    },
    [getCenterOfElement],
  );

  const getCursorAngle = useCallback(
    (el: HTMLElement, x: number, y: number) => {
      const [centerX, centerY] = getCenterOfElement(el);
      const deltaX = x - centerX;
      const deltaY = y - centerY;
      if (deltaX === 0 && deltaY === 0) return 0;

      const radians = Math.atan2(deltaY, deltaX);
      const degrees = radians * (180 / Math.PI) + 90;
      return degrees < 0 ? degrees + 360 : degrees;
    },
    [getCenterOfElement],
  );

  const handlePointerMove = useCallback(
    (event: React.PointerEvent<HTMLDivElement>) => {
      const card = cardRef.current;
      if (glowMode !== "directional" || !card || !canTrackPointerRef.current) return;

      const rect = card.getBoundingClientRect();
      const x = event.clientX - rect.left;
      const y = event.clientY - rect.top;

      card.style.setProperty("--edge-proximity", `${(getEdgeProximity(card, x, y) * 100).toFixed(3)}`);
      card.style.setProperty("--cursor-angle", `${getCursorAngle(card, x, y).toFixed(3)}deg`);
    },
    [getCursorAngle, getEdgeProximity, glowMode],
  );

  const handlePointerLeave = useCallback(() => {
    const card = cardRef.current;
    if (glowMode !== "directional" || !card) return;
    card.style.setProperty("--edge-proximity", "0");
  }, [glowMode]);

  useEffect(() => {
    if (glowMode !== "directional") {
      canTrackPointerRef.current = false;
      return;
    }
    if (typeof window.matchMedia !== "function") return;
    const media = window.matchMedia("(hover: hover) and (pointer: fine)");
    const update = () => {
      canTrackPointerRef.current = media.matches && !prefersReducedMotion();
    };
    update();
    media.addEventListener("change", update);
    return () => media.removeEventListener("change", update);
  }, [glowMode]);

  useEffect(() => {
    if (glowMode !== "directional" || !animated || prefersReducedMotion() || !cardRef.current) return;
    const card = cardRef.current;
    const angleStart = 110;
    const angleEnd = 465;
    const cancellations: Array<() => void> = [];

    card.classList.add("sweep-active");
    card.style.setProperty("--cursor-angle", `${angleStart}deg`);
    cancellations.push(animateValue({ duration: 500, onUpdate: (value) => card.style.setProperty("--edge-proximity", `${value}`) }));
    cancellations.push(
      animateValue({
        ease: easeInCubic,
        duration: 1500,
        end: 50,
        onUpdate: (value) => {
          card.style.setProperty("--cursor-angle", `${(angleEnd - angleStart) * (value / 100) + angleStart}deg`);
        },
      }),
    );
    cancellations.push(
      animateValue({
        ease: easeOutCubic,
        delay: 1500,
        duration: 2250,
        start: 50,
        end: 100,
        onUpdate: (value) => {
          card.style.setProperty("--cursor-angle", `${(angleEnd - angleStart) * (value / 100) + angleStart}deg`);
        },
      }),
    );
    cancellations.push(
      animateValue({
        ease: easeInCubic,
        delay: 2500,
        duration: 1500,
        start: 100,
        end: 0,
        onUpdate: (value) => card.style.setProperty("--edge-proximity", `${value}`),
        onEnd: () => card.classList.remove("sweep-active"),
      }),
    );

    return () => {
      cancellations.forEach((cancel) => cancel());
      card.classList.remove("sweep-active");
    };
  }, [animated, glowMode]);

  const glowVars = buildGlowVars(glowColor, glowIntensity);

  return (
    <div
      ref={cardRef}
      onPointerMove={handlePointerMove}
      onPointerLeave={handlePointerLeave}
      className={`border-glow-card${className ? ` ${className}` : ""}`}
      data-glow-mode={glowMode}
      style={
        {
          "--card-bg": backgroundColor,
          "--edge-sensitivity": edgeSensitivity,
          "--border-radius": `${borderRadius}px`,
          "--glow-padding": `${glowRadius}px`,
          "--cone-spread": coneSpread,
          "--fill-opacity": fillOpacity,
          ...glowVars,
          ...buildGradientVars(colors),
        } as CSSProperties
      }
    >
      <span className="edge-light" />
      <div className="border-glow-inner">{children}</div>
    </div>
  );
}
