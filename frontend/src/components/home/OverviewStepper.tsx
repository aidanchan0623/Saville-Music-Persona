import { ArrowDown, ArrowUp, BarChart3, Compass, Disc3, Gauge, RotateCcw, Sparkles } from "lucide-react";
import type { ReactNode } from "react";
import { Artwork } from "../Artwork";
import { GlowPanel } from "../GlowPanel";
import Stepper, { Step } from "../reactbits/Stepper/Stepper";
import type { ListeningMinutes, Overview, PeriodTopItem, PeriodTopResponse, ScoreMetric, TasteDnaComparison, TasteDnaExplorer } from "../../types/api";
import { asPercent, formatMinutes } from "../../utils/format";
import "./OverviewStepper.css";

type OverviewStepperProps = {
  overview: Overview;
  thisMonthMinutes: ListeningMinutes | null;
  rollingYearMinutes: ListeningMinutes | null;
  scores: ScoreMetric[];
  currentTaste: TasteDnaExplorer | null;
  comparison: TasteDnaComparison | null;
  currentTopArtists: PeriodTopResponse | null;
  currentTopTracks: PeriodTopResponse | null;
  onOpenTop10: () => void;
  onOpenScores: () => void;
  onOpenPatterns: () => void;
  onOpenReport: () => void;
};

const STEP_LABELS = ["Current State", "Core Sound", "Behaviour", "Movement", "Summary"];

export function OverviewStepper({
  overview,
  thisMonthMinutes,
  rollingYearMinutes,
  scores,
  currentTaste,
  comparison,
  currentTopArtists,
  currentTopTracks,
  onOpenTop10,
  onOpenScores,
  onOpenPatterns,
  onOpenReport,
}: OverviewStepperProps) {
  const scoreByKey = new Map(scores.map((score) => [score.key, score]));
  const topArtist = currentTopArtists?.items[0] ?? null;

  return (
    <Stepper
      className="overview-stepper"
      stepLabels={STEP_LABELS}
      backButtonText="Previous"
      nextButtonText="Next"
      completeButtonText="Return to start"
      completeAction="restart"
    >
      <Step>
        <ListeningStateSection
          overview={overview}
          thisMonthMinutes={thisMonthMinutes}
          currentTaste={currentTaste}
          comparison={comparison}
          topArtist={topArtist}
          repeatScore={overview.repeat_score}
          discoveryScore={overview.discovery_score}
          onOpenReport={onOpenReport}
        />
      </Step>
      <Step>
        <CoreSoundSection overview={overview} currentTaste={currentTaste} />
      </Step>
      <Step>
        <ListeningBehaviourSection
          overview={overview}
          thisMonthMinutes={thisMonthMinutes}
          rollingYearMinutes={rollingYearMinutes}
          artistLoyaltyScore={scoreByKey.get("artist_loyalty")}
          nicheScore={scoreByKey.get("mainstream_niche")}
        />
      </Step>
      <Step>
        <RecentMovementSection currentTopArtists={currentTopArtists} currentTopTracks={currentTopTracks} comparison={comparison} onOpenTop10={onOpenTop10} />
      </Step>
      <Step>
        <PersonalSummarySection
          overview={overview}
          currentTopArtists={currentTopArtists}
          onOpenReport={onOpenReport}
          onOpenScores={onOpenScores}
          onOpenPatterns={onOpenPatterns}
        />
      </Step>
    </Stepper>
  );
}

