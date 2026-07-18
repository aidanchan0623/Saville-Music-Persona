import { BarChart3, Disc3, Gauge, Home, Library, Menu, Music2, RefreshCw, Settings, Sparkles, X } from "lucide-react";
import type { ElementType } from "react";
import { useEffect, useMemo, useState } from "react";
import { api } from "./api/client";
import { LineSidebar, type LineSidebarItem } from "./components/LineSidebar";
import { LineWaves } from "./components/LineWaves";
import { StatusPill } from "./components/StatusPill";
import { SourceControl } from "./components/ui/SourceControl";
import { OverviewPage } from "./pages/OverviewPage";
import { PatternsPage } from "./pages/PatternsPage";
import { RecommendationsPage } from "./pages/RecommendationsPage";
import { ReportPage } from "./pages/ReportPage";
import { ScoresPage } from "./pages/ScoresPage";
import { SettingsPage } from "./pages/SettingsPage";
import { Top10Page } from "./pages/Top10Page";
import type { AuthStatus, Charts, ListeningMinutes, MusicSource, Overview, PersonaReport, Prerequisites, Recommendation, ScoreMetric, SpotifyStatus, TopArtist } from "./types/api";

type Page = "overview" | "top10" | "scores" | "patterns" | "report" | "recommendations" | "settings";

const nav: (LineSidebarItem<Page> & { icon: ElementType })[] = [
  { id: "overview", label: "Overview", kicker: "Identity read", icon: Home },
  { id: "top10", label: "Top 10", kicker: "Ranked plays", icon: Disc3 },
  { id: "scores", label: "Taste Scores", kicker: "Signal gauges", icon: Gauge },
  { id: "patterns", label: "Patterns", kicker: "Time and charts", icon: BarChart3 },
  { id: "report", label: "Persona Report", kicker: "Written profile", icon: Sparkles },
  { id: "recommendations", label: "Recommendations", kicker: "Curated picks", icon: Library },
  { id: "settings", label: "Settings", kicker: "Local setup", icon: Settings },
];

