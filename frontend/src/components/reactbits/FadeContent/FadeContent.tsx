import { useEffect, useRef, useState } from "react";
import type { CSSProperties, ReactNode } from "react";
import "./FadeContent.css";

type FadeContentProps = {
  children: ReactNode;
  as?: "div" | "span";
  className?: string;
  delay?: number;
  duration?: number;
  distance?: number;
  threshold?: number;
};

function prefersReducedMotion() {
  return typeof window !== "undefined" && typeof window.matchMedia === "function" && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
}

export function FadeContent({
  children,
  as = "div",
  className = "",
  delay = 0,
  duration = 0.68,
  distance = 34,
  threshold = 0.2,
}: FadeContentProps) {
  const nodeRef = useRef<HTMLElement | null>(null);
  const [visible, setVisible] = useState(false);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    if (prefersReducedMotion()) {
      setVisible(true);
      setReady(true);
      return;
    }
    const node = nodeRef.current;
    if (!node || typeof IntersectionObserver === "undefined") {
      setVisible(true);
      setReady(true);
      return;
    }
    setReady(true);
    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry?.isIntersecting) {
          setVisible(true);
          observer.disconnect();
        }
      },
      { threshold },
    );
    observer.observe(node);
    return () => observer.disconnect();
  }, [threshold]);

  const style = {
    "--fade-content-delay": `${delay}s`,
    "--fade-content-duration": `${duration}s`,
    "--fade-content-distance": `${distance}px`,
  } as CSSProperties;
  const content = {
    className: `fade-content${className ? ` ${className}` : ""}`,
    "data-ready": ready ? "true" : "false",
    "data-visible": visible ? "true" : "false",
    style,
    children,
  };

  if (as === "span") {
    return (
      <span
        ref={(node) => {
          nodeRef.current = node;
        }}
        {...content}
      />
    );
  }

  return (
    <div
      ref={(node) => {
        nodeRef.current = node;
      }}
      {...content}
    />
  );
}
