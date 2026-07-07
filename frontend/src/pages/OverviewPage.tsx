import { Brain, RefreshCw, Sparkles } from "lucide-react";
import type { ReactNode } from "react";
import { EmptyState } from "../components/EmptyState";
import { MetricCard } from "../components/MetricCard";
import { StatusPill } from "../components/StatusPill";
import { TasteDNA } from "../components/TasteDNA";
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
  const taste = overview.taste_interpretation;
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
        <MetricCard label="Top taste family" value={overview.top_genre_cluster} caption="Built from curated artist genre mapping, not weak raw metadata." accent="indigo" />
        <MetricCard label="Favourite decade" value={overview.favourite_decade} caption="Weighted by detected plays with usable release years." accent="magenta" />
        <MetricCard label="Taste confidence" value={`${overview.taste_confidence.value}%`} caption={overview.taste_confidence.label} accent="violet" />
      </section>

      {taste ? (
        <section className="rounded-lg border border-line bg-panel/82 p-6 shadow-glow">
          <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
            <div className="max-w-3xl">
              <p className="text-sm uppercase tracking-[0.18em] text-violet-200">What Your Taste Sounds Like</p>
              <h2 className="mt-2 text-3xl font-black text-white">Emotion, atmosphere, and guitar-driven pressure</h2>
              <p className="mt-4 text-lg leading-8 text-mist">{taste.summary}</p>
            </div>
            <div className="grid min-w-[16rem] gap-2 text-sm">
              <Confidence label="Genre coverage" value={overview.genre_coverage_percent} />
              <Confidence label="Curated artist coverage" value={overview.curated_artist_coverage_percent} />
              <Confidence label="Unknown artist coverage" value={overview.unknown_artist_coverage_percent} inverse />
            </div>
          </div>
          <div className="mt-6 grid gap-4 lg:grid-cols-3">
            <TasteLayer title="Core taste" items={taste.core_genre_families.map((item) => `${item.name} - ${item.share}%`)} />
            <TasteLayer title="Secondary taste" items={taste.secondary_genre_families.map((item) => `${item.name} - ${item.share}%`)} />
            <TasteLayer title="Side quests" items={taste.side_quests.map((item) => `${item.name} - ${item.share}%`)} />
          </div>
          <div className="mt-5 flex flex-wrap gap-2">
            {taste.sonic_traits.slice(0, 8).map((trait) => (
              <span key={trait} className="rounded-full border border-violet/20 bg-violet/10 px-3 py-1 text-sm text-violet-100">
                {trait}
              </span>
            ))}
          </div>
          {taste.coverage.unknown_artist_coverage_percent > 20 ? (
            <p className="mt-4 rounded-md border border-amber-200/10 bg-amber-200/10 p-3 text-sm text-amber-100">
              Your core genre pattern is clear from your dominant artists, but smaller artists could not be confidently classified.
            </p>
          ) : null}
        </section>
      ) : null}

      <TasteDNA dna={overview.taste_dna} interpretation={taste} />

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

function Confidence({ label, value, inverse = false }: { label: string; value: number; inverse?: boolean }) {
  const good = inverse ? 100 - value : value;
  return (
    <div className="rounded-md bg-white/[0.04] p-3">
      <div className="flex items-center justify-between gap-3 text-xs text-mist">
        <span>{label}</span>
        <strong className="text-white">{value}%</strong>
      </div>
      <div className="mt-2 h-1.5 rounded-full bg-white/10">
        <div className="h-full rounded-full bg-violet" style={{ width: `${Math.max(0, Math.min(100, good))}%` }} />
      </div>
    </div>
  );
}

function TasteLayer({ title, items }: { title: string; items: string[] }) {
  return (
    <div className="rounded-md bg-white/[0.04] p-4">
      <h3 className="font-semibold text-white">{title}</h3>
      <div className="mt-3 space-y-2">
        {items.length ? items.map((item) => <p key={item} className="text-sm text-mist">{item}</p>) : <p className="text-sm text-mist/70">No confident signal yet</p>}
      </div>
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