function ListeningStateSection({
  overview,
  thisMonthMinutes,
  currentTaste,
  comparison,
  topArtist,
  repeatScore,
  discoveryScore,
  onOpenReport,
}: {
  overview: Overview;
  thisMonthMinutes: ListeningMinutes | null;
  currentTaste: TasteDnaExplorer | null;
  comparison: TasteDnaComparison | null;
  topArtist: PeriodTopItem | null;
  repeatScore: ScoreMetric;
  discoveryScore: ScoreMetric;
  onOpenReport: () => void;
}) {
  const dominantCluster = currentTaste?.nodes[0]?.name ?? overview.top_genre_cluster;
  const comfortLabel = repeatScore.value >= discoveryScore.value ? "comfort-leaning" : "discovery-leaning";
  const shift = comparison?.claims.growing_cluster ?? comparison?.claims.declining_cluster ?? null;
  const headline = repeatScore.value >= discoveryScore.value ? "This phase is built around repeat gravity." : "This phase is more exploratory than usual.";
  const support = shift
    ? `${shift.name} is ${shift.delta > 0 ? "stronger" : "lower"} than your rolling-year baseline.`
    : "Your current listening still sits close to the long-term sound profile.";

  return (
    <OverviewSection
      eyebrow="Current Listening State"
      title={headline}
      intro={`${dominantCluster || "Your mapped sound"} is leading the current window. ${support}`}
      aside={
        <GlowPanel as="div" variant="row" className="overview-stepper__artist-focus">
          <Artwork src={topArtist?.thumbnail} alt={topArtist?.artist ?? "Current anchor artist"} kind="artist" size="hero" priority fallbackLabel={initials(topArtist?.artist ?? "Artist")} shape="rounded" />
          <div className="min-w-0">
            <p className="text-xs font-semibold uppercase tracking-[0.16em] text-red-200">Current anchor</p>
            <h3 className="mt-2 text-2xl font-black leading-tight text-white">{topArtist?.artist ?? "No clear anchor yet"}</h3>
            <p className="mt-2 text-sm leading-6 text-mist">
              {topArtist ? `${topArtist.play_count.toLocaleString()} detected plays, ${topArtist.unique_songs ?? 0} songs, ${topArtist.share_of_period}% of the period.` : "Refresh more current data to establish a clear artist signal."}
            </p>
          </div>
        </GlowPanel>
      }
    >
      <div className="overview-stepper__metric-grid">
        <DataCard label="This month" value={thisMonthMinutes ? formatMinutes(thisMonthMinutes.metrics.current_month_total_minutes) : "Unavailable"} detail="Detected listening time from tracks with usable durations." />
        <DataCard label="Dominant sound" value={dominantCluster || "Still mapping"} detail={currentTaste?.nodes[0] ? `${currentTaste.nodes[0].share}% of classified current listening.` : "Based on the strongest mapped genre family."} />
        <DataCard label="Comfort vs discovery" value={comfortLabel} detail={`${Math.round(repeatScore.value)} repeat score / ${Math.round(discoveryScore.value)} discovery score.`} />
      </div>
      <div className="overview-stepper__actions">
        <button className="btn-primary" type="button" onClick={onOpenReport}>Open Persona Report</button>
      </div>
    </OverviewSection>
  );
}

function CoreSoundSection({ overview, currentTaste }: { overview: Overview; currentTaste: TasteDnaExplorer | null }) {
  const taste = overview.taste_interpretation;
  const coreGenres = taste.core_genre_families.slice(0, 4);
  const secondary = (taste.secondary_genre_families.length ? taste.secondary_genre_families : taste.side_quests).slice(0, 2);
  const traits = (currentTaste?.traits.map((trait) => trait.trait) ?? taste.sonic_traits).slice(0, 7);

  return (
    <OverviewSection
      eyebrow="Core Sound"
      title="The centre is emotional alternative, with atmosphere around the edges."
      intro={shorten(overview.taste_interpretation.summary, 240)}
    >
      <div className="overview-stepper__sound-grid">
        <SoundGroup title="Main genres" items={coreGenres.map((item) => ({ label: item.name, value: `${item.share}%` }))} />
        <SoundGroup title="Secondary influences" items={secondary.map((item) => ({ label: item.name, value: `${item.share}%` }))} />
      </div>
      <GlowPanel as="div" variant="row" className="overview-stepper__trait-panel">
        <p className="text-sm font-semibold uppercase tracking-[0.16em] text-mist/70">Strongest sonic traits</p>
        <div className="mt-4 flex flex-wrap gap-2">
          {traits.map((trait) => <span key={trait} className="overview-stepper__chip">{trait}</span>)}
        </div>
      </GlowPanel>
      {taste.coverage.unknown_artist_coverage_percent > 30 ? (
        <GlowPanel as="p" variant="row" className="mt-4 p-4 text-sm leading-6 text-amber-100">
          Genre claims are strongest for mapped artists; {Math.round(taste.coverage.unknown_artist_coverage_percent)}% of artist coverage is still unknown.
        </GlowPanel>
      ) : null}
    </OverviewSection>
  );
}