export default function App() {
  const [page, setPage] = useState<Page>("overview");
  const [mobileOpen, setMobileOpen] = useState(false);
  const [source, setSource] = useState<MusicSource>(() => {
    const querySource = new URLSearchParams(window.location.search).get("source");
    if (querySource === "spotify") return "spotify";
    return "youtube";
  });
  const [useDemo, setUseDemo] = useState(() => localStorage.getItem("smp_use_demo") === "true");
  const [overview, setOverview] = useState<Overview | null>(null);
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
    setArtists([]);
    setScores([]);
    setCharts(null);
    setThisMonthMinutes(null);
    setRollingYearMinutes(null);
    setReport(null);
    setRecommendations([]);
  };

  const loadAnalysis = async (activeSource: MusicSource = source) => {
    const nextOverview = await api.overview(activeSource);
    setOverview(nextOverview);
    const [nextArtists, nextScores, nextCharts, nextThisMonthMinutes, nextRollingYearMinutes] = await Promise.allSettled([
      api.topArtists(activeSource),
      api.scores("rolling_year", null, activeSource),
      api.charts("rolling_year", null, activeSource),
      api.listeningMinutes("this_month", null, activeSource),
      api.listeningMinutes("rolling_year", null, activeSource),
    ] as const);
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
    void loadStatus().catch((error) => setMessage(error instanceof Error ? error.message : "Could not read local status."));
  }, []);

  useEffect(() => {
    void loadAnalysis(source).catch((error) => {
      clearAnalysis();
      setMessage(error instanceof Error ? error.message : "No local analysis is available for this source yet.");
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
      setPage("report");
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
      setPage("overview");
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
            onOpenSettings={() => setPage("settings")}
            onOpenTop10={() => setPage("top10")}
            onOpenScores={() => setPage("scores")}
            onOpenPatterns={() => setPage("patterns")}
            onOpenReport={() => setPage("report")}
            source={source}
          />
        );
      case "top10":
        return <Top10Page source={source} />;
      case "scores":
        return <ScoresPage scores={scores} source={source} />;
      case "patterns":
        return <PatternsPage charts={charts} source={source} />;
      case "report":
        return <ReportPage report={report} prerequisites={prerequisites} busy={busy} topArtists={artists} onGenerate={generateReport} source={source} />;
      case "recommendations":
        return <RecommendationsPage recommendations={recommendations} busy={busy} onGenerate={generateRecommendations} onCreatePlaylist={createPlaylist} source={source} />;
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
          />
        );
    }
  }, [page, overview, thisMonthMinutes, rollingYearMinutes, auth, spotifyStatus, prerequisites, busy, useDemo, artists, scores, charts, report, recommendations, source]);

  const youtubeReady = Boolean(auth?.connected || auth?.cached_data_available || useDemo);
  const youtubeLabel = useDemo ? "Demo data" : auth?.connected ? "YouTube connected" : auth?.cached_data_available ? "YouTube cached" : "YouTube offline";
  const currentNav = nav.find((item) => item.id === page) ?? nav[0];
  const shellFooter = (
    <div className="space-y-3">
      <div className="space-y-2">
        <StatusPill ok={youtubeReady} label={youtubeLabel} />
        <StatusPill ok={spotifyStatus?.connected} label={spotifyStatus?.connected ? "Spotify connected" : spotifyStatus?.configured ? "Spotify ready" : "Spotify optional"} muted={!spotifyStatus?.configured && !spotifyStatus?.connected} />
        <StatusPill ok={Boolean(prerequisites?.model_installed && prerequisites.ollama_reachable)} label={prerequisites?.model_installed && prerequisites.ollama_reachable ? "Gemma ready" : "Gemma offline"} />
      </div>
      <button type="button" className="btn-secondary w-full" onClick={refresh} disabled={busy}>
        <RefreshCw size={16} className={busy ? "animate-spin" : ""} /> Refresh data
      </button>
    </div>
  );

  return (
    <div className="relative min-h-screen overflow-x-hidden bg-ink text-white">
      <LineWaves className="fixed opacity-70" amplitude={26} speed={0.00014} waveCount={8} />
      <div className="fixed inset-0 -z-10 bg-[linear-gradient(115deg,rgba(5,3,3,0.98),rgba(13,6,6,0.96)_52%,rgba(4,3,3,0.99))]" />
      <div className="fixed inset-x-0 top-0 z-30 border-b border-white/10 bg-[#050303]/88 px-4 py-3 backdrop-blur-2xl lg:hidden">
        <div className="flex items-center justify-between gap-3">
          <button type="button" className="grid h-10 w-10 place-items-center rounded-md border border-white/10 bg-white/[0.06] text-white" aria-label="Open navigation" onClick={() => setMobileOpen(true)}>
            <Menu size={19} />
          </button>
          <div className="min-w-0 text-center">
            <p className="font-display text-lg uppercase leading-none tracking-[0.06em]">Saville</p>
            <p className="mt-1 truncate text-xs uppercase tracking-[0.18em] text-mist/70">{currentNav.label}</p>
          </div>
          <span className="grid h-10 w-10 place-items-center rounded-md border border-red-400/25 bg-red-600/20 text-red-100">
            <Music2 size={18} />
          </span>
        </div>
      </div>

      <LineSidebar items={nav} active={page} onNavigate={setPage} footer={shellFooter} className="fixed inset-y-0 left-0 z-30 hidden w-[19rem] lg:block" />

      {mobileOpen ? (
        <div className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm lg:hidden">
          <LineSidebar
            items={nav}
            active={page}
            onNavigate={(next) => {
              setPage(next);
              setMobileOpen(false);
            }}
            footer={shellFooter}
            className="h-full w-[min(22rem,calc(100vw-2rem))]"
          />
          <button type="button" className="absolute right-4 top-4 grid h-10 w-10 place-items-center rounded-md border border-white/10 bg-white/[0.08] text-white" aria-label="Close navigation" onClick={() => setMobileOpen(false)}>
            <X size={20} />
          </button>
        </div>
      ) : null}

      <div className="relative z-10 pt-[4.6rem] lg:pl-[19rem] lg:pt-0">
        <main className="mx-auto max-w-[94rem] px-4 pb-12 md:px-7 lg:px-10">
          <SourceControl source={source} spotifyStatus={spotifyStatus} onChange={setSource} onConnectSpotify={connectSpotify} />
          {message ? (
            <div className="mb-6 rounded-lg border border-white/10 bg-white/[0.055] px-4 py-3 text-sm leading-6 text-mist shadow-[0_18px_70px_rgba(0,0,0,0.4)]">
              {message}
            </div>
          ) : null}
          {activePage}
        </main>
      </div>
    </div>
  );
}
