import { useEffect, useState } from "react";
import type { CSSProperties, ElementType } from "react";
import SplitText from "./reactbits/SplitText/SplitText";

type TitleTag = "h1" | "h2" | "h3";

interface AnimatedPageTitleProps {
  text: string;
  tag?: TitleTag;
  className?: string;
  animationKey: string;
  textAlign?: CSSProperties["textAlign"];
}

const animatedKeys = new Set<string>();

function useReducedMotion() {
  const [reduced, setReduced] = useState(() => {
    if (typeof window === "undefined" || typeof window.matchMedia !== "function") return false;
    return window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  });

  useEffect(() => {
    if (typeof window.matchMedia !== "function") return;
    const media = window.matchMedia("(prefers-reduced-motion: reduce)");
    const update = () => setReduced(media.matches);
    update();
    media.addEventListener("change", update);
    return () => media.removeEventListener("change", update);
  }, []);

  return reduced;
}

export function AnimatedPageTitle({ text, tag = "h1", className = "", animationKey, textAlign = "left" }: AnimatedPageTitleProps) {
  const reducedMotion = useReducedMotion();
  const [animate] = useState(() => !animatedKeys.has(animationKey));

  if (reducedMotion || !animate) {
    const Tag = tag as ElementType;
    return <Tag className={className} style={{ textAlign }}>{text}</Tag>;
  }

  return (
    <SplitText
      key={animationKey}
      tag={tag}
      text={text}
      className={className}
      delay={35}
      duration={0.55}
      ease="power3.out"
      splitType="words"
      from={{
        opacity: 0,
        y: -28,
        rotationX: -8,
      }}
      to={{
        opacity: 1,
        y: 0,
        rotationX: 0,
      }}
      threshold={0.05}
      rootMargin="0px"
      textAlign={textAlign}
      onAnimationComplete={() => animatedKeys.add(animationKey)}
    />
  );
}