function ListeningBehaviourSection({
  overview,
  thisMonthMinutes,
  rollingYearMinutes,
  artistLoyaltyScore,
  nicheScore,
}: {
  overview: Overview;
  thisMonthMinutes: ListeningMinutes | null;
  rollingYearMinutes: ListeningMinutes | null;
  artistLoyaltyScore?: ScoreMetric;
  nicheScore?: ScoreMetric;
}) {
  const dna = overview.taste_dna;
  const activeDays = thisMonthMinutes?.metrics.active_listening_days ?? rollingYearMinutes?.metrics.active_listening_days;
  const streak = thisMonthMinutes?.metrics.current_listening_streak_days ?? rollingYearMinutes?.metrics.current_listening_streak_days;
  const durationCoverage = thisMonthMinutes?.duration_quality.duration_coverage_percent ?? rollingYearMinutes?.duration_quality.duration_coverage_percent;

  return (
    <OverviewSection
      eyebrow="Listening Behaviour"
      title="Known favourites carry the profile, but the sound world is not narrow."
      intro="These are calculated behaviour signals from repeat plays, artist concentration, discovery share, and duration-aware listening time."
    >
      <div className="overview-stepper__metric-grid overview-stepper__metric-grid--wide">
        <SignalCard icon={<RotateCcw size={18} />} label="Repeat listening" value={asPercent(overview.repeat_score.value)} detail={overview.repeat_score.label} />
        <SignalCard icon={<Compass size={18} />} label="Discovery" value={asPercent(overview.discovery_score.value)} detail={overview.discovery_score.label} />
        <SignalCard icon={<Gauge size={18} />} label="Artist concentration" value={asPercent(dna.artist_concentration.value)} detail={dna.artist_concentration.label} />
        <SignalCard icon={<Disc3 size={18} />} label="Comfort tendency" value={asPercent(dna.exploration_vs_comfort.value)} detail={dna.exploration_vs_comfort.label} />
      </div>
      <div className="overview-stepper__support-row">
        {artistLoyaltyScore ? <DataCard label="Artist loyalty" value={asPercent(artistLoyaltyScore.value)} detail={artistLoyaltyScore.interpretation?.plain_english ?? artistLoyaltyScore.label} /> : null}
        {nicheScore ? <DataCard label="Niche estimate" value={asPercent(nicheScore.value)} detail={nicheScore.interpretation?.plain_english ?? nicheScore.label} /> : null}
        {activeDays !== undefined ? <DataCard label="Active days" value={activeDays.toLocaleString()} detail={streak ? `${streak} day current listening streak.` : "Days with detected music activity."} /> : null}
        {durationCoverage !== undefined ? <DataCard label="Minute confidence" value={asPercent(durationCoverage)} detail="Share of detected plays with usable duration data." /> : null}
      </div>
    </OverviewSection>
  );
}

