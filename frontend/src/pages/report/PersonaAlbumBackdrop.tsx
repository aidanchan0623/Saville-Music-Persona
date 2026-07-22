import { useEffect, useMemo, useRef, useState } from "react";
import type { CSSProperties } from "react";
import { motion, useReducedMotion, useScroll, useSpring, useTransform } from "motion/react";
import type { PersonaAlbumBackdropItem } from "./personaStoryModel";
import "./PersonaAlbumBackdrop.css";

type PersonaAlbumBackdropProps = {
  albums: PersonaAlbumBackdropItem[];
};

type AlbumTile = {
  item: PersonaAlbumBackdropItem;
  layout: {
    left: number;
    top: number;
    size: number;
    mobileSize: number;
    opacity: number;
    rotateA: number;
    rotateB: number;
    tiltX: number;
    tiltY: number;
    floatX: number;
    floatY: number;
    scaleA: number;
    scaleB: number;
    duration: number;
    delay: number;
    depth: number;
    blur: number;
  };
};

const MAX_BACKDROP_ALBUMS = 20;

export function PersonaAlbumBackdrop({ albums }: PersonaAlbumBackdropProps) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const reducedMotion = useReducedMotion();
  const { scrollYProgress } = useScroll();
  const drift = useSpring(useTransform(scrollYProgress, [0, 1], ["-2vh", "5vh"]), { stiffness: 62, damping: 28, mass: 0.55 });
  const [tabHidden, setTabHidden] = useState(() => (typeof document === "undefined" ? false : document.hidden));
  const [smallViewport, setSmallViewport] = useState(() => (typeof window === "undefined" ? false : window.innerWidth < 720));

  useEffect(() => {
    const updateVisibility = () => setTabHidden(document.hidden);
    document.addEventListener("visibilitychange", updateVisibility);
    return () => document.removeEventListener("visibilitychange", updateVisibility);
  }, []);

  useEffect(() => {
    if (typeof window === "undefined") return;
    const media = window.matchMedia("(max-width: 719px)");
    const update = () => setSmallViewport(media.matches);
    update();
    media.addEventListener("change", update);
    return () => media.removeEventListener("change", update);
  }, []);

  const tiles = useMemo(() => {
    const limit = smallViewport ? Math.min(12, MAX_BACKDROP_ALBUMS) : MAX_BACKDROP_ALBUMS;
    return albums.slice(0, limit).map((item, index) => ({ item, layout: makeAlbumLayout(index, Math.min(albums.length, limit), smallViewport) }));
  }, [albums, smallViewport]);

  if (!tiles.length) return null;

  const paused = Boolean(reducedMotion || tabHidden || smallViewport);

  return (
    <div ref={containerRef} className="persona-album-backdrop" aria-hidden="true" data-paused={paused ? "true" : "false"}>
      <motion.div className="persona-album-backdrop__field" style={reducedMotion || smallViewport ? undefined : { y: drift }}>
        {tiles.map(({ item, layout }, index) => (
          <div
            key={`${item.albumBrowseId || item.albumTitle}-${item.artistName}-${index}`}
            className="persona-album-backdrop__tile"
            data-source={item.source}
            style={tileStyle(layout)}
          >
            <img src={item.albumImageUrl} alt="" loading={index < 5 ? "eager" : "lazy"} decoding="async" draggable={false} />
          </div>
        ))}
      </motion.div>
    </div>
  );
}

function tileStyle(layout: AlbumTile["layout"]) {
  return {
    "--album-left": `${layout.left}%`,
    "--album-top": `${layout.top}%`,
    "--album-size": `${layout.size}px`,
    "--album-mobile-size": `${layout.mobileSize}px`,
    "--album-opacity": layout.opacity,
    "--album-rotate-a": `${layout.rotateA}deg`,
    "--album-rotate-b": `${layout.rotateB}deg`,
    "--album-tilt-x": `${layout.tiltX}deg`,
    "--album-tilt-y": `${layout.tiltY}deg`,
    "--album-float-x": `${layout.floatX}px`,
    "--album-float-y": `${layout.floatY}px`,
    "--album-scale-a": layout.scaleA,
    "--album-scale-b": layout.scaleB,
    "--album-duration": `${layout.duration}s`,
    "--album-delay": `${layout.delay}s`,
    "--album-depth": layout.depth,
    "--album-blur": `${layout.blur}px`,
  } as CSSProperties;
}

function makeAlbumLayout(index: number, total: number, smallViewport: boolean): AlbumTile["layout"] {
  const denominator = Math.max(total - 1, 1);
  const angle = -148 + (296 * index) / denominator;
  const radians = (angle * Math.PI) / 180;
  const band = index % 5;
  const isEdge = band === 0 || band === 4;
  const left = 64 + Math.cos(radians) * (smallViewport ? 32 : 44) + ((index % 4) - 1.5) * 2.5;
  const top = 49 + Math.sin(radians) * (smallViewport ? 34 : 40) + ((index * 13) % 19) - 9;
  const direction = index % 2 === 0 ? 1 : -1;
  const size = (isEdge ? 178 : 126) + ((index * 29) % (isEdge ? 62 : 48));
  const mobileSize = 82 + ((index * 19) % 49);
  const rotateA = -6 + ((index * 7) % 13);

  return {
    left: clamp(left, smallViewport ? 18 : 32, 84),
    top: clamp(top, 7, 92),
    size,
    mobileSize,
    opacity: (isEdge ? 0.38 : 0.26) + ((index * 11) % 17) / 100,
    rotateA,
    rotateB: rotateA + direction * (2.6 + (index % 5) * 0.55),
    tiltX: -4 + ((index * 5) % 9),
    tiltY: -4 + ((index * 3) % 9),
    floatX: direction * (4 + ((index * 5) % 13)),
    floatY: 10 + ((index * 7) % 19),
    scaleA: 0.97 + (index % 3) * 0.01,
    scaleB: 1.01 + (index % 3) * 0.01,
    duration: 10 + ((index * 4) % 12),
    delay: -((index * 1.35) % 9),
    depth: 0.8 + ((index * 5) % 22) / 100,
    blur: isEdge ? 0 : index % 4 === 0 ? 1.2 : 0,
  };
}

function clamp(value: number, min: number, max: number) {
  return Math.min(max, Math.max(min, value));
}
