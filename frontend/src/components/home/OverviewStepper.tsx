import type { CSSProperties, ReactNode } from "react";
import { ArtistAvatar, PersonaBackground, TrackArtwork } from "../Artwork";
import Stepper, { Step } from "../reactbits/Stepper/Stepper";
import type { MusicIdentity, MusicalAge, Overview, OverviewPeriod, TasteDnaExplorer, TopFive } from "../../types/api";
import type { PersonaThemeImage, PersonaVisualTheme } from "../../utils/personaVisualTheme";
import "./OverviewStepper.css";

type OverviewStepperProps = {
  overview: Overview;
  identity: MusicIdentity;
  musicalAge: MusicalAge;
  topFive: TopFive;
  selectedPeriod: OverviewPeriod;
  currentTaste: TasteDnaExplorer | null;
  visualTheme: PersonaVisualTheme;
  onOpenTop10: () => void;
  onOpenInsights: () => void;
  onOpenReport: () => void;
};

const STEP_LABELS = ["Current State", "Core Sound", "Musical Age", "Top 5", "Summary"];

export function OverviewStepper({
  overview,
  identity,
  musicalAge,
  topFive,
  selectedPeriod,
  currentTaste,
  visualTheme,
  onOpenTop10,
  onOpenInsights,
  onOpenReport,
}: OverviewStepperProps) {
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
        <ListeningStateSection overview={overview} topFive={topFive} period={selectedPeriod} visualTheme={visualTheme} onOpenReport={onOpenReport} />
      </Step>
      <Step>
        <CoreSoundSection overview={overview} currentTaste={currentTaste} visualTheme={visualTheme} />
      </Step>
      <Step>
        <MusicalAgeSection musicalAge={musicalAge} visualTheme={visualTheme} />
      </Step>
      <Step>
        <TopFiveSection topFive={topFive} visualTheme={visualTheme} onOpenTop10={onOpenTop10} />
      </Step>
      <Step>
        <PersonalSummarySection
          overview={overview}
          identity={identity}
          period={selectedPeriod}
          visualTheme={visualTheme}
          onOpenReport={onOpenReport}
          onOpenInsights={onOpenInsights}
        />
      </Step>
    </Stepper>
  );
}

