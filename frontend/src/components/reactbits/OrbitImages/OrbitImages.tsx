import { useEffect, useMemo, useState } from "react";
import { useRef } from "react";
import type { CSSProperties } from "react";
import "./OrbitImages.css";

export type OrbitImageItem = {
  src: string;
  alt: string;
};

type OrbitImagesProps = {
  items: OrbitImageItem[];
  className?: string;
  priority?: boolean;
  active?: boolean;
};

export function OrbitImages({ items, className = "", priority = false, active }: OrbitImagesProps) {
  const ref = useRef<HTMLDivElement | null>(null);
  const [paused, setPaused] = useState(() => (typeof document === "undefined" ? false : document.hidden));
  const [inView, setInView] = useState(false);
  const safeItems = useMemo(() => items.filter((item) => item.src).slice(0, 8), [items]);

  useEffect(() => {
    const handleVisibility = () => setPaused(document.hidden);
    document.addEventListener("visibilitychange", handleVisibility);
    return () => document.removeEventListener("visibilitychange", handleVisibility);
  }, []);

  useEffect(() => {
    const node = ref.current;
    if (!node) return;
    const observer = new IntersectionObserver(
      ([entry]) => setInView(entry.isIntersecting),
      { threshold: 0.04, rootMargin: "120px 0px" },
    );
    observer.observe(node);
    return () => observer.disconnect();
  }, []);

  if (!safeItems.length) return null;
  const shouldRenderImages = active ?? inView;

  return (
    <div ref={ref} className={`orbit-images${paused || !shouldRenderImages ? " orbit-images--paused" : ""}${className ? ` ${className}` : ""}`} aria-hidden="true">
      <div className="orbit-images__glow" />
      <div className="orbit-images__ring">
        {shouldRenderImages ? safeItems.map((item, index) => {
          const angle = Math.round((360 / safeItems.length) * index);
          return (
            <img
              key={`${item.src}-${index}`}
              className="orbit-images__image"
              src={item.src}
              alt=""
              loading={priority && index < 2 ? "eager" : "lazy"}
              decoding="async"
              style={{ "--orbit-transform": `rotate(${angle}deg) translateX(var(--orbit-radius)) rotate(${-angle}deg)` } as CSSProperties}
            />
          );
        }) : null}
      </div>
    </div>
  );
}