function RecentMovementSection({
  currentTopArtists,
  currentTopTracks,
  comparison,
  onOpenTop10,
}: {
  currentTopArtists: PeriodTopResponse | null;
  currentTopTracks: PeriodTopResponse | null;
  comparison: TasteDnaComparison | null;
  onOpenTop10: () => void;
}) {
  const movers = [...movementItems(currentTopTracks?.items ?? [], "song"), ...movementItems(currentTopArtists?.items ?? [], "artist")].slice(0, 6);

  return (
    <OverviewSection
      eyebrow="Recent Movement"
      title="The current month has a few clear jumps, not a full identity reset."
      intro={comparison?.summary_sentence ?? "Movement is based on this period versus the previous comparable period where there is enough listening data."}
    >
      <div className="overview-stepper__movement-list">
        {movers.length ? movers.map((item) => <MovementRow key={item.key} item={item} />) : <GlowPanel as="p" variant="row" className="p-4 text-sm text-mist">No meaningful movement signal is available for this period yet.</GlowPanel>}
      </div>
      <div className="overview-stepper__actions">
        <button className="btn-secondary" type="button" onClick={onOpenTop10}>Open Top 10</button>
      </div>
    </OverviewSection>
  );
}

function PersonalSummarySection({
  overview,
  currentTopArtists,
  onOpenReport,
  onOpenScores,
  onOpenPatterns,
}: {
  overview: Overview;
  currentTopArtists: PeriodTopResponse | null;
  onOpenReport: () => void;
  onOpenScores: () => void;
  onOpenPatterns: () => void;
}) {
  const topCurrentArtist = currentTopArtists?.items[0]?.artist ?? overview.top_3_artists[0]?.artist;
  const distinctive = overview.taste_interpretation.listening_character.slice(0, 3).join(", ") || overview.taste_dna.core_dna[0] || "a stable mapped taste profile";
  const genresDiscovered = overview.taste_interpretation.canonical_genre_shares.length;

  return (
    <OverviewSection
      eyebrow="Personal Summary"
      title={overview.headline_persona}
      intro={`The most distinctive pattern is ${distinctive}. ${topCurrentArtist ? `${topCurrentArtist} is one of the strongest artist signals right now.` : "The artist signal is spread across several favourites."}`}
    >
      <GlowPanel as="div" variant="row" className="overview-stepper__summary-panel">
        <p className="text-base leading-7 text-mist">{shorten(overview.taste_interpretation.summary, 300)}</p>
      </GlowPanel>
      <div className="overview-stepper__snapshot" aria-label="Data snapshot">
        <SnapshotItem label="Genres discovered" value={genresDiscovered.toLocaleString()} />
        <SnapshotItem label="Detected plays" value={overview.total_detected_plays.toLocaleString()} />
        <SnapshotItem label="Unique tracks" value={overview.unique_tracks.toLocaleString()} />
      </div>
      <div className="overview-stepper__actions overview-stepper__actions--wrap">
        <button className="btn-primary" type="button" onClick={onOpenReport}>Read full report</button>
        <button className="btn-secondary" type="button" onClick={onOpenScores}>View scores</button>
        <button className="btn-secondary" type="button" onClick={onOpenPatterns}>View patterns</button>
      </div>
    </OverviewSection>
  );
}

function OverviewSection({ eyebrow, title, intro, aside, children }: { eyebrow: string; title: string; intro: string; aside?: ReactNode; children: ReactNode }) {
  return (
    <section className="overview-stepper__section">
      <div className={aside ? "overview-stepper__section-grid" : ""}>
        <div className="min-w-0">
          <p className="overview-stepper__eyebrow">{eyebrow}</p>
          <h2 className="overview-stepper__title">{title}</h2>
          <p className="overview-stepper__intro">{intro}</p>
        </div>
        {aside ? <div className="min-w-0">{aside}</div> : null}
      </div>
      <div className="overview-stepper__body">{children}</div>
    </section>
  );
}

