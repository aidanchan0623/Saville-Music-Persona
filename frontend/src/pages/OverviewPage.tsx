import { Brain, RefreshCw, Sparkles } from "lucide-react";
import type { ReactNode } from "react";
import { EmptyState } from "../components/EmptyState";
import { MetricCard } from "../components/MetricCard";
import { StatusPill } from "../components/StatusPill";
import type { AuthStatus, Overview, Prerequisites } from "../types/api";
import { formatDate, formatDateTime } from "../utils/format";

interface Props {
  overview: Overview | null;
  auth: AuthStatus | null;
  prerequisites: Prerequisites | null;
  busy: boolean;
  useDemo: boolean;
  onRefresh: () => void;
  onGenerateReport: () => void;
  onOpenSettings: () => void;
}

export function OverviewPage({ overview, auth, prerequisites, busy, useDemo, onRefresh, onGenerateReport, onOpenSettings }: Props) {
  if (!overview) {
    return (
      <EmptyState
        title="No listening analysis loaded yet"
        body="Connect YouTube Music for private local analysis, or switch on demo data to explore the dashboard without account access."
        action={
          <div className="flex flex-wrap justify-center gap-3">
            <button className="btn-primary" onClick={onRefresh} disabled={busy}>
              <RefreshCw size={17} /> {busy ? "Refreshing..." : useDemo ? "Load Demo Data" : "Refresh My Music Data"}
            </button>
            <button className="btn-secondary" onClick={onOpenSettings}>Open Settings</button>
          </div>
        }
      />
    );
  }
  return (
    <div className="space-y-8">
      <section className="relative overflow-hidden rounded-lg border border-line bg-[radial-gradient(circle_at_20%_20%,rgba(139,92,246,0.24),transparent_35%),linear-gradient(135deg,rgba(17,17,29,0.96),rgba(7,7,13,0.98))] p-7 shadow-glow md:p-10">
        <div className="max-w-4xl">
          <div className="flex flex-wrap gap-2">
            <StatusPill ok={auth?.connected || useDemo} label={useDemo ? "Demo data active" : auth?.connected ? "YouTube Music connected" : "YouTube Music not connected"} />
            <StatusPill ok={Boolean(prerequisites?.ollama_reachable && prerequisites?.model_installed)} label={prerequisites?.model_installed ? "Gemma ready" : "Gemma unavailable"} />
          </div>
          <h1 className="mt-6 text-4xl font-black text-white md:text-6xl">Saville Music Persona</h1>
          <p className="mt-3 max-w-2xl text-lg leading-8 text-mist">A private local analysis of your YouTube Music identity.</p>
          <div className="mt-8 flex flex-wrap gap-3">
            <button className="btn-primary" onClick={onRefresh} disabled={busy}>
              <RefreshCw size={17} /> {busy ? "Refreshing..." : "Refresh My Music Data"}
            </button>
            <button className="btn-secondary" onClick={onGenerateReport} disabled={busy || !prerequisites?.model_installed}>
              <Sparkles size={17} /> Generate Persona Report
            </button>
          </div>
          <p className="mt-4 text-sm text-mist">Last refreshed: {formatDateTime(overview.last_refreshed_at)}</p>
        </div>
      </section>

      <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <MetricCard label="Your headline persona" value={overview.headline_persona} caption="A deterministic label from your strongest listening signals." accent="violet" />
        <MetricCard label="Top genre cluster" value={overview.top_genre_cluster} caption="Inferred only when metadata or playlist evidence exists." accent="indigo" />
        <MetricCard label="Favourite decade" value={overview.favourite_decade} caption="Weighted by detected plays with usable release years." accent="magenta" />
        <MetricCard label="Taste confidence" value={`${overview.taste_confidence.value}%`} caption={overview.taste_confidence.label} accent="violet" />
      </section>

      <section className="grid gap-5 lg:grid-cols-[1.1fr_0.9fr]">
        <div className="rounded-lg border border-line bg-panel/80 p-5">
          <h2 className="text-xl font-semibold text-white">Analysis coverage</h2>
          <dl className="mt-5 grid gap-3 sm:grid-cols-2">
            <CoverageItem label="Earliest detected play" value={formatDate(overview.coverage.earliest_detected_play)} />
            <CoverageItem label="Latest detected play" value={formatDate(overview.coverage.latest_detected_play)} />
            <CoverageItem label="Days represented" value={String(overview.coverage.days_represented)} />
            <CoverageItem label="Full 365-day analysis" value={overview.coverage.full_365_day_analysis ? "Yes" : "No"} />
          </dl>
          <div className="mt-4 space-y-2">
            {overview.coverage.notes.map((note) => (
              <p key={note} className="rounded-md border border-amber-200/10 bg-amber-200/10 p-3 text-sm text-amber-100">
                {note}
              </p>
            ))}
          </div>
        </div>
        <div className="rounded-lg border border-line bg-panel/80 p-5">
          <h2 className="text-xl font-semibold text-white">Core signals</h2>
          <div className="mt-5 grid gap-3">
            <Signal icon={<Brain size={18} />} label="Repeat score" value={`${overview.repeat_score.value}%`} detail={overview.repeat_score.label} />
            <Signal icon={<Sparkles size={18} />} label="Discovery score" value={`${overview.discovery_score.value}%`} detail={overview.discovery_score.label} />
            <Signal icon={<RefreshCw size={18} />} label="Detected plays" value={String(overview.total_detected_plays)} detail={`${overview.unique_tracks} tracks, ${overview.unique_artists} artists`} />
          </div>
        </div>
      </section>

      <section className="grid gap-5 lg:grid-cols-2">
        <MiniRank title="Top 3 artists" items={overview.top_3_artists.map((item) => `${item.artist} - ${item.play_count} plays`)} />
        <MiniRank title="Top 3 tracks" items={overview.top_3_tracks.map((item) => `${item.title} - ${item.artist}`)} />
      </section>
    </div>
  );
}

function CoverageItem({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-md bg-white/[0.04] p-4">
      <dt className="text-xs uppercase tracking-[0.16em] text-mist/60">{label}</dt>
      <dd className="mt-2 text-lg font-semibold text-white">{value}</dd>
    </div>
  );
}

function Signal({ icon, label, value, detail }: { icon: ReactNode; label: string; value: string; detail: string }) {
  return (
    <div className="flex items-center justify-between gap-3 rounded-md bg-white/[0.04] p-4">
      <div className="flex items-center gap-3 text-mist">
        <span className="grid h-9 w-9 place-items-center rounded-full bg-violet/15 text-violet-100">{icon}</span>
        <span>
          <span className="block text-sm text-white">{label}</span>
          <span className="text-xs">{detail}</span>
        </span>
      </div>
      <strong className="text-xl text-white">{value}</strong>
    </div>
  );
}

function MiniRank({ title, items }: { title: string; items: string[] }) {
  return (
    <div className="rounded-lg border border-line bg-panel/80 p-5">
      <h2 className="text-xl font-semibold text-white">{title}</h2>
      <ol className="mt-4 space-y-3">
        {items.map((item, index) => (
          <li key={item} className="flex items-center gap-3 rounded-md bg-white/[0.04] p-3 text-sm text-mist">
            <span className="text-lg font-black text-white/30">#{index + 1}</span>
            <span>{item}</span>
          </li>
        ))}
      </ol>
    </div>
  );
}
