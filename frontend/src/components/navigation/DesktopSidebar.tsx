import { Music2 } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { StatusPill } from "../StatusPill";
import LineSidebar from "../reactbits/LineSidebar/LineSidebar";
import { NAVIGATION_ITEMS, USE_REACT_BITS_DESKTOP_SIDEBAR } from "./navigation";
import type { Page } from "./navigation";

interface DesktopSidebarProps {
  activePage: Page;
  youtubeReady: boolean;
  youtubeLabel: string;
  spotifyConnected?: boolean;
  modelInstalled?: boolean;
  onNavigate: (page: Page) => void;
}

export function DesktopSidebar(props: DesktopSidebarProps) {
  const desktopMounted = useDesktopSidebarMounted();

  if (!desktopMounted) return null;

  return USE_REACT_BITS_DESKTOP_SIDEBAR ? <ReactBitsDesktopSidebar {...props} /> : <StandardSidebar {...props} />;
}

function ReactBitsDesktopSidebar({ activePage, youtubeReady, youtubeLabel, spotifyConnected, modelInstalled, onNavigate }: DesktopSidebarProps) {
  const labels = useMemo(() => NAVIGATION_ITEMS.map((item) => item.label), []);
  const activeIndex = NAVIGATION_ITEMS.findIndex((item) => item.id === activePage);

  return (
    <aside className="fixed inset-y-0 left-0 z-30 flex w-60 flex-col border-r border-line bg-backgroundElevated/95 p-5 shadow-[18px_0_70px_rgba(0,0,0,0.28)] backdrop-blur-xl">
      <SidebarBrand subtitle="Private taste analysis" />
      <div className="mt-8 min-h-0 flex-1 overflow-y-auto py-1 pr-1">
        <LineSidebar
          items={labels}
          activeIndex={activeIndex >= 0 ? activeIndex : null}
          onItemClick={(index) => {
            const item = NAVIGATION_ITEMS[index];
            if (item) onNavigate(item.id);
          }}
          ariaLabel="Primary navigation"
          accentColor="#ef2b2d"
          textColor="#a4a4ad"
          markerColor="#3f3f46"
          markerLength={24}
          markerGap={9}
          itemGap={16}
          maxShift={7}
          proximityRadius={72}
          smoothing={150}
          className="w-full"
        />
      </div>
      <LocalStatusPanel youtubeReady={youtubeReady} youtubeLabel={youtubeLabel} spotifyConnected={spotifyConnected} modelInstalled={modelInstalled} />
    </aside>
  );
}

function StandardSidebar({ activePage, youtubeReady, youtubeLabel, spotifyConnected, modelInstalled, onNavigate }: DesktopSidebarProps) {
  return (
    <aside className="fixed inset-y-0 left-0 z-30 flex w-60 flex-col border-r border-line bg-backgroundElevated/95 p-5 shadow-[18px_0_70px_rgba(0,0,0,0.28)] backdrop-blur-xl">
      <SidebarBrand subtitle="Private taste analysis" />
      <nav className="mt-8 min-h-0 flex-1 space-y-2 overflow-y-auto pr-1" aria-label="Primary navigation">
        {NAVIGATION_ITEMS.map((item) => {
          const Icon = item.icon;
          return (
            <button key={item.id} className={`nav-item ${activePage === item.id ? "nav-item-active" : ""}`} onClick={() => onNavigate(item.id)} aria-current={activePage === item.id ? "page" : undefined}>
              <Icon size={18} />
              {item.label}
            </button>
          );
        })}
      </nav>
      <LocalStatusPanel youtubeReady={youtubeReady} youtubeLabel={youtubeLabel} spotifyConnected={spotifyConnected} modelInstalled={modelInstalled} />
    </aside>
  );
}

function SidebarBrand({ subtitle }: { subtitle: string }) {
  return (
    <div className="flex items-center gap-3">
      <div className="grid h-11 w-11 place-items-center rounded-lg border border-red-400/25 bg-red-600/[0.18] text-red-100">
        <Music2 size={22} />
      </div>
      <div>
        <p className="font-bold leading-5">Saville Music</p>
        <p className="text-xs text-mist">{subtitle}</p>
      </div>
    </div>
  );
}

function LocalStatusPanel({
  youtubeReady,
  youtubeLabel,
  spotifyConnected,
  modelInstalled,
}: {
  youtubeReady: boolean;
  youtubeLabel: string;
  spotifyConnected?: boolean;
  modelInstalled?: boolean;
}) {
  return (
    <div className="mt-6 space-y-2 rounded-lg border border-line bg-white/[0.035] p-3">
      <p className="text-xs font-semibold uppercase tracking-[0.16em] text-mist/70">Local status</p>
      <StatusPill ok={youtubeReady} label={youtubeLabel} />
      <StatusPill ok={spotifyConnected} label={spotifyConnected ? "Spotify connected" : "Spotify optional"} />
      <StatusPill ok={Boolean(modelInstalled)} label={modelInstalled ? "Gemma ready" : "Gemma offline"} />
    </div>
  );
}

function useDesktopSidebarMounted() {
  const [desktopMounted, setDesktopMounted] = useState(() => {
    if (typeof window === "undefined" || typeof window.matchMedia !== "function") return true;
    return window.matchMedia("(min-width: 1024px)").matches;
  });

  useEffect(() => {
    if (typeof window.matchMedia !== "function") return;
    const media = window.matchMedia("(min-width: 1024px)");
    const update = () => setDesktopMounted(media.matches);
    update();
    media.addEventListener("change", update);
    return () => media.removeEventListener("change", update);
  }, []);

  return desktopMounted;
}
