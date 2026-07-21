import { useEffect, useMemo, useRef, useState } from "react";

type CountUpProps = {
  from?: number;
  to: number;
  duration?: number;
  separator?: string;
  decimals?: number;
  className?: string;
};

function prefersReducedMotion() {
  return typeof window !== "undefined" && typeof window.matchMedia === "function" && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
}

function formatValue(value: number, separator: string, decimals: number) {
  const fixed = value.toFixed(decimals);
  const [whole, fraction] = fixed.split(".");
  const grouped = separator ? whole.replace(/\B(?=(\d{3})+(?!\d))/g, separator) : whole;
  return fraction ? `${grouped}.${fraction}` : grouped;
}

export default function CountUp({ from = 0, to, duration = 1.2, separator = ",", decimals, className = "" }: CountUpProps) {
  const resolvedDecimals = useMemo(() => decimals ?? (Number.isInteger(to) ? 0 : 1), [decimals, to]);
  const [value, setValue] = useState(from);
  const nodeRef = useRef<HTMLSpanElement | null>(null);
  const frameRef = useRef<number | null>(null);
  const hasAnimatedRef = useRef(false);
  const targetRef = useRef(to);

  useEffect(() => {
    if (targetRef.current !== to) {
      targetRef.current = to;
      hasAnimatedRef.current = false;
      setValue(from);
    }
  }, [from, to]);

  useEffect(() => {
    const node = nodeRef.current;
    if (!node) return;

    const finish = () => {
      setValue(to);
      hasAnimatedRef.current = true;
    };

    const animate = () => {
      if (hasAnimatedRef.current) return;
      if (prefersReducedMotion() || duration <= 0) {
        finish();
        return;
      }
      const start = performance.now();
      const range = to - from;
      const durationMs = duration * 1000;
      const tick = (now: number) => {
        const progress = Math.min(1, (now - start) / durationMs);
        const eased = 1 - (1 - progress) ** 3;
        setValue(from + range * eased);
        if (progress < 1) {
          frameRef.current = requestAnimationFrame(tick);
        } else {
          finish();
        }
      };
      frameRef.current = requestAnimationFrame(tick);
    };

    if (typeof IntersectionObserver === "undefined") {
      animate();
      return () => {
        if (frameRef.current !== null) cancelAnimationFrame(frameRef.current);
      };
    }

    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry?.isIntersecting) {
          animate();
          observer.disconnect();
        }
      },
      { threshold: 0.35 },
    );
    observer.observe(node);
    return () => {
      observer.disconnect();
      if (frameRef.current !== null) cancelAnimationFrame(frameRef.current);
    };
  }, [duration, from, to]);

  return (
    <span ref={nodeRef} className={className}>
      {formatValue(value, separator, resolvedDecimals)}
    </span>
  );
}
