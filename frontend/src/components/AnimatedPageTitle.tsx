import type { CSSProperties, ElementType } from "react";
import ShimmerText from "./ui/shimmer-text";

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
  return (
    <ShimmerText key={`${animationKey}:${text}`} className="max-w-full">
      <Tag className={className} style={{ textAlign }}>{text}</Tag>
    </ShimmerText>
  );
}
