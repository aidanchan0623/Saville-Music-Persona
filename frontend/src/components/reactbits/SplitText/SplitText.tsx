import { useEffect, useRef, useState } from "react";
import type { CSSProperties, ElementType } from "react";
import { useGSAP } from "@gsap/react";
import { gsap } from "gsap";
import { ScrollTrigger } from "gsap/ScrollTrigger";
import { SplitText as GSAPSplitText } from "gsap/SplitText";
import "./SplitText.css";

gsap.registerPlugin(ScrollTrigger, GSAPSplitText, useGSAP);

type HeadingTag = "h1" | "h2" | "h3" | "h4" | "h5" | "h6" | "p" | "span";
type SplitType = "chars" | "words" | "lines" | "words, chars";

export interface SplitTextProps {
  text: string;
  className?: string;
  delay?: number;
  duration?: number;
  ease?: string | ((progress: number) => number);
  splitType?: SplitType;
  from?: gsap.TweenVars;
  to?: gsap.TweenVars;
  threshold?: number;
  rootMargin?: string;
  tag?: HeadingTag;
  textAlign?: CSSProperties["textAlign"];
  disabled?: boolean;
  onAnimationComplete?: () => void;
}

function prefersReducedMotion() {
  return typeof window !== "undefined" && typeof window.matchMedia === "function" && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
}

function useFontsReady() {
  const [ready, setReady] = useState(() => typeof document === "undefined" || !("fonts" in document) || document.fonts.status === "loaded");

  useEffect(() => {
    if (typeof document === "undefined" || !("fonts" in document) || document.fonts.status === "loaded") {
      setReady(true);
      return;
    }

    let cancelled = false;
    document.fonts.ready.then(() => {
      if (!cancelled) setReady(true);
    });
    return () => {
      cancelled = true;
    };
  }, []);

  return ready;
}

export default function SplitText({
  text,
  className = "",
  delay = 50,
  duration = 1.25,
  ease = "power3.out",
  splitType = "chars",
  from = { opacity: 0, y: 40 },
  to = { opacity: 1, y: 0 },
  threshold = 0.1,
  rootMargin = "-100px",
  textAlign = "left",
  tag = "p",
  disabled = false,
  onAnimationComplete,
}: SplitTextProps) {
  const ref = useRef<HTMLElement | null>(null);
  const completedRef = useRef(false);
  const onCompleteRef = useRef(onAnimationComplete);
  const fontsReady = useFontsReady();
  const shouldAnimate = !disabled && !prefersReducedMotion();

  useEffect(() => {
    onCompleteRef.current = onAnimationComplete;
  }, [onAnimationComplete]);

  useGSAP(
    () => {
      const element = ref.current;
      if (!element || !text || !fontsReady || !shouldAnimate || completedRef.current) return;

      const startPct = (1 - threshold) * 100;
      const marginMatch = /^(-?\d+(?:\.\d+)?)(px|em|rem|%)?$/.exec(rootMargin);
      const marginValue = marginMatch ? parseFloat(marginMatch[1]) : 0;
      const marginUnit = marginMatch ? marginMatch[2] || "px" : "px";
      const sign = marginValue === 0 ? "" : marginValue < 0 ? `-=${Math.abs(marginValue)}${marginUnit}` : `+=${marginValue}${marginUnit}`;
      const start = `top ${startPct}%${sign}`;

      let splitInstance: GSAPSplitText | null = null;
      let tween: gsap.core.Tween | null = null;

      try {
        splitInstance = new GSAPSplitText(element, {
          type: splitType,
          smartWrap: true,
          autoSplit: splitType === "lines",
          linesClass: "smp-split-line",
          wordsClass: "smp-split-word",
          charsClass: "smp-split-char",
          reduceWhiteSpace: false,
        });

        let targets: Element[] = [];
        if (splitType.includes("chars") && splitInstance.chars.length) targets = splitInstance.chars;
        if (!targets.length && splitType.includes("words") && splitInstance.words.length) targets = splitInstance.words;
        if (!targets.length && splitType.includes("lines") && splitInstance.lines.length) targets = splitInstance.lines;

        if (!targets.length) {
          splitInstance.revert();
          splitInstance = null;
          return;
        }

        tween = gsap.fromTo(
          targets,
          { ...from },
          {
            ...to,
            duration,
            ease,
            stagger: delay / 1000,
            scrollTrigger: {
              trigger: element,
              start,
              once: true,
              fastScrollEnd: true,
              anticipatePin: 0.4,
            },
            onComplete: () => {
              completedRef.current = true;
              onCompleteRef.current?.();
            },
            willChange: "transform, opacity",
            force3D: true,
          },
        );
      } catch {
        splitInstance?.revert();
        splitInstance = null;
      }

      return () => {
        tween?.kill();
        ScrollTrigger.getAll().forEach((trigger) => {
          if (trigger.trigger === element) trigger.kill();
        });
        splitInstance?.revert();
      };
    },
    {
      dependencies: [delay, duration, ease, splitType, JSON.stringify(from), JSON.stringify(to), threshold, rootMargin, fontsReady, shouldAnimate],
      scope: ref,
    },
  );

  const Tag = tag as ElementType;
  const classes = `smp-split-text${className ? ` ${className}` : ""}`;

  return (
    <Tag
      ref={(element: HTMLElement | null) => {
        ref.current = element;
      }}
      className={classes}
      aria-label={text}
      style={{ textAlign }}
    >
      {text}
    </Tag>
  );
}
