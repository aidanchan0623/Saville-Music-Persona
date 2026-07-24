import { Menu, Music2, X } from "lucide-react";
import { useEffect, useMemo, useRef, useState } from "react";
import { api } from "./api/client";
import { pollTakeoutImport, runExclusiveOperation } from "./api/takeoutImport";
import { GlowPanel } from "./components/GlowPanel";
import { DesktopSidebar } from "./components/navigation/DesktopSidebar";
import { NAVIGATION_ITEMS } from "./components/navigation/navigation";
import type { Page } from "./components/navigation/navigation";
import { OverviewPage } from "./pages/OverviewPage";
import { InsightsPage } from "./pages/InsightsPage";
import { RecommendationsPage } from "./pages/RecommendationsPage";
import { ReportPage } from "./pages/ReportPage";
import { SettingsPage } from "./pages/SettingsPage";
import { Top10Page } from "./pages/Top10Page";
import type { AuthStatus, MusicSource, OverviewResponse, PersonaReport, Prerequisites, Recommendation, SpotifyStatus, TopArtist, TopTrack } from "./types/api";

const PAGE_PATHS: Record<Page, string> = {
  overview: "/",
  top10: "/top10",
  insights: "/insights",
  report: "/report",
  recommendations: "/recommendations",
  settings: "/settings",
};

const PATH_PAGES = new Map(Object.entries(PAGE_PATHS).map(([page, path]) => [path, page as Page]));

function getHistoryPage(): Page {
  if (typeof window === "undefined") return "overview";
  const path = normalisePath(window.location.pathname);
  if (path === "/scores" || path === "/patterns") return "insights";
  const routePage = PATH_PAGES.get(path);
  if (routePage) return routePage;
  const value = window.history.state?.page;
  return NAVIGATION_ITEMS.some((item) => item.id === value) ? value : "overview";
}

function normalisePath(pathname: string) {
  if (!pathname || pathname === "/") return "/";
  return pathname.replace(/\/+$/, "").toLowerCase();
}

