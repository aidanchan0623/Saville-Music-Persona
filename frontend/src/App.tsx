import { BarChart3, Disc3, Gauge, Home, Library, Music2, Settings, Sparkles } from "lucide-react";
import type { ElementType } from "react";
import { useEffect, useMemo, useState } from "react";
import { api } from "./api/client";
import { StatusPill } from "./components/StatusPill";
import { OverviewPage } from "./pages/OverviewPage";
import { PatternsPage } from "./pages/PatternsPage";
import { RecommendationsPage } from "./pages/RecommendationsPage";
import { ReportPage } from "./pages/ReportPage";
import { ScoresPage } from "./pages/ScoresPage";
import { SettingsPage } from "./pages/SettingsPage";
import { Top10Page } from "./pages/Top10Page";
import type { AuthStatus, Charts, ListeningMinutes, Overview, PersonaReport, Prerequisites, Recommendation, ScoreMetric, TopArtist, TopTrack } from "./types/api";

type Page = "overview" | "top10" | "scores" | "patterns" | "report" | "recommendations" | "settings";

const nav: { id: Page; label: string; icon: ElementType }[] = [
  { id: "overview", label: "Overview", icon: Home },
  { id: "top10", label: "Top 10", icon: Disc3 },
  { id: "scores", label: "Scores", icon: Gauge },
  { id: "patterns", label: "Patterns", icon: BarChart3 },
  { id: "report", label: "Persona Report", icon: Sparkles },
  { id: "recommendations", label: "Recommendations", icon: Library },
  { id: "settings", label: "Settings", icon: Settings },
];

export default function App() {
  const [page, setPage] = useState<Page>("overview");
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
  const [prerequisites, setPrerequisites] = useState<Prerequisites | null>(null);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  const loadStatus = async () => {
    const [nextPrerequisites, nextAuth] = await Promise.all([api.prerequisites(), api.authStatus()]);
    setPrerequisites(nextPrerequisites);
    setAuth(nextAuth);
  };

  const loadAnalysis = async () => {
    const nextOverview = await api.overview();
    setOverview(nextOverview);
    const [nextTracks, nextArtists, nextScores, nextCharts, nextThisMonthMinutes, nextRollingYearMinutes] = await Promise.allSettled([
      api.topTracks(),
      api.topArtists(),
      api.scores(),
      api.charts(),
      api.listeningMinutes("this_month"),
      api.listeningMinutes("rolling_year"),
    ] as const);
    if (nextTracks.status === "fulfilled") setTracks(nextTracks.value);
    if (nextArtists.status === "fulfilled") setArtists(nextArtists.value);
    if (nextScores.status === "fulfilled") setScores(nextScores.value);
    if (nextCharts.status === "fulfilled") setCharts(nextCharts.value);
    if (nextThisMonthMinutes.status === "fulfilled") setThisMonthMinutes(nextThisMonthMinutes.value);
    if (nextRollingYearMinutes.status === "fulfilled") setRollingYearMinutes(nextRollingYearMinutes.value);
    try {
      setReport(await api.latestReport());
    } catch {
      setReport(null);
    }
    try {
      setRecommendations(await api.recommendations());
    } catch {
      setRecommendations([]);
    }
  };

  useEffect(() => {
    localStorage.setItem("smp_use_demo", String(useDemo));
  }, [useDemo]);

  useEffect(() => {
    void loadStatus().catch((error) => setMessage(error.message));
    void loadAnalysis().catch(() => undefined);
  }, []);

  const refresh = async () => {
    setBusy(true);
    setMessage(useDemo ? "Loading anonymised demo listening history..." : "Refreshing local YouTube Music data...");
    try {
      const response = await api.refresh(useDemo);
      await loadStatus();
      await loadAnalysis();
      setMessage(`Refreshed ${response.track_count} tracks and ${response.play_count} detected plays.`);
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Refresh failed.");
    } finally {
      setBusy(false);
    }
  };

  const generateReport = async (mode: "serious" | "playful" | "roast" = "serious") => {
    setBusy(true);
    setMessage("Asking local Gemma to write from the factual profile...");
    try {
      const nextReport = await api.generateReport(mode);
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
      await loadAnalysis();
      setMessage(`${result.message} Imported ${result.imported_count} history entries.`);
      setPage("overview");
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Takeout import failed.");
    } finally {
      setBusy(false);
    }
  };

  const createPlaylist = async () => {
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
          />
        );
      case "top10":
        return <Top10Page />;
      case "scores":
        return <ScoresPage scores={scores} />;
      case "patterns":
        return <PatternsPage charts={charts} />;
      case "report":
        return <ReportPage report={report} prerequisites={prerequisites} busy={busy} onGenerate={generateReport} />;
      case "recommendations":
        return <RecommendationsPage recommendations={recommendations} busy={busy} onGenerate={generateRecommendations} onCreatePlaylist={createPlaylist} />;
      case "settings":
        return (
          <SettingsPage
            auth={auth}
            prerequisites={prerequisites}
            useDemo={useDemo}
            busy={busy}
            onUseDemoChange={setUseDemo}
            onCheckAuth={() => void loadStatus().catch((error) => setMessage(error.message))}
            onImportTakeout={importTakeout}
          />
        );
    }
  }, [page, overview, thisMonthMinutes, rollingYearMinutes, auth, prerequisites, busy, useDemo, tracks, artists, scores, charts, report, recommendations]);

  return (
    <div className="min-h-screen bg-ink text-white">
      <div className="fixed inset-0 -z-10 bg-[radial-gradient(circle_at_70%_10%,rgba(99,102,241,0.18),transparent_28%),radial-gradient(circle_at_20%_80%,rgba(217,70,239,0.12),transparent_25%)]" />
      <aside className="fixed inset-y-0 left-0 hidden w-72 border-r border-line bg-ink/85 p-5 backdrop-blur-xl lg:block">
        <div className="flex items-center gap-3">
          <div className="grid h-11 w-11 place-items-center rounded-lg bg-gradient-to-br from-violet to-magenta">
            <Music2 size={22} />
          </div>
          <div>
            <p className="font-bold">Saville Music</p>
            <p className="text-xs text-mist">Persona dashboard</p>
          </div>
        </div>
        <nav className="mt-8 space-y-2">
          {nav.map((item) => {
            const Icon = item.icon;
            return (
              <button key={item.id} className={`nav-item ${page === item.id ? "nav-item-active" : ""}`} onClick={() => setPage(item.id)}>
                <Icon size={18} />
                {item.label}
              </button>
            );
          })}
        </nav>
        <div className="absolute bottom-5 left-5 right-5 space-y-2">
          <StatusPill ok={auth?.connected || useDemo} label={useDemo ? "Demo data" : auth?.connected ? "Connected" : "Not connected"} />
          <StatusPill ok={Boolean(prerequisites?.model_installed)} label={prerequisites?.model_installed ? "Gemma ready" : "Gemma offline"} />
        </div>
      </aside>

      <div className="lg:pl-72">
        <header className="sticky top-0 z-20 border-b border-line bg-ink/78 px-4 py-3 backdrop-blur-xl lg:hidden">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2 font-bold">
              <Music2 size={20} /> Saville
            </div>
            <select className="rounded-md border border-line bg-panel px-3 py-2 text-sm" value={page} onChange={(event) => setPage(event.target.value as Page)}>
              {nav.map((item) => <option key={item.id} value={item.id}>{item.label}</option>)}
            </select>
          </div>
        </header>
        <main className="mx-auto max-w-7xl px-4 py-6 md:px-8 md:py-10">
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
