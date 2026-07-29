"use client";

import type { CSSProperties, ReactNode } from "react";
import { motion, useReducedMotion } from "motion/react";
import { cn } from "@/lib/utils";

type Variant =
  | "default"
  | "secondary"
  | "destructive"
  | "red"
  | "blue"
  | "green"
  | "yellow"
  | "purple"
  | "pink"
  | "orange"
  | "cyan"
  | "indigo"
  | "violet"
  | "rose"
  | "amber"
  | "lime"
  | "emerald"
  | "sky"
  | "slate"
  | "fuchsia";

interface ShimmerTextProps {
  children: ReactNode;
  className?: string;
  variant?: Variant;
  duration?: number;
  delay?: number;
  spread?: number;
}

const variantMap: Record<Variant, string> = {
  default: "",
  secondary: "text-secondary-foreground",
  destructive: "text-destructive dark:text-destructive-foreground",
  red: "text-red-600 dark:text-red-400",
  blue: "text-blue-600 dark:text-blue-400",
  green: "text-green-600 dark:text-green-400",
  yellow: "text-yellow-600 dark:text-yellow-400",
  purple: "text-purple-600 dark:text-purple-400",
  pink: "text-pink-600 dark:text-pink-400",
  orange: "text-orange-600 dark:text-orange-400",
  cyan: "text-cyan-600 dark:text-cyan-400",
  indigo: "text-indigo-600 dark:text-indigo-400",
  violet: "text-violet-600 dark:text-violet-400",
  rose: "text-rose-600 dark:text-rose-400",
  amber: "text-amber-600 dark:text-amber-400",
  lime: "text-lime-600 dark:text-lime-400",
  emerald: "text-emerald-600 dark:text-emerald-400",
  sky: "text-sky-600 dark:text-sky-400",
  slate: "text-slate-600 dark:text-slate-400",
  fuchsia: "text-fuchsia-600 dark:text-fuchsia-400",
};

export function ShimmerText({
  children,
  className,
  variant = "default",
  duration = 2.6,
  delay = 0.8,
  spread = 50,
}: ShimmerTextProps) {
  const reducedMotion = useReducedMotion();

  return (
    <div className="group max-w-full overflow-visible">
      <motion.div
        className={cn(
          "inline-block max-w-full [--shimmer-contrast:rgba(255,126,132,0.96)]",
          variantMap[variant],
          className,
        )}
        style={{
          WebkitTextFillColor: "transparent",
          backgroundImage:
            "linear-gradient(to right, currentColor 0%, currentColor 38%, var(--shimmer-contrast) 50%, currentColor 62%, currentColor 100%)",
          WebkitBackgroundClip: "text",
          backgroundClip: "text",
          backgroundRepeat: "repeat-x",
          backgroundSize: `${Math.max(180, spread * 4.4)}% 100%`,
        } as CSSProperties}
        initial={reducedMotion ? false : { backgroundPositionX: "200%" }}
        animate={reducedMotion ? undefined : { backgroundPositionX: ["200%", "-200%"] }}
        transition={reducedMotion ? undefined : {
          duration,
          delay,
          repeat: Infinity,
          repeatDelay: 2.4,
          ease: "linear",
        }}
      >
        {children}
      </motion.div>
    </div>
  );
}

export default ShimmerText;