export default function App() {
  const [page, setPage] = useState<Page>(() => getHistoryPage());
  const [titleVisitId, setTitleVisitId] = useState(0);
  const [mobileOpen, setMobileOpen] = useState(false);
  const [source, setSource] = useState<MusicSource>(() => {
    const querySource = new URLSearchParams(window.location.search).get("source");
    if (querySource === "spotify") return "spotify";
    return "youtube";
  });
  const [useDemo, setUseDemo] = useState(() => localStorage.getItem("smp_use_demo") === "true");
  const [overview, setOverview] = useState<OverviewResponse | null>(null);
  const [tracks, setTracks] = useState<TopTrack[]>([]);
  const [artists, setArtists] = useState<TopArtist[]>([]);
  const [report, setReport] = useState<PersonaReport | null>(null);
  const [recommendations, setRecommendations] = useState<Recommendation[]>([]);
  const [auth, setAuth] = useState<AuthStatus | null>(null);
  const [spotifyStatus, setSpotifyStatus] = useState<SpotifyStatus | null>(null);
  const [prerequisites, setPrerequisites] = useState<Prerequisites | null>(null);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const loadAnalysisTokenRef = useRef(0);
  const operationInFlightRef = useRef(false);
  const importAbortControllerRef = useRef<AbortController | null>(null);
  const lastTakeoutFileRef = useRef<File | null>(null);
  const skipNextSourceLoadRef = useRef(false);
  const [canRetryTakeout, setCanRetryTakeout] = useState(false);

  const loadStatus = async () => {
    const [nextPrerequisites, nextAuth, nextSpotifyStatus] = await Promise.all([api.prerequisites(), api.authStatus(), api.spotifyStatus()]);
    setPrerequisites(nextPrerequisites);
    setAuth(nextAuth);
    setSpotifyStatus(nextSpotifyStatus);
  };

  const clearAnalysis = () => {
    loadAnalysisTokenRef.current += 1;
    setOverview(null);
    setTracks([]);
    setArtists([]);
    setReport(null);
    setRecommendations([]);
  };

  const navigate = (next: Page) => {
    if (next !== page) {
      window.history.pushState({ ...(window.history.state ?? {}), page: next }, "", `${PAGE_PATHS[next]}${window.location.search}`);
      setTitleVisitId((value) => value + 1);
    }
    setPage(next);
    setMobileOpen(false);
  };

  const loadAnalysis = async (activeSource: MusicSource = source) => {
    const requestToken = loadAnalysisTokenRef.current + 1;
    loadAnalysisTokenRef.current = requestToken;
    const isCurrentRequest = () => loadAnalysisTokenRef.current === requestToken;
    const setIfCurrent = <T,>(setter: (value: T) => void) => (value: T) => {
      if (isCurrentRequest()) setter(value);
    };
    setReport(null);
    void api.latestReport(activeSource)
      .then(setIfCurrent(setReport))
      .catch(() => { if (isCurrentRequest()) setReport(null); });
    const nextOverview = await api.overview("this_month", null, activeSource);
    if (!isCurrentRequest()) return;
    setOverview(nextOverview);
    setMessage(null);
    setTracks([]);
    setArtists([]);
    void api.topTracks(activeSource).then(setIfCurrent(setTracks)).catch(() => { if (isCurrentRequest()) setTracks([]); });
    void api.topArtists(activeSource).then(setIfCurrent(setArtists)).catch(() => { if (isCurrentRequest()) setArtists([]); });
    if (activeSource === "youtube") {
      try {
        const nextRecommendations = await api.recommendations();
        if (isCurrentRequest()) setRecommendations(nextRecommendations);
      } catch {
        if (isCurrentRequest()) setRecommendations([]);
      }
    } else {
      if (isCurrentRequest()) setRecommendations([]);
    }
  };

  useEffect(() => {
    localStorage.setItem("smp_use_demo", String(useDemo));
  }, [useDemo]);

  useEffect(() => {
    void loadStatus().catch((error) => setMessage(error.message));
  }, []);

  useEffect(() => {
    const legacyPath = ["/scores", "/patterns"].includes(normalisePath(window.location.pathname));
    window.history.replaceState(
      { ...(window.history.state ?? {}), page },
      "",
      legacyPath ? `${PAGE_PATHS.insights}${window.location.search}` : window.location.href,
    );
    const handlePopState = () => {
      setPage(getHistoryPage());
      setTitleVisitId((value) => value + 1);
      setMobileOpen(false);
    };
    window.addEventListener("popstate", handlePopState);
    return () => window.removeEventListener("popstate", handlePopState);
  }, []);

  useEffect(() => {
    if (skipNextSourceLoadRef.current) {
      skipNextSourceLoadRef.current = false;
      return;
    }
    void loadAnalysis(source).catch((error) => {
      clearAnalysis();
      setMessage(
        error instanceof Error
          ? error.message
          : source === "spotify"
            ? "Connect Spotify in Settings, then refresh Spotify data."
            : "YouTube Music analysis could not be loaded.",
      );
    });
  }, [source]);

  useEffect(() => () => importAbortControllerRef.current?.abort(), []);

  const refresh = async () => {
    const started = await runExclusiveOperation(operationInFlightRef, setBusy, async () => {
      setMessage(source === "spotify" ? "Refreshing local Spotify data..." : useDemo ? "Loading anonymised demo listening history..." : "Refreshing local YouTube Music data...");
      try {
        const response = source === "spotify" ? await api.spotifyRefresh() : await api.refresh(useDemo);
        await loadStatus();
        await loadAnalysis(source);
        setMessage(`Refreshed ${response.track_count} tracks and ${response.play_count} detected plays.`);
      } catch (error) {
        setMessage(error instanceof Error ? error.message : "Refresh failed.");
      }
    });
    if (!started) {
      setMessage("Another data operation is already running. Wait for it to finish before refreshing again.");
    }
  };

  const generateReport = async (mode: "serious" | "playful" | "roast" = "serious") => {
    setBusy(true);
    setMessage("Asking local Gemma to rewrite the deterministic Music Character profile...");
    try {
      const nextReport = await api.generateReport(mode, source);
      setReport(nextReport);
      navigate("report");
      setMessage("Persona report generated locally.");
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Report generation failed.");
    } finally {
      setBusy(false);
    }
  };

  const generateRecommendations = async () => {
    if (source === "spotify") {
      setMessage("Recommendations currently use YouTube Music history. Switch to YouTube Music to generate them.");
      return;
    }
    setBusy(true);
    setMessage("Building recommendations from your local taste profile...");
    try {
      const next = await api.generateRecommendations();
      setRecommendations(next);
      setMessage(`Generated ${next.length} recommendations.`);
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Recommendation generation failed.");
    } finally {
      setBusy(false);
    }
  };

  const importTakeout = async (file: File) => {
    lastTakeoutFileRef.current = file;
    setCanRetryTakeout(false);
    const started = await runExclusiveOperation(operationInFlightRef, setBusy, async () => {
      const controller = new AbortController();
      importAbortControllerRef.current = controller;
      setMessage(`Uploading ${file.name} from Google Takeout...`);
      try {
        const queued = await api.importTakeout(file, controller.signal);
        const result = await pollTakeoutImport(
          (signal) => api.takeoutImportStatus(queued.jobId, signal),
          {
            signal: controller.signal,
            onStatus: (status) => setMessage(`${status.message} (${status.progress}%)`),
          },
        );
        await loadStatus();
        await loadAnalysis("youtube");
        if (source !== "youtube") {
          skipNextSourceLoadRef.current = true;
          setSource("youtube");
        }
        setCanRetryTakeout(false);
        setMessage(`${result.message} Imported ${result.importedCount ?? 0} history entries.`);
        navigate("overview");
      } catch (error) {
        if (!(error instanceof DOMException && error.name === "AbortError")) {
          setCanRetryTakeout(true);
          setMessage(error instanceof Error ? error.message : "Takeout import failed. Retry with the same file.");
        }
      } finally {
        if (importAbortControllerRef.current === controller) importAbortControllerRef.current = null;
      }
    });
    if (!started) {
      setMessage("A Takeout import or refresh is already running. Wait for it to finish before starting another.");
    }
  };

  const retryTakeout = () => {
    const file = lastTakeoutFileRef.current;
    if (file) void importTakeout(file);
  };

  const createPlaylist = async () => {
    if (source === "spotify") {
      setMessage("Playlist creation currently uses YouTube Music recommendations. Switch back to YouTube Music first.");
      return;
    }
    const confirmed = window.confirm('Create a private YouTube Music playlist named "Saville Recommendations"?');
    if (!confirmed) return;
    setBusy(true);
    try {
      const result = await api.createPlaylist("Saville Recommendations");
      setMessage(`${result.message} Playlist ID: ${result.playlist_id}`);
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Playlist creation failed.");
    } finally {
      setBusy(false);
    }
  };

  const connectSpotify = () => {
    window.location.href = api.spotifyLoginUrl();
  };

  const refreshSpotify = async () => {
    setBusy(true);
    setMessage("Refreshing local Spotify data...");
    try {
      const response = await api.spotifyRefresh();
      await loadStatus();
      if (source === "spotify") {
        await loadAnalysis("spotify");
      }
      setMessage(`Refreshed Spotify with ${response.track_count} tracks and ${response.play_count} local signals.`);
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Spotify refresh failed.");
    } finally {
      setBusy(false);
    }
  };

  const disconnectSpotify = async () => {
    setBusy(true);
    try {
      const result = await api.spotifyDisconnect();
      await loadStatus();
      if (source === "spotify") {
        setSource("youtube");
      }
      setMessage(result.message);
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Spotify disconnect failed.");
    } finally {
      setBusy(false);
    }
  };

  const activePage = useMemo(() => {
    const titleAnimationKey = `${page}:${titleVisitId}`;
    switch (page) {
      case "overview":
        return (
          <OverviewPage
            overview={overview}
            auth={auth}
            prerequisites={prerequisites}
            busy={busy}
            useDemo={useDemo}
            onRefresh={refresh}
            onOpenSettings={() => navigate("settings")}
            onOpenReport={() => navigate("report")}
            source={source}
            titleAnimationKey={titleAnimationKey}
          />
        );
      case "top10":
        return <Top10Page source={source} titleAnimationKey={titleAnimationKey} />;
      case "insights":
        return <InsightsPage source={source} titleAnimationKey={titleAnimationKey} onOpenTop10={() => navigate("top10")} />;
      case "report":
        return <ReportPage report={report} prerequisites={prerequisites} busy={busy} onGenerate={generateReport} source={source} titleAnimationKey={titleAnimationKey} />;
      case "recommendations":
        return <RecommendationsPage recommendations={recommendations} busy={busy} onGenerate={generateRecommendations} onCreatePlaylist={createPlaylist} source={source} titleAnimationKey={titleAnimationKey} />;
      case "settings":
        return (
          <SettingsPage
            auth={auth}
            prerequisites={prerequisites}
            useDemo={useDemo}
            busy={busy}
            onUseDemoChange={setUseDemo}
            onCheckAuth={async () => {
              try {
                const liveAuth = await api.authStatus(true);
                setAuth(liveAuth);
                setMessage(liveAuth.message);
              } catch (error) {
                setMessage(error instanceof Error ? error.message : "YouTube live auth check failed.");
              }
            }}
            onImportTakeout={importTakeout}
            spotifyStatus={spotifyStatus}
            onConnectSpotify={connectSpotify}
            onRefreshSpotify={refreshSpotify}
            onDisconnectSpotify={disconnectSpotify}
            titleAnimationKey={titleAnimationKey}
          />
        );
    }
  }, [page, titleVisitId, overview, auth, spotifyStatus, prerequisites, busy, useDemo, tracks, artists, report, recommendations, source]);

  const youtubeAnalysisReady = overview?.source === "youtube";
  const youtubeReady = Boolean(auth?.connected || youtubeAnalysisReady || (useDemo && overview));
  const youtubeLabel = useDemo
    ? youtubeAnalysisReady ? "Demo data" : "Demo data loading"
    : auth?.connected
      ? "YouTube connected"
      : auth?.cached_data_available && youtubeAnalysisReady
        ? "YouTube data loaded"
        : auth?.cached_data_available
          ? "YouTube data pending"
          : "YouTube offline";
  const currentNav = NAVIGATION_ITEMS.find((item) => item.id === page) ?? NAVIGATION_ITEMS[0];

  return (
    <div className="min-h-screen bg-ink text-white">
      <div className="fixed inset-0 -z-10 bg-[radial-gradient(circle_at_70%_10%,rgba(239,43,45,0.16),transparent_28%),radial-gradient(circle_at_20%_80%,rgba(123,17,24,0.15),transparent_25%)]" />
      <DesktopSidebar activePage={page} youtubeReady={youtubeReady} youtubeLabel={youtubeLabel} spotifyConnected={spotifyStatus?.connected} modelInstalled={Boolean(prerequisites?.ollama_reachable && prerequisites.model_installed)} onNavigate={navigate} />

      {mobileOpen ? (
        <div className="fixed inset-0 z-40 lg:hidden">
          <button className="absolute inset-0 bg-black/72 backdrop-blur-sm" type="button" aria-label="Close navigation overlay" onClick={() => setMobileOpen(false)} />
          <aside className="relative flex h-full w-[min(20rem,calc(100vw-2rem))] flex-col border-r border-line bg-backgroundElevated p-5 shadow-[24px_0_80px_rgba(0,0,0,0.5)]">
            <div className="flex items-center justify-between gap-3">
              <div className="flex items-center gap-3">
                <div className="grid h-10 w-10 place-items-center rounded-lg border border-red-400/25 bg-red-600/[0.18] text-red-100">
                  <Music2 size={20} />
                </div>
                <div>
                  <p className="font-bold">Saville Music</p>
                  <p className="text-xs text-mist">Navigation</p>
                </div>
              </div>
              <button className="grid h-10 w-10 place-items-center rounded-md border border-line bg-white/[0.055] text-mist hover:text-white" type="button" aria-label="Close navigation" onClick={() => setMobileOpen(false)}>
                <X size={18} />
              </button>
            </div>
            <nav className="mt-8 min-h-0 flex-1 space-y-2 overflow-y-auto" aria-label="Mobile navigation">
              {NAVIGATION_ITEMS.map((item) => {
                const Icon = item.icon;
                return (
                  <button key={item.id} className={`nav-item ${page === item.id ? "nav-item-active" : ""}`} onClick={() => navigate(item.id)} aria-current={page === item.id ? "page" : undefined}>
                    <Icon size={18} />
                    {item.label}
                  </button>
                );
              })}
            </nav>
          </aside>
        </div>
      ) : null}

      <div className="min-w-0 lg:pl-60">
        <header className="sticky top-0 z-20 border-b border-line bg-backgroundElevated/90 px-4 py-3 backdrop-blur-xl lg:hidden">
          <div className="flex items-center justify-between gap-3">
            <button className="grid h-10 w-10 shrink-0 place-items-center rounded-md border border-line bg-white/[0.055] text-white" type="button" aria-label="Open navigation" onClick={() => setMobileOpen(true)}>
              <Menu size={19} />
            </button>
            <div className="min-w-0 flex-1">
              <p className="truncate text-sm font-bold">Saville</p>
              <p className="truncate text-xs text-mist">{currentNav.label}</p>
            </div>
            <select className="max-w-[11rem] rounded-md border border-line bg-panel px-3 py-2 text-sm text-white" value={page} onChange={(event) => navigate(event.target.value as Page)} aria-label="Go to page">
              {NAVIGATION_ITEMS.map((item) => <option key={item.id} value={item.id}>{item.label}</option>)}
            </select>
          </div>
        </header>
        <main className="mx-auto max-w-7xl px-4 py-6 md:px-8 md:py-10">
          <SourceSwitcher source={source} spotifyStatus={spotifyStatus} onChange={setSource} onConnectSpotify={connectSpotify} />
          {message ? (
            <GlowPanel as="div" variant="row" wrapperClassName="mb-5" className="flex flex-wrap items-center justify-between gap-3 px-4 py-3 text-sm text-mist">
              <span>{message}</span>
              {canRetryTakeout && lastTakeoutFileRef.current ? (
                <button type="button" className="btn-secondary" disabled={busy} onClick={retryTakeout}>Retry</button>
              ) : null}
            </GlowPanel>
          ) : null}
          {activePage}
        </main>
      </div>
    </div>
  );
}

