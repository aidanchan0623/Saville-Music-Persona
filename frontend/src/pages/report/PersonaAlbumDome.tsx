import { memo, useEffect, useMemo, useState } from "react";
import type { CSSProperties } from "react";
import { motion, useReducedMotion, useSpring, useTransform } from "motion/react";
import type { MotionValue } from "motion/react";
import type { PersonaBackgroundAlbum } from "../../types/api";
import "./PersonaAlbumDome.css";

interface Props {
  albums: PersonaBackgroundAlbum[];
  progress: MotionValue<number>;
}

export const PersonaAlbumDome = memo(function PersonaAlbumDome({ albums, progress }: Props) {
  const reducedMotion = useReducedMotion();
  const [hidden, setHidden] = useState(() => (typeof document === "undefined" ? false : document.hidden));
  const [mobile, setMobile] = useState(() => (typeof window === "undefined" ? false : window.matchMedia("(max-width: 767px)").matches));
  const rotate = useSpring(useTransform(progress, [0, 0.28, 0.55, 0.82, 1], [0, -3, 2.4, -2, 0]), { stiffness: 90, damping: 24 });
  const scale = useSpring(useTransform(progress, [0, 0.5, 0.82, 1], [1, 0.91, 1.06, 1]), { stiffness: 90, damping: 24 });
  const y = useSpring(useTransform(progress, [0, 0.5, 1], [0, -24, 12]), { stiffness: 90, damping: 24 });

  useEffect(() => {
    const onVisibility = () => setHidden(document.hidden);
    document.addEventListener("visibilitychange", onVisibility);
    return () => document.removeEventListener("visibilitychange", onVisibility);
  }, []);

  useEffect(() => {
    const query = window.matchMedia("(max-width: 767px)");
    const update = () => setMobile(query.matches);
    update();
    query.addEventListener("change", update);
    return () => query.removeEventListener("change", update);
  }, []);

  const tiles = useMemo(() => albums.slice(0, mobile ? 8 : 20).map((album, index) => ({ album, layout: layoutFor(index, mobile) })), [albums, mobile]);
  if (!tiles.length) return null;

  return (
    <div className="persona-album-dome" aria-hidden="true" data-paused={hidden || reducedMotion ? "true" : "false"}>
      <motion.div
        className="persona-album-dome__field"
        style={reducedMotion || mobile ? undefined : { rotateZ: rotate, scale, y }}
      >
        {tiles.map(({ album, layout }, index) => (
          <div
            className="persona-album-dome__tile"
            key={album.albumBrowseId || `${album.albumTitle}-${album.artistName}`}
            style={layout as CSSProperties}
          >
            <img
              src={album.albumImageUrl}
              alt=""
              loading={index < 4 ? "eager" : "lazy"}
              decoding="async"
              draggable={false}
              onError={(event) => { event.currentTarget.parentElement?.setAttribute("hidden", ""); }}
            />
          </div>
        ))}
      </motion.div>
    </div>
  );
});

function layoutFor(index: number, mobile: boolean) {
  const columns = mobile ? 4 : 7;
  const row = Math.floor(index / columns);
  const column = index % columns;
  const xStep = mobile ? 29 : 16.5;
  const left = mobile ? 5 + column * xStep : 1 + column * xStep + (row % 2 ? 7 : 0);
  const topRows = mobile ? [10, 37] : [5, 31, 67];
  const arc = Math.abs(column - (columns - 1) / 2) * (mobile ? 2.5 : 4.2);
  const size = mobile ? 78 + ((index * 17) % 48) : 92 + ((index * 37) % 154);
  const direction = index % 2 ? -1 : 1;
  return {
    "--dome-left": `${left}%`,
    "--dome-top": `${(topRows[row] ?? 83) + arc}%`,
    "--dome-size": `${size}px`,
    "--dome-opacity": `${0.38 + ((index * 7) % 29) / 100}`,
    "--dome-rotate": `${-4.5 + ((index * 11) % 10)}deg`,
    "--dome-tilt": `${direction * (1 + (index % 4))}deg`,
    "--dome-float-x": `${direction * (5 + ((index * 3) % 13))}px`,
    "--dome-float-y": `${10 + ((index * 5) % 21)}px`,
    "--dome-duration": `${11 + ((index * 7) % 14)}s`,
    "--dome-delay": `${-((index * 1.9) % 13)}s`,
    "--dome-depth": `${20 + ((index * 17) % 90)}px`,
  };
}