function ListeningStateSection({
  overview,
  topFive,
  period,
  visualTheme,
  onOpenReport,
}: {
  overview: Overview;
  topFive: TopFive;
  period: OverviewPeriod;
  visualTheme: PersonaVisualTheme;
  onOpenReport: () => void;
}) {
  const topArtist = topFive.artists[0] ?? null;
  const topSong = topFive.songs[0] ?? null;
  const headline = topArtist ? `${topArtist.name} holds the centre of this window.` : "This listening window is still forming.";

  return (
    <OverviewSection
      eyebrow="Current Listening State"
      title={headline}
      intro={`${overview.top_genre_cluster || "Your mapped sound"} leads ${period.label}. Rankings and counts below use this same timeframe.`}
      image={visualTheme.secondaryImages[0]}
      aside={
        <aside className="overview-stepper__artist-focus">
          <ArtistAvatar artistImageUrl={topArtist?.imageUrl} artistName={topArtist?.name ?? "Current anchor artist"} size="hero" priority shape="rounded" />
          <div className="min-w-0">
            <p className="overview-stepper__micro-label">Current anchor</p>
            <h3 className="overview-stepper__artist-name">{topArtist?.name ?? "No clear anchor yet"}</h3>
            <p className="overview-stepper__plain-copy">{topArtist ? `${topArtist.detectedPlays.toLocaleString()} detected plays across ${topArtist.uniqueSongs.toLocaleString()} songs` : "More listening will sharpen this view."}</p>
          </div>
        </aside>
      }
    >
      <div className="overview-stepper__metric-grid">
        <DataCard label="Top song" value={topSong?.title ?? "Still mapping"} detail={topSong?.artist} />
        <DataCard label="Dominant sound" value={overview.top_genre_cluster || "Still mapping"} />
        <DataCard label="Detected plays" value={overview.total_detected_plays.toLocaleString()} detail={period.label} />
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
  const supporting = segments.slice(1, 3).map((item) => item.label).join(" and ");

  return (
    <OverviewSection
      eyebrow="Core Sound"
      title={`${overview.top_genre_cluster || "Your strongest sound"} holds the centre${supporting ? `, with ${supporting} around it` : ""}.`}
      intro="Mapped composition from the selected listening window."
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

function MusicalAgeSection({ musicalAge, visualTheme }: { musicalAge: MusicalAge; visualTheme: PersonaVisualTheme }) {
  return (
    <OverviewSection
      eyebrow="Musical Age"
      title={musicalAge.title}
      intro={`Musical age based on your ${musicalAge.sourcePeriod.label.replace(/^Rolling year/, "rolling year")} profile.`}
      image={visualTheme.secondaryImages[0] ?? visualTheme.primaryImage}
    >
      <div className="overview-stepper__age-layout">
        <div className="overview-stepper__age-number" aria-label={`Musical age ${musicalAge.age}`}>
          {musicalAge.age}
        </div>
        <div className="overview-stepper__age-copy">
          <p className="overview-stepper__age-summary">{musicalAge.summary}</p>
          <p className="overview-stepper__plain-copy">Likely range: {musicalAge.likelyMin}-{musicalAge.likelyMax}</p>
          <p className="overview-stepper__confidence">{musicalAge.confidenceLabel}</p>
        </div>
      </div>
      <p className="overview-stepper__age-explanation">{musicalAge.explanation}</p>
      <details className="overview-stepper__age-disclosure">
        <summary>What does this mean?</summary>
        <p>Musical age is a playful estimate of the emotional character of your listening. It is not your physical age or a measure of emotional maturity.</p>
      </details>
    </OverviewSection>
  );
}

function TopFiveSection({ topFive, visualTheme, onOpenTop10 }: { topFive: TopFive; visualTheme: PersonaVisualTheme; onOpenTop10: () => void }) {
  return (
    <OverviewSection
      eyebrow="Your Rotation"
      title={`Top 5 for ${topFive.period.label}`}
      intro="The same deterministic ranking used by the Top 10 page."
      image={visualTheme.secondaryImages[2] ?? visualTheme.primaryImage}
    >
      <div className="overview-stepper__top-five-grid">
        <RankingList title={`Top songs for ${topFive.period.label}`} empty="No valid songs in this period.">
          {topFive.songs.map((song) => (
            <article className="overview-stepper__ranking-row" key={`${song.rank}-${song.title}-${song.artist}`}>
              <span className="overview-stepper__ranking-number">{song.rank}</span>
              <TrackArtwork trackImageUrl={song.imageUrl} title={song.title} size="sm" />
              <div className="min-w-0">
                <strong>{song.title}</strong>
                <span>{song.artist}</span>
              </div>
              <em>{song.detectedPlays.toLocaleString()} plays</em>
            </article>
          ))}
        </RankingList>
        <RankingList title={`Top artists for ${topFive.period.label}`} empty="No valid artists in this period.">
          {topFive.artists.map((artist) => (
            <article className="overview-stepper__ranking-row" key={`${artist.rank}-${artist.name}`}>
              <span className="overview-stepper__ranking-number">{artist.rank}</span>
              <ArtistAvatar artistImageUrl={artist.imageUrl} artistName={artist.name} size="sm" />
              <div className="min-w-0">
                <strong>{artist.name}</strong>
                <span>{artist.uniqueSongs.toLocaleString()} unique songs</span>
              </div>
              <em>{artist.detectedPlays.toLocaleString()} plays</em>
            </article>
          ))}
        </RankingList>
      </div>
      <div className="overview-stepper__actions">
        <button className="btn-secondary" type="button" onClick={onOpenTop10}>Open Top 10</button>
      </div>
    </OverviewSection>
  );
}

function RankingList({ title, empty, children }: { title: string; empty: string; children: ReactNode }) {
  const hasItems = Array.isArray(children) ? children.length > 0 : Boolean(children);
  return (
    <section className="overview-stepper__ranking-list">
      <h3>{title}</h3>
      {hasItems ? children : <p className="overview-stepper__empty-line">{empty}</p>}
    </section>
  );
}

function PersonalSummarySection({
  overview,
  identity,
  period,
  visualTheme,
  onOpenReport,
  onOpenInsights,
}: {
  overview: Overview;
  identity: MusicIdentity;
  period: OverviewPeriod;
  visualTheme: PersonaVisualTheme;
  onOpenReport: () => void;
  onOpenInsights: () => void;
}) {
  return (
    <OverviewSection
      eyebrow="Personal Summary"
      title={identity.characterTitle}
      intro={`${identity.explanation} This summary uses ${period.label}.`}
      image={visualTheme.primaryImage}
    >
      <div className="overview-stepper__snapshot" aria-label="Selected-period data snapshot">
        <SnapshotItem label="Unique artists" value={overview.unique_artists.toLocaleString()} />
        <SnapshotItem label="Unique tracks" value={overview.unique_tracks.toLocaleString()} />
        <SnapshotItem label="Detected plays" value={overview.total_detected_plays.toLocaleString()} />
      </div>
      <div className="overview-stepper__actions overview-stepper__actions--wrap">
        <button className="btn-primary" type="button" onClick={onOpenReport}>Read full report</button>
        <button className="btn-secondary" type="button" onClick={onOpenInsights}>View insights</button>
      </div>
    </OverviewSection>
  );
}

function OverviewSection({ eyebrow, title, intro, aside, image, children }: { eyebrow: string; title: string; intro: string; aside?: ReactNode; image?: PersonaThemeImage; children: ReactNode }) {
  return (
    <section className={`overview-stepper__section${image ? " overview-stepper__section--with-image" : ""}`}>
      {image ? <div className="overview-stepper__image-edge" aria-hidden="true"><PersonaBackground image={image} /></div> : null}
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
  return <article className="overview-stepper__data-card"><p className="overview-stepper__micro-label">{label}</p><p className="overview-stepper__data-value">{value}</p>{detail ? <p className="overview-stepper__plain-copy">{detail}</p> : null}</article>;
}

type GenreSegment = { label: string; value: number; color: string };

function GenreStack({ segments }: { segments: GenreSegment[] }) {
  if (!segments.length) return <p className="overview-stepper__empty-line">No confident genre composition yet.</p>;
  return (
    <div className="overview-stepper__genre-stack" aria-label="Core genre composition">
      <div className="overview-stepper__stack-bar">
        {segments.map((segment, index) => <span key={segment.label} className="overview-stepper__stack-segment" style={{ "--segment-share": `${segment.value}%`, "--segment-color": segment.color, "--segment-delay": `${index * 90}ms` } as CSSProperties} title={`${segment.label}: ${formatShare(segment.value)}`} />)}
      </div>
      <div className="overview-stepper__stack-legend">
        {segments.map((segment) => <span key={segment.label} className="overview-stepper__legend-item"><i style={{ backgroundColor: segment.color }} aria-hidden="true" /><span>{segment.label}</span><strong>{formatShare(segment.value)}</strong></span>)}
      </div>
    </div>
  );
}

function buildGenreSegments(taste: Overview["taste_interpretation"]): GenreSegment[] {
  const source = (taste.cluster_shares.length ? taste.cluster_shares : [...taste.core_genre_families, ...taste.secondary_genre_families, ...taste.side_quests]).filter((item) => item.share > 0);
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
  if (remaining >= 0.5) segments.push({ label: "Other / unclassified", value: remaining, color: "#29292e" });
  return segments;
}

function SnapshotItem({ label, value }: { label: string; value: string }) {
  return <div className="overview-stepper__snapshot-item"><span>{label}</span><strong>{value}</strong></div>;
}

function formatShare(value: number) {
  return `${Number.isInteger(value) ? value.toFixed(0) : value.toFixed(1)}%`;
}

function roundShare(value: number) {
  return Math.round(value * 10) / 10;
}
