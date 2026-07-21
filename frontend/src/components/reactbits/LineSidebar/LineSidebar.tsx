import { useCallback, useEffect, useRef, useState } from "react";
import type { CSSProperties, PointerEvent } from "react";
import "./LineSidebar.css";

type Falloff = "linear" | "smooth" | "sharp";

export interface LineSidebarProps {
  items?: string[];
  accentColor?: string;
  textColor?: string;
  markerColor?: string;
  showIndex?: boolean;
  showMarker?: boolean;
  proximityRadius?: number;
  maxShift?: number;
  falloff?: Falloff;
  markerLength?: number;
  markerGap?: number;
  tickScale?: number;
  scaleTick?: boolean;
  itemGap?: number;
  fontSize?: number;
  smoothing?: number;
  defaultActive?: number | null;
  activeIndex?: number | null;
  onItemClick?: (index: number, label: string) => void;
  ariaLabel?: string;
  className?: string;
}

const FALLOFF_CURVES: Record<Falloff, (p: number) => number> = {
  linear: (p) => p,
  smooth: (p) => p * p * (3 - 2 * p),
  sharp: (p) => p * p * p,
};

const DEFAULT_ITEMS = ["Overview", "Top 10", "Scores", "Patterns", "Persona Report", "Recommendations", "Settings"];

export default function LineSidebar({
  items = DEFAULT_ITEMS,
  accentColor = "#ef2b2d",
  textColor = "#a4a4ad",
  markerColor = "#3f3f46",
  showIndex = false,
  showMarker = true,
  proximityRadius = 85,
  maxShift = 10,
  falloff = "smooth",
  markerLength = 28,
  markerGap = 10,
  tickScale = 0.35,
  scaleTick = true,
  itemGap = 14,
  fontSize = 0.95,
  smoothing = 120,
  defaultActive = null,
  activeIndex,
  onItemClick,
  ariaLabel = "Primary navigation",
  className = "",
}: LineSidebarProps) {
  const isControlled = activeIndex !== undefined;
  const [internalActiveIndex, setInternalActiveIndex] = useState<number | null>(defaultActive);
  const currentActiveIndex = isControlled ? activeIndex : internalActiveIndex;
  const listRef = useRef<HTMLUListElement>(null);
  const itemRefs = useRef<(HTMLLIElement | null)[]>([]);
  const targetsRef = useRef<number[]>([]);
  const currentRef = useRef<number[]>([]);
  const rafRef = useRef<number | null>(null);
  const lastRef = useRef(0);
  const activeRef = useRef<number | null>(currentActiveIndex ?? null);
  const smoothingRef = useRef(smoothing);
  const reducedMotionRef = useRef(false);

  activeRef.current = currentActiveIndex ?? null;
  smoothingRef.current = smoothing;

  const runFrame = useCallback((now: number) => {
    const dt = Math.min((now - lastRef.current) / 1000, 0.05);
    lastRef.current = now;
    const tau = Math.max(smoothingRef.current, 1) / 1000;
    const k = reducedMotionRef.current ? 1 : 1 - Math.exp(-dt / tau);

    let moving = false;
    const elements = itemRefs.current;
    for (let i = 0; i < elements.length; i += 1) {
      const el = elements[i];
      if (!el) continue;
      const target = Math.max(targetsRef.current[i] || 0, activeRef.current === i ? 1 : 0);
      const cur = currentRef.current[i] || 0;
      const next = cur + (target - cur) * k;
      const settled = Math.abs(target - next) < 0.0015;
      const value = settled ? target : next;
      currentRef.current[i] = value;
      el.style.setProperty("--effect", value.toFixed(4));
      if (!settled) moving = true;
    }

    rafRef.current = moving ? requestAnimationFrame(runFrame) : null;
  }, []);

  const startLoop = useCallback(() => {
    if (rafRef.current !== null) return;
    lastRef.current = performance.now();
    rafRef.current = requestAnimationFrame(runFrame);
  }, [runFrame]);

  const handlePointerMove = useCallback(
    (event: PointerEvent<HTMLUListElement>) => {
      if (reducedMotionRef.current) return;
      const list = listRef.current;
      if (!list) return;
      const rect = list.getBoundingClientRect();
      const pointerY = event.clientY - rect.top;
      const ease = FALLOFF_CURVES[falloff] ?? FALLOFF_CURVES.linear;

      itemRefs.current.forEach((el, index) => {
        if (!el) return;
        const center = el.offsetTop + el.offsetHeight / 2;
        const distance = Math.abs(pointerY - center);
        targetsRef.current[index] = ease(Math.max(0, 1 - distance / proximityRadius));
      });
      startLoop();
    },
    [falloff, proximityRadius, startLoop],
  );

  const handlePointerLeave = useCallback(() => {
    targetsRef.current = targetsRef.current.map(() => 0);
    startLoop();
  }, [startLoop]);

  const handleActivate = useCallback(
    (index: number, label: string) => {
      if (!isControlled) setInternalActiveIndex(index);
      onItemClick?.(index, label);
    },
    [isControlled, onItemClick],
  );

  useEffect(() => {
    if (typeof window === "undefined" || typeof window.matchMedia !== "function") {
      reducedMotionRef.current = false;
      return;
    }
    const media = window.matchMedia("(prefers-reduced-motion: reduce)");
    const update = () => {
      reducedMotionRef.current = media.matches;
    };
    update();
    media.addEventListener("change", update);
    return () => media.removeEventListener("change", update);
  }, []);

  useEffect(() => {
    targetsRef.current = items.map(() => 0);
    currentRef.current = items.map((_, index) => (currentActiveIndex === index ? 1 : 0));
    itemRefs.current = itemRefs.current.slice(0, items.length);
    itemRefs.current.forEach((el, index) => {
      el?.style.setProperty("--effect", currentRef.current[index].toFixed(4));
    });
    startLoop();
  }, [items, currentActiveIndex, startLoop]);

  useEffect(
    () => () => {
      if (rafRef.current !== null) cancelAnimationFrame(rafRef.current);
    },
    [],
  );

  return (
    <nav
      className={`line-sidebar${showMarker ? " line-sidebar--markers" : ""}${scaleTick ? " line-sidebar--scale-tick" : ""}${className ? ` ${className}` : ""}`}
      aria-label={ariaLabel}
      style={
        {
          "--accent-color": accentColor,
          "--text-color": textColor,
          "--marker-color": markerColor,
          "--marker-length": `${markerLength}px`,
          "--marker-gap": `${markerGap}px`,
          "--tick-scale": tickScale,
          "--max-shift": `${maxShift}px`,
          "--item-gap": `${itemGap}px`,
          "--font-size": `${fontSize}rem`,
        } as CSSProperties
      }
    >
      <ul ref={listRef} className="line-sidebar__list" onPointerMove={handlePointerMove} onPointerLeave={handlePointerLeave}>
        {items.map((label, index) => (
          <li
            key={`${label}-${index}`}
            ref={(element) => {
              itemRefs.current[index] = element;
            }}
            className="line-sidebar__item"
          >
            {showMarker ? <span className="line-sidebar__marker" aria-hidden="true" /> : null}
            <button
              className="line-sidebar__button"
              type="button"
              aria-current={currentActiveIndex === index ? "page" : undefined}
              onClick={() => handleActivate(index, label)}
            >
              <span className="line-sidebar__label">
                {showIndex ? <span className="line-sidebar__index">{String(index + 1).padStart(2, "0")}</span> : null}
                <span className="line-sidebar__text">{label}</span>
              </span>
            </button>
          </li>
        ))}
      </ul>
    </nav>
  );
}
