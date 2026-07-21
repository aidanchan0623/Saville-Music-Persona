import { ArrowDown, ArrowUp, BarChart3, Compass, Disc3, Gauge, RotateCcw, Sparkles } from "lucide-react";
import type { CSSProperties, ReactNode } from "react";
import { ArtistAvatar, PersonaBackground } from "../Artwork";
import Stepper, { Step } from "../reactbits/Stepper/Stepper";
import type { ListeningMinutes, Overview, PeriodTopItem, PeriodTopResponse, ScoreMetric, TasteDnaComparison, TasteDnaExplorer } from "../../types/api";
import { asPercent, formatMinutes } from "../../utils/format";
import type { PersonaThemeImage, PersonaVisualTheme } from "../../utils/personaVisualTheme";
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
  visualTheme: PersonaVisualTheme;
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
  visualTheme,
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
          topArtist={topArtist}
          repeatScore={overview.repeat_score}
          discoveryScore={overview.discovery_score}
          visualTheme={visualTheme}
          onOpenReport={onOpenReport}
        />
      </Step>
      <Step>
        <CoreSoundSection overview={overview} currentTaste={currentTaste} visualTheme={visualTheme} />
      </Step>
      <Step>
        <ListeningBehaviourSection
          overview={overview}
          thisMonthMinutes={thisMonthMinutes}
          rollingYearMinutes={rollingYearMinutes}
          artistLoyaltyScore={scoreByKey.get("artist_loyalty")}
          nicheScore={scoreByKey.get("mainstream_niche")}
          visualTheme={visualTheme}
        />
      </Step>
      <Step>
        <RecentMovementSection currentTopArtists={currentTopArtists} currentTopTracks={currentTopTracks} comparison={comparison} visualTheme={visualTheme} onOpenTop10={onOpenTop10} />
      </Step>
      <Step>
        <PersonalSummarySection
          overview={overview}
          currentTopArtists={currentTopArtists}
          visualTheme={visualTheme}
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
  topArtist,
  repeatScore,
  discoveryScore,
  visualTheme,
  onOpenReport,
}: {
  overview: Overview;
  thisMonthMinutes: ListeningMinutes | null;
  currentTaste: TasteDnaExplorer | null;
  topArtist: PeriodTopItem | null;
  repeatScore: ScoreMetric;
  discoveryScore: ScoreMetric;
  visualTheme: PersonaVisualTheme;
  onOpenReport: () => void;
}) {
  const dominantCluster = currentTaste?.nodes[0]?.name ?? overview.top_genre_cluster;
  const comfortLabel = repeatScore.value >= discoveryScore.value ? "comfort-leaning" : "discovery-leaning";
  const headline = repeatScore.value >= discoveryScore.value ? "This phase is built around repeat gravity." : "This phase is more exploratory than usual.";
  const anchorLine = topArtist ? `${topArtist.artist} anchors this window.` : "No clear anchor yet.";

  return (
    <OverviewSection
      eyebrow="Current Listening State"
      title={headline}
      intro={`${dominantCluster || "Your mapped sound"} leads right now. ${anchorLine}`}
      image={visualTheme.secondaryImages[0]}
      aside={
        <aside className="overview-stepper__artist-focus">
          <ArtistAvatar artistImageUrl={topArtist?.artist_image_url} artistName={topArtist?.artist ?? "Current anchor artist"} size="hero" priority fallbackLabel={initials(topArtist?.artist ?? "Artist")} shape="rounded" />
          <div className="min-w-0">
            <p className="overview-stepper__micro-label">Current anchor</p>
            <h3 className="overview-stepper__artist-name">{topArtist?.artist ?? "No clear anchor yet"}</h3>
            <p className="overview-stepper__plain-copy">{topArtist ? `${topArtist.unique_songs ?? 0} songs in rotation` : "More current data will sharpen this."}</p>
          </div>
        </aside>
      }
    >
      <div className="overview-stepper__metric-grid overview-stepper__metric-grid--state">
        <DataCard label="Listening time" value={thisMonthMinutes ? formatMinutes(thisMonthMinutes.metrics.current_month_total_minutes) : "Unavailable"} />
        <DataCard label="Dominant sound" value={dominantCluster || "Still mapping"} />
        <DataCard label="Comfort vs discovery" value={comfortLabel} />
      </div>
      <div className="overview-stepper__actions">
        <button className="btn-primary" type="button" onClick={onOpenReport}>Open Persona Report</button>
      </div>
    </OverviewSection>
  );
}

function CoreSoundSection({ overview, currentTaste, visualTheme }: { overview: Overview; currentTaste: TasteDnaExplorer | null; visualTheme: PersonaVisualTheme }) {
  const taste = overview.taste_interpretation;
  const segments = buildGenreSegments(taste);
  const traits = (currentTaste?.traits.map((trait) => trait.trait) ?? taste.sonic_traits).slice(0, 5);

  return (
    <OverviewSection
      eyebrow="Core Sound"
      title="The centre is emotional alternative, with atmosphere around the edges."
      intro="Mapped genre composition from your listening."
      image={visualTheme.secondaryImages[1] ?? visualTheme.primaryImage}
    >
      <GenreStack segments={segments} />
      <div className="overview-stepper__trait-line">
        <p className="overview-stepper__micro-label">Strongest sonic traits</p>
        <p className="overview-stepper__trait-list">
          {traits.map((trait) => <span key={trait}>{trait}</span>)}
        </p>
      </div>
    </OverviewSection>
  );
}

