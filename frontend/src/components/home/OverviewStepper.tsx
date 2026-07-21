import { ArrowDown, ArrowUp, BarChart3, Compass, Disc3, Gauge, Info, RotateCcw, Sparkles } from "lucide-react";
import type { ReactNode } from "react";
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
          comparison={comparison}
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
  comparison,
  topArtist,
  repeatScore,
  discoveryScore,
  visualTheme,
  onOpenReport,
}: {
  overview: Overview;
  thisMonthMinutes: ListeningMinutes | null;
  currentTaste: TasteDnaExplorer | null;
  comparison: TasteDnaComparison | null;
  topArtist: PeriodTopItem | null;
  repeatScore: ScoreMetric;
  discoveryScore: ScoreMetric;
  visualTheme: PersonaVisualTheme;
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
      image={visualTheme.secondaryImages[0]}
      aside={
        <aside className="overview-stepper__artist-focus">
          <ArtistAvatar artistImageUrl={topArtist?.artist_image_url} artistName={topArtist?.artist ?? "Current anchor artist"} size="hero" priority fallbackLabel={initials(topArtist?.artist ?? "Artist")} shape="rounded" />
          <div className="min-w-0">
            <p className="overview-stepper__micro-label">Current anchor</p>
            <h3 className="overview-stepper__artist-name">{topArtist?.artist ?? "No clear anchor yet"}</h3>
            <p className="overview-stepper__plain-copy">
              {topArtist ? `${topArtist.play_count.toLocaleString()} detected plays, ${topArtist.unique_songs ?? 0} songs, ${topArtist.share_of_period}% of the period.` : "Refresh more current data to establish a clear artist signal."}
            </p>
          </div>
        </aside>
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

function CoreSoundSection({ overview, currentTaste, visualTheme }: { overview: Overview; currentTaste: TasteDnaExplorer | null; visualTheme: PersonaVisualTheme }) {
  const taste = overview.taste_interpretation;
  const coreGenres = taste.core_genre_families.slice(0, 4);
  const secondary = (taste.secondary_genre_families.length ? taste.secondary_genre_families : taste.side_quests).slice(0, 2);
  const traits = (currentTaste?.traits.map((trait) => trait.trait) ?? taste.sonic_traits).slice(0, 7);

  return (
    <OverviewSection
      eyebrow="Core Sound"
      title="The centre is emotional alternative, with atmosphere around the edges."
      intro={shorten(overview.taste_interpretation.summary, 240)}
      image={visualTheme.secondaryImages[1] ?? visualTheme.primaryImage}
    >
      <div className="overview-stepper__sound-grid">
        <SoundGroup title="Main genres" items={coreGenres.map((item) => ({ label: item.name, value: `${item.share}%` }))} />
        <SoundGroup title="Secondary influences" items={secondary.map((item) => ({ label: item.name, value: `${item.share}%` }))} />
      </div>
      <div className="overview-stepper__trait-panel">
        <p className="overview-stepper__micro-label">Strongest sonic traits</p>
        <p className="overview-stepper__trait-list">
          {traits.map((trait) => <span key={trait}>{trait}</span>)}
        </p>
      </div>
      {taste.coverage.unknown_artist_coverage_percent > 30 ? (
        <p className="overview-stepper__footnote">
          <Info size={15} aria-hidden="true" />
          <span>Genre claims are strongest for mapped artists; {Math.round(taste.coverage.unknown_artist_coverage_percent)}% of artist coverage is still unknown.</span>
        </p>
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
      intro="These are calculated behaviour signals from repeat plays, artist concentration, discovery share, and duration-aware listening time."
      image={visualTheme.secondaryImages[0] ?? visualTheme.primaryImage}
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
      intro={comparison?.summary_sentence ?? "Movement is based on this period versus the previous comparable period where there is enough listening data."}
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
  const genresDiscovered = overview.taste_interpretation.canonical_genre_shares.length;

  return (
    <OverviewSection
      eyebrow="Personal Summary"
      title={overview.headline_persona}
      intro={`The most distinctive pattern is ${distinctive}. ${topCurrentArtist ? `${topCurrentArtist} is one of the strongest artist signals right now.` : "The artist signal is spread across several favourites."}`}
      image={visualTheme.primaryImage}
    >
      <div className="overview-stepper__summary-panel">
        <p className="text-base leading-7 text-mist">{shorten(overview.taste_interpretation.summary, 300)}</p>
      </div>
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
    <article className="overview-stepper__data-card">
      <p className="overview-stepper__micro-label">{label}</p>
      <p className="overview-stepper__data-value">{value}</p>
      <p className="overview-stepper__plain-copy">{detail}</p>
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

function SoundGroup({ title, items }: { title: string; items: { label: string; value: string }[] }) {
  return (
    <div className="overview-stepper__sound-group">
      <h3 className="overview-stepper__micro-label overview-stepper__micro-label--accent">{title}</h3>
      <div className="mt-4 space-y-3">
        {items.length ? items.map((item) => (
          <div key={item.label} className="overview-stepper__sound-item">
            <span>{item.label}</span>
            <strong>{item.value}</strong>
          </div>
        )) : <p className="overview-stepper__plain-copy">No confident signal yet.</p>}
      </div>
    </div>
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

function shorten(value: string, maxLength: number) {
  if (value.length <= maxLength) return value;
  const sentences = value.match(/[^.!?]+[.!?]+/g)?.map((sentence) => sentence.trim()).filter(Boolean) ?? [];
  const concise = sentences.reduce((current, sentence) => {
    const next = current ? `${current} ${sentence}` : sentence;
    return next.length <= maxLength ? next : current;
  }, "");
  if (concise) return concise;
  const boundary = value.lastIndexOf(" ", maxLength);
  const clipped = value.slice(0, boundary > 60 ? boundary : maxLength).replace(/[,\s;:]+$/g, "").trim();
  return clipped.endsWith(".") ? clipped : `${clipped}.`;
}
