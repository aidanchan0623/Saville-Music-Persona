import type { ElementType, ReactNode } from "react";
import { useMemo, useState } from "react";

export interface LineSidebarItem<T extends string> {
  id: T;
  label: string;
  kicker: string;
  icon: ElementType;
}

interface LineSidebarProps<T extends string> {
  items: LineSidebarItem<T>[];
  active: T;
  onNavigate: (id: T) => void;
  footer?: ReactNode;
  className?: string;
}

const itemHeight = 58;
const firstItemTop = 130;

export function LineSidebar<T extends string>({ items, active, onNavigate, footer, className = "" }: LineSidebarProps<T>) {
  const [hovered, setHovered] = useState<T | null>(null);
  const markerIndex = useMemo(() => {
    const target = hovered ?? active;
    return Math.max(0, items.findIndex((item) => item.id === target));
  }, [active, hovered, items]);

  return (
    <aside className={`relative flex flex-col overflow-hidden border-r border-white/10 bg-[#070505]/92 p-5 text-white backdrop-blur-2xl ${className}`}>
      <div className="absolute inset-y-5 left-5 w-px bg-gradient-to-b from-transparent via-red-500/25 to-transparent" />
      <div
        className="absolute left-[1.17rem] h-12 w-px rounded-full bg-red-400 shadow-[0_0_24px_rgba(239,68,68,0.72)] transition-transform duration-300"
        style={{ transform: `translateY(${firstItemTop + markerIndex * itemHeight}px)` }}
        aria-hidden="true"
      />

      <div className="relative pl-5">
        <button className="group flex w-full items-center gap-3 rounded-lg text-left focus:outline-none focus-visible:ring-2 focus-visible:ring-red-400" onClick={() => onNavigate("overview" as T)}>
          <span className="grid h-12 w-12 place-items-center rounded-lg border border-red-400/30 bg-red-600 text-white shadow-[0_0_34px_rgba(220,38,38,0.28)]">
            <span className="font-display text-xl leading-none">S</span>
          </span>
          <span>
            <span className="block font-display text-xl uppercase leading-none tracking-[0.06em]">Saville</span>
            <span className="mt-1 block text-xs uppercase tracking-[0.2em] text-red-200/75">Music Persona</span>
          </span>
        </button>
      </div>

      <nav className="relative mt-12 min-h-0 flex-1 space-y-1 overflow-y-auto pb-5 pl-5 pr-1" aria-label="Primary navigation">
        {items.map((item) => {
          const Icon = item.icon;
          const activeItem = item.id === active;
          return (
            <button
              key={item.id}
              type="button"
              className={`group flex h-[3.25rem] w-full items-center gap-3 rounded-lg px-3 text-left transition focus:outline-none focus-visible:ring-2 focus-visible:ring-red-400 ${
                activeItem ? "bg-red-500/12 text-white" : "text-mist hover:bg-white/[0.045] hover:text-white"
              }`}
              data-nav-id={item.id}
              aria-current={activeItem ? "page" : undefined}
              onClick={() => onNavigate(item.id)}
              onMouseEnter={() => setHovered(item.id)}
              onMouseLeave={() => setHovered(null)}
            >
              <span className={`grid h-9 w-9 shrink-0 place-items-center rounded-md border transition ${activeItem ? "border-red-400/40 bg-red-500/20 text-red-100" : "border-white/10 bg-white/[0.035] text-mist group-hover:border-red-400/25 group-hover:text-red-100"}`}>
                <Icon size={18} />
              </span>
              <span className="min-w-0">
                <span className="block truncate text-sm font-semibold">{item.label}</span>
                <span className="mt-0.5 block truncate text-[0.68rem] uppercase tracking-[0.16em] text-mist/55">{item.kicker}</span>
              </span>
            </button>
          );
        })}
      </nav>

      {footer ? <div className="relative mt-auto border-t border-white/10 pt-4 pl-5">{footer}</div> : null}
    </aside>
  );
}