function SourceSwitcher({
  source,
  spotifyStatus,
  onChange,
  onConnectSpotify,
}: {
  source: MusicSource;
  spotifyStatus: SpotifyStatus | null;
  onChange: (source: MusicSource) => void;
  onConnectSpotify: () => void;
}) {
  const label = source === "spotify" ? "Spotify" : "YouTube Music";
  return (
    <GlowPanel as="section" variant="card" wrapperClassName="relative z-10 mb-5" className="p-3">
      <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
        <div>
          <p className="text-xs uppercase tracking-[0.18em] text-mist/70">Music source</p>
          <p className="mt-1 text-sm font-semibold text-white">Currently analysing: {label}</p>
          {source === "spotify" ? (
            <p className="mt-1 max-w-3xl text-xs leading-5 text-mist">
              Spotify profile is based on top items, saved music, playlists and recent sync data. Full historical play counts are not available immediately.
            </p>
          ) : null}
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <button className={`rounded-md px-3 py-2 text-sm font-semibold ${source === "youtube" ? "bg-red-600 text-white" : "bg-white/10 text-mist hover:text-white"}`} onClick={() => onChange("youtube")}>
            YouTube Music
          </button>
          <button className={`rounded-md px-3 py-2 text-sm font-semibold ${source === "spotify" ? "bg-red-600 text-white" : "bg-white/10 text-mist hover:text-white"}`} onClick={() => onChange("spotify")}>
            Spotify
          </button>
          {source === "spotify" && !spotifyStatus?.connected ? (
            <button className="btn-secondary" onClick={onConnectSpotify}>Connect Spotify</button>
          ) : null}
        </div>
      </div>
    </GlowPanel>
  );
}
