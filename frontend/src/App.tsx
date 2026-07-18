import { Menu, Music2, X } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { api } from "./api/client";
import { DesktopSidebar } from "./components/navigation/DesktopSidebar";
import { NAVIGATION_ITEMS } from "./components/navigation/navigation";
import type { Page } from "./components/navigation/navigation";
import { OverviewPage } from "./pages/OverviewPage";
import { PatternsPage } from "./pages/PatternsPage";
import { RecommendationsPage } from "./pages/RecommendationsPage";
import { ReportPage } from "./pages/ReportPage";
import { ScoresPage } from "./pages/ScoresPage";
import { SettingsPage } from "./pages/SettingsPage";
import { Top10Page } from "./pages/Top10Page";
import type { AuthStatus, Charts, ListeningMinutes, MusicSource, Overview, PersonaReport, Prerequisites, Recommendation, ScoreMetric, SpotifyStatus, TopArtist, TopTrack } from "./types/api";

function getHistoryPage(): Page {
  if (typeof window === "undefined") return "overview";
  const value = window.history.state?.page;
  return NAVIGATION_ITEMS.some((item) => item.id === value) ? value : "overview";
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
  const [overview, setOverview] = useState<Overview | null>(null);
  const [tracks, setTracks] = useState<TopTrack[]>([]);
  const [artists, setArtists] = useState<TopArtist[]>([]);
  const [scores, setScores] = useState<ScoreMetric[]>([]);
  const [charts, setCharts] = useState<Charts | null>(null);
  const [thisMonthMinutes, setThisMonthMinutes] = useState<ListeningMinutes | null>(null);
  const [rollingYearMinutes, setRollingYearMinutes] = useState<ListeningMinutes | null>(null);
  const [report, setReport] = useState<PersonaReport | null>(null);
  const [recommendations, setRecommendations] = useState<Recommendation[]>([]);
  const [auth, setAuth] = useState<AuthStatus | null>(null);
  const [spotifyStatus, setSpotifyStatus] = useState<SpotifyStatus | null>(null);
  const [prerequisites, setPrerequisites] = useState<Prerequisites | null>(null);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  const loadStatus = async () => {
    const [nextPrerequisites, nextAuth, nextSpotifyStatus] = await Promise.all([api.prerequisites(), api.authStatus(), api.spotifyStatus()]);
    setPrerequisites(nextPrerequisites);
    setAuth(nextAuth);
    setSpotifyStatus(nextSpotifyStatus);
  };

  const clearAnalysis = () => {
    setOverview(null);
    setTracks([]);
    setArtists([]);
    setScores([]);
    setCharts(null);
    setThisMonthMinutes(null);
    setRollingYearMinutes(null);
    setReport(null);
    setRecommendations([]);
  };

  const navigate = (next: Page) => {
    if (next !== page) {
      window.history.pushState({ ...(window.history.state ?? {}), page: next }, "", window.location.href);
      setTitleVisitId((value) => value + 1);
    }
    setPage(next);
    setMobileOpen(false);
  };

  const loadAnalysis = async (activeSource: MusicSource = source) => {
    const nextOverview = await api.overview(activeSource);
    setOverview(nextOverview);
    const [nextTracks, nextArtists, nextScores, nextCharts, nextThisMonthMinutes, nextRollingYearMinutes] = await Promise.allSettled([
      api.topTracks(activeSource),
      api.topArtists(activeSource),
      api.scores("rolling_year", null, activeSource),
      api.charts("rolling_year", null, activeSource),
      api.listeningMinutes("this_month", null, activeSource),
      api.listeningMinutes("rolling_year", null, activeSource),
    ] as const);
    if (nextTracks.status === "fulfilled") setTracks(nextTracks.value);
    if (nextArtists.status === "fulfilled") setArtists(nextArtists.value);
    if (nextScores.status === "fulfilled") setScores(nextScores.value);
    if (nextCharts.status === "fulfilled") setCharts(nextCharts.value);
    if (nextThisMonthMinutes.status === "fulfilled") setThisMonthMinutes(nextThisMonthMinutes.value);
    if (nextRollingYearMinutes.status === "fulfilled") setRollingYearMinutes(nextRollingYearMinutes.value);
    try {
      setReport(await api.latestReport(activeSource));
    } catch {
      setReport(null);
    }
    if (activeSource === "youtube") {
      try {
        setRecommendations(await api.recommendations());
      } catch {
        setRecommendations([]);
      }
    } else {
      setRecommendations([]);
    }
  };

  useEffect(() => {
    localStorage.setItem("smp_use_demo", String(useDemo));
  }, [useDemo]);

  useEffect(() => {
    void loadStatus().catch((error) => setMessage(error.message));
  }, []);

  useEffect(() => {
    window.history.replaceState({ ...(window.history.state ?? {}), page }, "", window.location.href);
    const handlePopState = () => {
      setPage(getHistoryPage());
      setTitleVisitId((value) => value + 1);
      setMobileOpen(false);
    };
    window.addEventListener("popstate", handlePopState);
    return () => window.removeEventListener("popstate", handlePopState);
  }, []);

  useEffect(() => {
    void loadAnalysis(source).catch((error) => {
      clearAnalysis();
      if (source === "spotify") {
        setMessage(error instanceof Error ? error.message : "Connect Spotify in Settings, then refresh Spotify data.");
      }
    });
  }, [source]);

  const refresh = async () => {
    setBusy(true);
    setMessage(source === "spotify" ? "Refreshing local Spotify data..." : useDemo ? "Loading anonymised demo listening history..." : "Refreshing local YouTube Music data...");
    try {
      const response = source === "spotify" ? await api.spotifyRefresh() : await api.refresh(useDemo);
      await loadStatus();
      await loadAnalysis(source);
      setMessage(`Refreshed ${response.track_count} tracks and ${response.play_count} detected plays.`);
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Refresh failed.");
    } finally {
      setBusy(false);
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
    setBusy(true);
    setMessage(`Importing ${file.name} from Google Takeout...`);
    try {
      const result = await api.importTakeout(file);
      setSource("youtube");
      await loadAnalysis("youtube");
      setMessage(`${result.message} Imported ${result.imported_count} history entries.`);
      navigate("overview");
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Takeout import failed.");
    } finally {
      setBusy(false);
    }
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
            thisMonthMinutes={thisMonthMinutes}
            rollingYearMinutes={rollingYearMinutes}
            scores={scores}
            auth={auth}
            prerequisites={prerequisites}
            busy={busy}
            useDemo={useDemo}
            onRefresh={refresh}
            onOpenSettings={() => navigate("settings")}
            onOpenTop10={() => navigate("top10")}
            onOpenScores={() => navigate("scores")}
            onOpenPatterns={() => navigate("patterns")}
            onOpenReport={() => navigate("report")}
            source={source}
            titleAnimationKey={titleAnimationKey}
          />
        );
      case "top10":
        return <Top10Page source={source} titleAnimationKey={titleAnimationKey} />;
      case "scores":
        return <ScoresPage scores={scores} source={source} titleAnimationKey={titleAnimationKey} />;
      case "patterns":
        return <PatternsPage charts={charts} source={source} titleAnimationKey={titleAnimationKey} />;
      case "report":
        return <ReportPage report={report} prerequisites={prerequisites} busy={busy} topArtists={artists} onGenerate={generateReport} source={source} titleAnimationKey={titleAnimationKey} />;
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
  }, [page, titleVisitId, overview, thisMonthMinutes, rollingYearMinutes, auth, spotifyStatus, prerequisites, busy, useDemo, tracks, artists, scores, charts, report, recommendations, source]);

  const youtubeReady = Boolean(auth?.connected || auth?.cached_data_available || useDemo);
  const youtubeLabel = useDemo ? "Demo data" : auth?.connected ? "YouTube connected" : auth?.cached_data_available ? "YouTube data loaded" : "YouTube offline";
  const currentNav = NAVIGATION_ITEMS.find((item) => item.id === page) ?? NAVIGATION_ITEMS[0];

  return (
    <div className="min-h-screen bg-ink text-white">
      <div className="fixed inset-0 -z-10 bg-[radial-gradient(circle_at_70%_10%,rgba(239,43,45,0.16),transparent_28%),radial-gradient(circle_at_20%_80%,rgba(123,17,24,0.15),transparent_25%)]" />
      <DesktopSidebar activePage={page} youtubeReady={youtubeReady} youtubeLabel={youtubeLabel} spotifyConnected={spotifyStatus?.connected} modelInstalled={prerequisites?.model_installed} onNavigate={navigate} />

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
            <div className="mb-5 rounded-lg border border-white/10 bg-white/[0.04] px-4 py-3 text-sm text-mist">
              {message}
            </div>
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
    <section className="mb-5 rounded-lg border border-line bg-panel/72 p-3">
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
    </section>
  );
}
