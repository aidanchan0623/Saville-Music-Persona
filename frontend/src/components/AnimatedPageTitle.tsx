import type { CSSProperties, ElementType } from "react";

type TitleTag = "h1" | "h2" | "h3";

interface AnimatedPageTitleProps {
  text: string;
  tag?: TitleTag;
  className?: string;
  animationKey: string;
  textAlign?: CSSProperties["textAlign"];
}

export function AnimatedPageTitle({ text, tag = "h1", className = "", animationKey, textAlign = "left" }: AnimatedPageTitleProps) {
  const Tag = tag as ElementType;
  return <Tag key={`${animationKey}:${text}`} className={className} style={{ textAlign }}>{text}</Tag>;
}