function ListeningBehaviourSection({
  overview,
  thisMonthMinutes,
  rollingYearMinutes,
  artistLoyaltyScore,
  nicheScore,
  visualTheme,
}: {
  overview: Overview;
  thisMonthMinutes: ListeningMinutes | null;
  rollingYearMinutes: ListeningMinutes | null;
  artistLoyaltyScore?: ScoreMetric;
  nicheScore?: ScoreMetric;
  visualTheme: PersonaVisualTheme;
}) {
  const dna = overview.taste_dna;
  const activeDays = thisMonthMinutes?.metrics.active_listening_days ?? rollingYearMinutes?.metrics.active_listening_days;
  const streak = thisMonthMinutes?.metrics.current_listening_streak_days ?? rollingYearMinutes?.metrics.current_listening_streak_days;
  const durationCoverage = thisMonthMinutes?.duration_quality.duration_coverage_percent ?? rollingYearMinutes?.duration_quality.duration_coverage_percent;

  return (
    <OverviewSection
      eyebrow="Listening Behaviour"
      title="Known favourites carry the profile, but the sound world is not narrow."
      intro="Replay, discovery, artist pull, and listening rhythm."
      image={visualTheme.secondaryImages[0] ?? visualTheme.primaryImage}
    >
      <div className="overview-stepper__metric-grid overview-stepper__metric-grid--wide">
        <SignalCard icon={<RotateCcw size={18} />} label="Repeat listening" value={asPercent(overview.repeat_score.value)} detail={overview.repeat_score.label} />
        <SignalCard icon={<Compass size={18} />} label="Discovery" value={asPercent(overview.discovery_score.value)} detail={overview.discovery_score.label} />
        <SignalCard icon={<Gauge size={18} />} label="Artist concentration" value={asPercent(dna.artist_concentration.value)} detail={dna.artist_concentration.label} />
        <SignalCard icon={<Disc3 size={18} />} label="Comfort tendency" value={asPercent(dna.exploration_vs_comfort.value)} detail={dna.exploration_vs_comfort.label} />
      </div>
      <div className="overview-stepper__support-row">
        {artistLoyaltyScore ? <DataCard label="Artist loyalty" value={asPercent(artistLoyaltyScore.value)} detail={artistLoyaltyScore.label} /> : null}
        {nicheScore ? <DataCard label="Niche estimate" value={asPercent(nicheScore.value)} detail={nicheScore.label} /> : null}
        {activeDays !== undefined ? <DataCard label="Active days" value={activeDays.toLocaleString()} detail={streak ? `${streak} day streak` : undefined} /> : null}
        {durationCoverage !== undefined ? <DataCard label="Minute confidence" value={asPercent(durationCoverage)} /> : null}
      </div>
    </OverviewSection>
  );
}