function DataCard({ label, value, detail }: { label: string; value: string; detail: string }) {
  return (
    <GlowPanel as="article" variant="row" className="overview-stepper__data-card">
      <p className="text-xs font-semibold uppercase tracking-[0.14em] text-mist/65">{label}</p>
      <p className="mt-3 text-2xl font-black leading-tight text-white">{value}</p>
      <p className="mt-2 text-sm leading-6 text-mist">{detail}</p>
    </GlowPanel>
  );
}

function SignalCard({ icon, label, value, detail }: { icon: ReactNode; label: string; value: string; detail: string }) {
  return (
    <GlowPanel as="article" variant="row" className="overview-stepper__signal-card">
      <div className="overview-stepper__signal-icon">{icon}</div>
      <div className="min-w-0">
        <p className="text-xs font-semibold uppercase tracking-[0.14em] text-mist/65">{label}</p>
        <p className="mt-2 text-2xl font-black leading-tight text-white">{value}</p>
        <p className="mt-2 text-sm leading-6 text-mist">{detail}</p>
      </div>
    </GlowPanel>
  );
}

function SoundGroup({ title, items }: { title: string; items: { label: string; value: string }[] }) {
  return (
    <GlowPanel as="div" variant="row" className="overview-stepper__sound-group">
      <h3 className="text-sm font-semibold uppercase tracking-[0.16em] text-red-200">{title}</h3>
      <div className="mt-4 space-y-3">
        {items.length ? items.map((item) => (
          <div key={item.label} className="overview-stepper__sound-item">
            <span>{item.label}</span>
            <strong>{item.value}</strong>
          </div>
        )) : <p className="text-sm text-mist">No confident signal yet.</p>}
      </div>
    </GlowPanel>
  );
}

type MovementItem = {
  key: string;
  rank: number;
  title: string;
  subtitle: string;
  metric: string;
  direction: "up" | "down" | "new" | "returning" | "stable";
};

function movementItems(items: PeriodTopItem[], kind: "song" | "artist"): MovementItem[] {
  return items
    .filter((item) => item.movement || item.interpretation_label === "Returning favourite")
    .map((item) => {
      const movement = item.movement;
      const direction = movement?.direction === "up" ? "up" : movement?.direction === "down" ? "down" : movement?.direction === "new" ? "new" : item.interpretation_label === "Returning favourite" ? "returning" : "stable";
      return {
        key: `${kind}-${item.key}`,
        rank: item.rank,
        title: kind === "artist" ? item.artist : item.title ?? "Unknown track",
        subtitle: kind === "artist" ? `${item.unique_songs ?? 0} songs, top track ${item.most_played_song ?? "unknown"}` : item.artist,
        metric: movement?.label ?? item.interpretation_label,
        direction,
      };
    });
}

function MovementRow({ item }: { item: MovementItem }) {
  const Icon = item.direction === "up" ? ArrowUp : item.direction === "down" ? ArrowDown : item.direction === "new" ? Sparkles : item.direction === "returning" ? RotateCcw : BarChart3;
  return (
    <GlowPanel as="article" variant="row" className="overview-stepper__movement-row">
      <span className="overview-stepper__movement-rank">#{item.rank}</span>
      <div className="overview-stepper__movement-icon" data-direction={item.direction}>
        <Icon size={16} />
      </div>
      <div className="min-w-0">
        <h3 className="truncate text-base font-black text-white">{item.title}</h3>
        <p className="truncate text-sm text-mist">{item.subtitle}</p>
      </div>
      <span className="overview-stepper__movement-metric">{item.metric}</span>
    </GlowPanel>
  );
}

function SnapshotItem({ label, value }: { label: string; value: string }) {
  return (
    <div className="overview-stepper__snapshot-item">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

function initials(value: string) {
  const parts = value.split(/\s+/).filter(Boolean);
  return (parts[0]?.[0] ?? "?") + (parts[1]?.[0] ?? "");
}

function shorten(value: string, maxLength: number) {
  if (value.length <= maxLength) return value;
  return `${value.slice(0, maxLength - 1).trim()}...`;
}
