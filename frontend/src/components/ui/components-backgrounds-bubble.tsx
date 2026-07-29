"use client";

import * as React from "react";
import {
  motion,
  useMotionValue,
  useReducedMotion,
  useSpring,
  type SpringOptions,
} from "motion/react";

import { cn } from "@/lib/utils";

type BubbleColors = {
  first: string;
  second: string;
  third: string;
  fourth: string;
  fifth: string;
  sixth: string;
};

type BubbleBackgroundProps = React.ComponentProps<"div"> & {
  interactive?: boolean;
  transition?: SpringOptions;
  colors?: BubbleColors;
};

function BubbleBackground({
  ref,
  className,
  children,
  interactive = false,
  transition = { stiffness: 100, damping: 20 },
  colors = {
    first: "239,43,45",
    second: "123,17,24",
    third: "255,74,77",
    fourth: "82,18,24",
    fifth: "126,34,42",
    sixth: "255,120,126",
  },
  ...props
}: BubbleBackgroundProps) {
  const containerRef = React.useRef<HTMLDivElement>(null);
  React.useImperativeHandle(ref, () => containerRef.current as HTMLDivElement);
  const reducedMotion = useReducedMotion();

  const mouseX = useMotionValue(0);
  const mouseY = useMotionValue(0);
  const springX = useSpring(mouseX, transition);
  const springY = useSpring(mouseY, transition);

  const rectRef = React.useRef<DOMRect | null>(null);
  const rafIdRef = React.useRef<number | null>(null);

  React.useLayoutEffect(() => {
    const updateRect = () => {
      if (containerRef.current) rectRef.current = containerRef.current.getBoundingClientRect();
    };
    updateRect();
    const el = containerRef.current;
    const ro = new ResizeObserver(updateRect);
    if (el) ro.observe(el);
    window.addEventListener("resize", updateRect);
    window.addEventListener("scroll", updateRect, { passive: true });
    return () => {
      ro.disconnect();
      window.removeEventListener("resize", updateRect);
      window.removeEventListener("scroll", updateRect);
    };
  }, []);

  React.useEffect(() => {
    if (!interactive || reducedMotion) return;
    const el = containerRef.current;
    if (!el) return;
    const handleMouseMove = (event: MouseEvent) => {
      const rect = rectRef.current;
      if (!rect) return;
      const centerX = rect.left + rect.width / 2;
      const centerY = rect.top + rect.height / 2;
      if (rafIdRef.current != null) cancelAnimationFrame(rafIdRef.current);
      rafIdRef.current = requestAnimationFrame(() => {
        mouseX.set(event.clientX - centerX);
        mouseY.set(event.clientY - centerY);
      });
    };
    el.addEventListener("mousemove", handleMouseMove, { passive: true });
    return () => {
      el.removeEventListener("mousemove", handleMouseMove);
      if (rafIdRef.current != null) cancelAnimationFrame(rafIdRef.current);
    };
  }, [interactive, mouseX, mouseY, reducedMotion]);

  const looping = (animation: Record<string, number | number[]>, duration: number) => reducedMotion
    ? { animate: undefined, transition: undefined }
    : { animate: animation, transition: { duration, ease: "easeInOut" as const, repeat: Infinity } };

  return (
    <div
      ref={containerRef}
      data-slot="bubble-background"
      className={cn("relative size-full overflow-hidden bg-black", className)}
      {...props}
    >
      <style>{`:root{--first-color:${colors.first};--second-color:${colors.second};--third-color:${colors.third};--fourth-color:${colors.fourth};--fifth-color:${colors.fifth};--sixth-color:${colors.sixth};}`}</style>
      <svg xmlns="http://www.w3.org/2000/svg" className="absolute left-0 top-0 h-0 w-0" aria-hidden="true">
        <defs>
          <filter id="smp-bubble-goo">
            <feGaussianBlur in="SourceGraphic" stdDeviation="16" result="blur" />
            <feColorMatrix in="blur" mode="matrix" values="1 0 0 0 0  0 1 0 0 0  0 0 1 0 0  0 0 0 18 -8" result="goo" />
            <feBlend in="SourceGraphic" in2="goo" />
          </filter>
        </defs>
      </svg>
      <div className="absolute inset-0" style={{ filter: "url(#smp-bubble-goo) blur(46px)" }}>
        <motion.div className="absolute left-[8%] top-[4%] size-[72%] rounded-full bg-[radial-gradient(circle_at_center,rgba(var(--first-color),0.64)_0%,rgba(var(--first-color),0)_54%)] mix-blend-screen" {...looping({ y: [-44, 44, -44] }, 34)} />
        <motion.div className="absolute inset-0 flex origin-[calc(50%-360px)] items-center justify-center" {...looping({ rotate: 360 }, 42)}>
          <div className="size-[68%] rounded-full bg-[radial-gradient(circle_at_center,rgba(var(--second-color),0.62)_0%,rgba(var(--second-color),0)_52%)] mix-blend-screen" />
        </motion.div>
        <motion.div className="absolute inset-0 flex origin-[calc(50%+400px)] items-center justify-center" {...looping({ rotate: -360 }, 54)}>
          <div className="absolute left-[calc(50%-460px)] top-[calc(50%+140px)] size-[72%] rounded-full bg-[radial-gradient(circle_at_center,rgba(var(--third-color),0.46)_0%,rgba(var(--third-color),0)_52%)] mix-blend-screen" />
        </motion.div>
        <motion.div className="absolute left-[14%] top-[12%] size-[66%] rounded-full bg-[radial-gradient(circle_at_center,rgba(var(--fourth-color),0.56)_0%,rgba(var(--fourth-color),0)_54%)] mix-blend-screen" {...looping({ x: [-42, 42, -42] }, 48)} />
        <motion.div className="absolute inset-0 flex origin-[calc(50%_-_720px)_calc(50%_+_180px)] items-center justify-center" {...looping({ rotate: 360 }, 58)}>
          <div className="absolute left-[calc(50%-70%)] top-[calc(50%-70%)] size-[140%] rounded-full bg-[radial-gradient(circle_at_center,rgba(var(--fifth-color),0.42)_0%,rgba(var(--fifth-color),0)_52%)] mix-blend-screen" />
        </motion.div>
        {interactive && !reducedMotion ? (
          <motion.div className="absolute size-full rounded-full bg-[radial-gradient(circle_at_center,rgba(var(--sixth-color),0.45)_0%,rgba(var(--sixth-color),0)_52%)] mix-blend-screen" style={{ x: springX, y: springY }} />
        ) : null}
      </div>
      {children}
    </div>
  );
}

export { BubbleBackground, type BubbleBackgroundProps };
export default BubbleBackground;
