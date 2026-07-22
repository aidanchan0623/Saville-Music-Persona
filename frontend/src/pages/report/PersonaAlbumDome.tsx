import { useEffect, useMemo, useRef, useState } from "react";
import type { CSSProperties } from "react";
import { motion, useInView, useReducedMotion } from "motion/react";
import type { MotionStyle } from "motion/react";
import type { PersonaAlbumDomeItem } from "./personaStoryModel";
import "./PersonaAlbumDome.css";

type PersonaAlbumDomeProps = {
  items: PersonaAlbumDomeItem[];
  priority?: boolean;
  className?: string;
  style?: MotionStyle;
};

type TileLayout = {
  left: number;
  top: number;
  size: number;
  mobileSize: number;
  opacity: number;
  depth: number;
  rotateA: number;
  rotateB: number;
  tiltX: number;
  tiltY: number;
  floatDistance: number;
  duration: number;
  delay: number;
};

const MAX_DOME_ALBUMS = 12;

export function PersonaAlbumDome({ items, priority = false, className = "", style }: PersonaAlbumDomeProps) {
  const rootRef = useRef<HTMLDivElement | null>(null);
  const isInView = useInView(rootRef, { margin: "720px 0px 720px 0px" });
  const reducedMotion = useReducedMotion();
  const [tabHidden, setTabHidden] = useState(() => (typeof document === "undefined" ? false : document.hidden));

  useEffect(() => {
    const updateVisibility = () => setTabHidden(document.hidden);
    document.addEventListener("visibilitychange", updateVisibility);
    return () => document.removeEventListener("visibilitychange", updateVisibility);
  }, []);

  const domeItems = useMemo(
    () =>
      items.slice(0, MAX_DOME_ALBUMS).map((item, index) => ({
        item,
        layout: makeTileLayout(index, Math.min(items.length, MAX_DOME_ALBUMS)),
      })),
    [items],
  );

  if (!domeItems.length) return null;

  const paused = Boolean(reducedMotion || tabHidden || !isInView);

  return (
    <motion.div
      ref={rootRef}
      className={`persona-album-dome${className ? ` ${className}` : ""}`}
      aria-hidden="true"
      data-paused={paused ? "true" : "false"}
      style={style}
    >
      <div className="persona-album-dome__glow" />
      <div className="persona-album-dome__ring">
        {domeItems.map(({ item, layout }, index) => (
          <div
            key={`${item.rank}-${item.title}-${item.artist}`}
            className="persona-album-dome__tile"
            style={tileStyle(layout)}
          >
            <img
              src={item.src}
              alt=""
              loading={priority && index < 4 ? "eager" : "lazy"}
              decoding="async"
              draggable={false}
            />
          </div>
        ))}
      </div>
    </motion.div>
  );
}

function tileStyle(layout: TileLayout) {
  return {
    "--tile-left": `${layout.left}%`,
    "--tile-top": `${layout.top}%`,
    "--tile-size": `${layout.size}px`,
    "--tile-mobile-size": `${layout.mobileSize}px`,
    "--tile-opacity": layout.opacity,
    "--tile-depth": layout.depth,
    "--tile-rotate-a": `${layout.rotateA}deg`,
    "--tile-rotate-b": `${layout.rotateB}deg`,
    "--tile-tilt-x": `${layout.tiltX}deg`,
    "--tile-tilt-y": `${layout.tiltY}deg`,
    "--tile-float": `${layout.floatDistance}px`,
    "--tile-duration": `${layout.duration}s`,
    "--tile-delay": `${layout.delay}s`,
  } as CSSProperties;
}

function makeTileLayout(index: number, total: number): TileLayout {
  const denominator = Math.max(total - 1, 1);
  const angle = -154 + (308 * index) / denominator;
  const radians = (angle * Math.PI) / 180;
  const innerPull = index % 3 === 0 ? 0.78 : index % 3 === 1 ? 0.9 : 1;
  const left = 53 + Math.cos(radians) * 43 * innerPull;
  const top = 48 + Math.sin(radians) * 34 + ((index % 4) - 1.5) * 3.6;
  const size = 136 + ((index * 31) % 74);
  const mobileSize = 82 + ((index * 17) % 45);
  const rotateA = -7 + ((index * 11) % 15);
  const direction = index % 2 === 0 ? 1 : -1;

  return {
    left: clamp(left, 7, 96),
    top: clamp(top, 7, 90),
    size,
    mobileSize,
    opacity: 0.48 + ((index * 13) % 38) / 100,
    depth: 0.7 + ((index * 7) % 28) / 100,
    rotateA,
    rotateB: rotateA + direction * (2.4 + (index % 4) * 0.45),
    tiltX: -3 + ((index * 5) % 7),
    tiltY: -3 + ((index * 3) % 7),
    floatDistance: 8 + ((index * 7) % 15),
    duration: 9 + ((index * 5) % 10),
    delay: -((index * 1.15) % 8),
  };
}

function clamp(value: number, min: number, max: number) {
  return Math.min(max, Math.max(min, value));
}
