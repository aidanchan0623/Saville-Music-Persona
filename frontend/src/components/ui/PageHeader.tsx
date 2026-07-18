import type { ReactNode } from "react";

interface PageHeaderProps {
  eyebrow: string;
  title: string;
  description?: string;
  meta?: ReactNode;
  action?: ReactNode;
}

export function PageHeader({ eyebrow, title, description, meta, action }: PageHeaderProps) {
  return (
    <header className="flex flex-col gap-5 lg:flex-row lg:items-end lg:justify-between">
      <div className="max-w-4xl">
        <p className="section-label">{eyebrow}</p>
        <h1 className="mt-3 font-display text-4xl uppercase leading-[0.9] tracking-[0.03em] text-white md:text-6xl">{title}</h1>
        {description ? <p className="mt-4 max-w-3xl text-base leading-7 text-mist md:text-lg">{description}</p> : null}
        {meta ? <div className="mt-4 flex flex-wrap gap-2">{meta}</div> : null}
      </div>
      {action ? <div className="flex shrink-0 flex-wrap gap-2">{action}</div> : null}
    </header>
  );
}