function RecentMovementSection({
  currentTopArtists,
  currentTopTracks,
  comparison,
  visualTheme,
  onOpenTop10,
}: {
  currentTopArtists: PeriodTopResponse | null;
  currentTopTracks: PeriodTopResponse | null;
  comparison: TasteDnaComparison | null;
  visualTheme: PersonaVisualTheme;
  onOpenTop10: () => void;
}) {
  const movers = [...movementItems(currentTopTracks?.items ?? [], "song"), ...movementItems(currentTopArtists?.items ?? [], "artist")].slice(0, 6);

  return (
    <OverviewSection
      eyebrow="Recent Movement"
      title="The current month has a few clear jumps, not a full identity reset."
      intro={comparison?.claims.growing_cluster ? `${comparison.claims.growing_cluster.name} is rising.` : "Rank movement from the current period."}
      image={visualTheme.secondaryImages[2] ?? visualTheme.primaryImage}
    >
      <div className="overview-stepper__movement-list">
        {movers.length ? movers.map((item) => <MovementRow key={item.key} item={item} />) : <p className="overview-stepper__empty-line">No meaningful movement signal is available for this period yet.</p>}
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
  visualTheme,
  onOpenReport,
  onOpenScores,
  onOpenPatterns,
}: {
  overview: Overview;
  currentTopArtists: PeriodTopResponse | null;
  visualTheme: PersonaVisualTheme;
  onOpenReport: () => void;
  onOpenScores: () => void;
  onOpenPatterns: () => void;
}) {
  const topCurrentArtist = currentTopArtists?.items[0]?.artist ?? overview.top_3_artists[0]?.artist;
  const distinctive = overview.taste_interpretation.listening_character.slice(0, 3).join(", ") || overview.taste_dna.core_dna[0] || "a stable mapped taste profile";

  return (
    <OverviewSection
      eyebrow="Personal Summary"
      title={overview.headline_persona}
      intro={`The most distinctive pattern is ${distinctive}. ${topCurrentArtist ? `${topCurrentArtist} is one of the strongest artist signals right now.` : "The artist signal is spread across several favourites."}`}
      image={visualTheme.primaryImage}
    >
      <div className="overview-stepper__snapshot" aria-label="Data snapshot">
        <SnapshotItem label="Unique artists" value={overview.unique_artists.toLocaleString()} />
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

function OverviewSection({
  eyebrow,
  title,
  intro,
  aside,
  image,
  children,
}: {
  eyebrow: string;
  title: string;
  intro: string;
  aside?: ReactNode;
  image?: PersonaThemeImage;
  children: ReactNode;
}) {
  return (
    <section className={`overview-stepper__section${image ? " overview-stepper__section--with-image" : ""}`}>
      {image ? (
        <div className="overview-stepper__image-edge" aria-hidden="true">
          <PersonaBackground image={image} />
        </div>
      ) : null}
      <div className={aside ? "overview-stepper__section-grid" : ""}>
        <div className="min-w-0">
          <p className="overview-stepper__eyebrow">{eyebrow}</p>
          <h2 className="overview-stepper__title">{title}</h2>
          {intro ? <p className="overview-stepper__intro">{intro}</p> : null}
        </div>
        {aside ? <div className="min-w-0">{aside}</div> : null}
      </div>
      <div className="overview-stepper__body">{children}</div>
    </section>
  );
}

function DataCard({ label, value, detail }: { label: string; value: string; detail?: string }) {
  return (
    <article className="overview-stepper__data-card">
      <p className="overview-stepper__micro-label">{label}</p>
      <p className="overview-stepper__data-value">{value}</p>
      {detail ? <p className="overview-stepper__plain-copy">{detail}</p> : null}
    </article>
  );
}

function SignalCard({ icon, label, value, detail }: { icon: ReactNode; label: string; value: string; detail: string }) {
  return (
    <article className="overview-stepper__signal-card">
      <div className="overview-stepper__signal-icon">{icon}</div>
      <div className="min-w-0">
        <p className="overview-stepper__micro-label">{label}</p>
        <p className="overview-stepper__data-value">{value}</p>
        <p className="overview-stepper__plain-copy">{detail}</p>
      </div>
    </article>
  );
}

type GenreSegment = {
  label: string;
  value: number;
  color: string;
};

function GenreStack({ segments }: { segments: GenreSegment[] }) {
  if (!segments.length) {
    return <p className="overview-stepper__empty-line">No confident genre composition yet.</p>;
  }
  return (
    <div className="overview-stepper__genre-stack" aria-label="Core genre composition">
      <div className="overview-stepper__stack-bar">
        {segments.map((segment, index) => (
          <span
            key={segment.label}
            className="overview-stepper__stack-segment"
            style={{
              "--segment-share": `${segment.value}%`,
              "--segment-color": segment.color,
              "--segment-delay": `${index * 90}ms`,
            } as CSSProperties}
            title={`${segment.label}: ${formatShare(segment.value)}`}
            aria-label={`${segment.label}: ${formatShare(segment.value)}`}
          />
        ))}
      </div>
      <div className="overview-stepper__stack-legend">
        {segments.map((segment) => (
          <span key={segment.label} className="overview-stepper__legend-item">
            <i style={{ backgroundColor: segment.color }} aria-hidden="true" />
            <span>{segment.label}</span>
            <strong>{formatShare(segment.value)}</strong>
          </span>
        ))}
      </div>
    </div>
  );
}

function buildGenreSegments(taste: Overview["taste_interpretation"]): GenreSegment[] {
  const source = (
    taste.cluster_shares.length
      ? taste.cluster_shares
      : [...taste.core_genre_families, ...taste.secondary_genre_families, ...taste.side_quests]
  ).filter((item) => item.share > 0);
  const palette = ["#e52b32", "#7b1118", "#4a1d22", "#5f5f66", "#96969d"];
  const segments: GenreSegment[] = [];
  let used = 0;
  for (const item of source.slice(0, 5)) {
    if (used >= 99.5) break;
    const value = Math.max(0, Math.min(item.share, 100 - used));
    if (value <= 0) continue;
    segments.push({ label: item.name, value: roundShare(value), color: palette[segments.length % palette.length] });
    used += value;
  }
  const remaining = roundShare(Math.max(0, 100 - used));
  if (remaining >= 0.5) {
    segments.push({ label: "Other / unclassified", value: remaining, color: "#29292e" });
  }
  return segments;
}

function formatShare(value: number) {
  return `${Number.isInteger(value) ? value.toFixed(0) : value.toFixed(1)}%`;
}

function roundShare(value: number) {
  return Math.round(value * 10) / 10;
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
    <article className="overview-stepper__movement-row">
      <span className="overview-stepper__movement-rank">#{item.rank}</span>
      <div className="overview-stepper__movement-icon" data-direction={item.direction}>
        <Icon size={16} />
      </div>
      <div className="min-w-0">
        <h3 className="overview-stepper__movement-title">{item.title}</h3>
        <p className="overview-stepper__movement-subtitle">{item.subtitle}</p>
      </div>
      <span className="overview-stepper__movement-metric">{item.metric}</span>
    </article>
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
