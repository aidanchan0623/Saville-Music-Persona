import { forwardRef } from "react";
import type { HTMLAttributes, ReactNode } from "react";
import "./ScrollStack.css";

type ScrollStackProps = HTMLAttributes<HTMLDivElement> & {
  children: ReactNode;
};

type ScrollStackItemProps = HTMLAttributes<HTMLElement> & {
  children: ReactNode;
};

export function ScrollStack({ children, className = "", ...props }: ScrollStackProps) {
  return (
    <div className={`scroll-stack${className ? ` ${className}` : ""}`} {...props}>
      {children}
    </div>
  );
}

export const ScrollStackItem = forwardRef<HTMLElement, ScrollStackItemProps>(function ScrollStackItem(
  { children, className = "", ...props },
  ref,
) {
  return (
    <section ref={ref} className={`scroll-stack__item${className ? ` ${className}` : ""}`} {...props}>
      {children}
    </section>
  );
});
