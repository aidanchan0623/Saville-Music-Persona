import { Sparkles } from "lucide-react";
import { useMemo, useRef } from "react";
import type { ReactNode } from "react";
import { motion, useInView, useReducedMotion } from "motion/react";
import { AlbumCover, ArtistAvatar } from "../../components/Artwork";
import CountUp from "../../components/reactbits/CountUp/CountUp";
import { FadeContent } from "../../components/reactbits/FadeContent/FadeContent";
import type { MusicCharacterResponse, MusicSource, PersonaMainCharacter, TopAlbumItem, TopArtist, TopTrack } from "../../types/api";
import { PersonaAlbumBackdrop } from "./PersonaAlbumBackdrop";
import {
  artistMetric,
  buildAlbumBackdropItems,
  buildGenreSegments,
  findArtist,
  formatShare,
  initials,
  scoreValue,
} from "./personaStoryModel";
import type { GenreSegment, PersonaStory } from "./personaStoryModel";

type GenerateMode = "serious" | "playful" | "roast";

type PersonaStoryExperienceProps = {
  story: PersonaStory;
  rollingCharacter: MusicCharacterResponse | null;
  currentCharacter: MusicCharacterResponse | null;
  favouriteAlbums: TopAlbumItem[];
  topArtists: TopArtist[];
  topTracks: TopTrack[];
  prerequisitesModelReady: boolean;
  busy: boolean;
  onGenerate: (mode: GenerateMode) => void;
  source: MusicSource;
  titleAnimationKey: string;
};

type ChapterLabel = {
  number: string;
  label: string;
};

const REPORT_ACTIONS: { mode: GenerateMode; label: string }[] = [
  { mode: "serious", label: "Regenerate" },
  { mode: "playful", label: "Playful" },
  { mode: "roast", label: "Light Roast" },
];

export function PersonaStoryExperience({
  story,
  rollingCharacter,
  currentCharacter,
  favouriteAlbums,
  topArtists,
  topTracks,
  prerequisitesModelReady,
  busy,
  onGenerate,
  source,
  titleAnimationKey,
}: PersonaStoryExperienceProps) {
  const albumCovers = useMemo(() => buildAlbumBackdropItems(favouriteAlbums, topTracks), [favouriteAlbums, topTracks]);
  const genreSegments = useMemo(() => buildGenreSegments(rollingCharacter), [rollingCharacter]);
  const topAlbum = favouriteAlbums.find((album) => album.album_image_url) ?? favouriteAlbums[0] ?? null;
  const repeatScore = scoreValue(rollingCharacter, "repeat");
  const discoveryScore = scoreValue(rollingCharacter, "discovery");
  const dominantSound = rollingCharacter?.top_clusters[0]?.name ?? genreSegments[0]?.label ?? "Your strongest sound-world";
  const traits = rollingCharacter?.sonic_traits.slice(0, 5) ?? [];

  return (
    <div className="persona-report-page">
      <PersonaAlbumBackdrop albums={albumCovers} />
      <div className="persona-report-content">
        <header className="persona-report__masthead" aria-label="Persona report controls">
          <div>
            <p className="persona-report__eyebrow">Persona Report</p>
            <p className="persona-report__meta">
              Six-part local story
              {!prerequisitesModelReady ? " / Gemma can fall back deterministically" : ""}
            </p>
          </div>
          <div className="persona-report__actions" aria-label="Generate persona report">
            {REPORT_ACTIONS.map((action, index) => (
              <button
                key={action.mode}
                className={index === 0 ? "btn-secondary persona-report__action-primary" : "btn-secondary"}
                disabled={busy}
                type="button"
                onClick={() => onGenerate(action.mode)}
              >
                {index === 0 ? <Sparkles size={16} /> : null}
                {action.label}
              </button>
            ))}
          </div>
        </header>

        <article className="persona-story" aria-label="Persona story report">

        <OpeningSection
          chapter={{ number: "01", label: "Opening" }}
          story={story}
          dominantSound={dominantSound}
          traits={traits}
          titleAnimationKey={titleAnimationKey}
        />

        <EditorialSection
          id="core-sound"
          chapter={{ number: "02", label: "Core Sound" }}
          headline={story.coreSound.headline}
          body={story.coreSound.body}
          pullQuote={story.coreSound.pullQuote}
          variant="core"
        >
          <CoreSoundVisual segments={genreSegments} traits={traits} />
        </EditorialSection>

        <EditorialSection
          id="comfort-loop"
          chapter={{ number: "03", label: "Comfort Loop" }}
          headline={story.comfortLoop.headline}
          body={story.comfortLoop.body}
          pullQuote={story.comfortLoop.pullQuote}
          variant="comfort"
          reversed
        >
          <ComfortVisual repeatScore={repeatScore} discoveryScore={discoveryScore} topAlbum={topAlbum} source={source} />
        </EditorialSection>

        <EditorialSection
          id="main-characters"
          chapter={{ number: "04", label: "Main Characters" }}
          headline="The Names That Hold The Frame"
          body="These recurring artists give the report continuity, tension, and recognizable gravity."
          variant="characters"
        >
          <MainCharactersVisual characters={story.mainCharacters} topArtists={topArtists} source={source} />
        </EditorialSection>

        <EditorialSection
          id="plot-twist"
          chapter={{ number: "05", label: "Plot Twist" }}
          headline={story.plotTwist.headline}
          body={story.plotTwist.body}
          variant="twist"
          reversed
        >
          <PlotTwistVisual rollingName={story.personaName} rollingCharacter={rollingCharacter} currentCharacter={currentCharacter} />
        </EditorialSection>

        <EditorialSection
          id="closing-note"
          chapter={{ number: "06", label: "Closing Note" }}
          headline={story.closing.headline}
          body={story.closing.body}
          pullQuote={story.closing.finalLine}
          variant="closing"
        >
          <ClosingVisual finalLine={story.closing.finalLine} />
        </EditorialSection>
        </article>
      </div>
    </div>
  );
}

function OpeningSection({
  chapter,
  story,
  dominantSound,
  traits,
  titleAnimationKey,
}: {
  chapter: ChapterLabel;
  story: PersonaStory;
  dominantSound: string;
  traits: string[];
  titleAnimationKey: string;
}) {
  return (
    <section id="opening" className="persona-story-section persona-section persona-section--opening" aria-labelledby="opening-title">
      <div className="persona-section__copy persona-section__copy--opening persona-copy-scrim">
        <StoryReveal delay={0.02}>
          <ChapterKicker chapter={chapter} />
        </StoryReveal>
        <StoryReveal delay={0.1} distance={42}>
          <h1 id="opening-title" key={titleAnimationKey}>
            {story.personaName}
          </h1>
        </StoryReveal>
        <StoryReveal className="persona-opening-hook" delay={0.18}>
          <p>{story.openingHook}</p>
        </StoryReveal>
        <StoryReveal delay={0.28}>
          <div className="persona-opening-signal">
            <span>Dominant sound</span>
            <strong>{dominantSound}</strong>
          </div>
        </StoryReveal>
        <StoryReveal delay={0.36}>
          <p className="persona-scroll-cue">Scroll to enter your listening story</p>
        </StoryReveal>
      </div>
      <StoryReveal className="persona-section__visual" delay={0.22} distance={28}>
        <aside className="persona-opening-atmosphere" aria-label="Opening sound details">
          <span>Sound weather</span>
          <strong>{dominantSound}</strong>
          {traits.length ? <p>{traits.join(" / ")}</p> : null}
        </aside>
      </StoryReveal>
    </section>
  );
}

type EditorialSectionProps = {
  id: string;
  chapter: ChapterLabel;
  headline: string;
  body: string;
  pullQuote?: string;
  children: ReactNode;
  variant: string;
  reversed?: boolean;
};

function EditorialSection({ id, chapter, headline, body, pullQuote, children, variant, reversed = false }: EditorialSectionProps) {
  return (
    <section
      id={id}
      className={`persona-story-section persona-section persona-section--${variant}${reversed ? " persona-section--reversed" : ""}`}
      aria-labelledby={`${id}-title`}
    >
      <div className="persona-section__copy persona-copy-scrim">
        <StoryReveal delay={0.02}>
          <ChapterKicker chapter={chapter} />
        </StoryReveal>
        <StoryReveal delay={0.1} distance={42}>
          <h2 id={`${id}-title`}>{headline}</h2>
        </StoryReveal>
        <StoryReveal delay={0.18}>
          <p className="persona-section__body">{body}</p>
        </StoryReveal>
        {pullQuote ? (
          <StoryReveal className="persona-section__quote" delay={0.28}>
            <blockquote>{pullQuote}</blockquote>
          </StoryReveal>
        ) : null}
      </div>
      <StoryReveal className="persona-section__visual" delay={0.22} distance={32}>
        {children}
      </StoryReveal>
    </section>
  );
}

function ChapterKicker({ chapter }: { chapter: ChapterLabel }) {
  return (
    <p className="persona-section__label">
      <span>{chapter.number}</span>
      {chapter.label}
    </p>
  );
}

function StoryReveal({
  children,
  className = "",
  delay = 0,
  distance = 34,
}: {
  children: ReactNode;
  className?: string;
  delay?: number;
  distance?: number;
}) {
  return (
    <FadeContent className={className} delay={delay} distance={distance} duration={0.68} threshold={0.18}>
      {children}
    </FadeContent>
  );
}

function CoreSoundVisual({ segments, traits }: { segments: GenreSegment[]; traits: string[] }) {
  const visibleSegments = segments.length ? segments : [{ label: "Signal forming", value: 100, color: "#343036" }];
  const barRef = useRef<HTMLDivElement | null>(null);
  const reducedMotion = useReducedMotion();
  const barInView = useInView(barRef, { once: true, amount: 0.24 });

  return (
    <div className="persona-sound-visual">
      <div ref={barRef} className="persona-genre-ribbon" aria-label="Top sound clusters">
        {visibleSegments.map((segment, index) => (
          <motion.span
            key={segment.label}
            className="persona-genre-ribbon__segment"
            initial={reducedMotion ? { flexBasis: `${segment.value}%` } : { flexBasis: "0%" }}
            animate={reducedMotion || barInView ? { flexBasis: `${segment.value}%` } : { flexBasis: "0%" }}
            transition={{ duration: 0.82, delay: index * 0.08, ease: [0.22, 1, 0.36, 1] }}
            style={{ backgroundColor: segment.color }}
            title={`${segment.label}: ${formatShare(segment.value)}`}
            aria-label={`${segment.label}: ${formatShare(segment.value)}`}
          />
        ))}
      </div>
      <div className="persona-genre-list">
        {visibleSegments.slice(0, 5).map((segment) => (
          <span key={segment.label}>
            <i style={{ backgroundColor: segment.color }} aria-hidden="true" />
            {segment.label}
            <strong>
              <CountUp to={segment.value} duration={0.9} separator="" />%
            </strong>
          </span>
        ))}
      </div>
      {traits.length ? <p className="persona-trait-line">{traits.join(" / ")}</p> : null}
    </div>
  );
}

function ComfortVisual({
  repeatScore,
  discoveryScore,
  topAlbum,
  source,
}: {
  repeatScore: number;
  discoveryScore: number;
  topAlbum: TopAlbumItem | null;
  source: MusicSource;
}) {
  return (
    <div className="persona-comfort-visual">
      <div className="persona-main-number">
        <span>Repeat score</span>
        <strong>
          <CountUp to={Math.round(repeatScore)} duration={0.9} separator="" />
        </strong>
      </div>
      <div className="persona-meter-list">
        <MiniMeter label="Repeat" value={repeatScore} />
        <MiniMeter label="Discovery" value={discoveryScore} />
      </div>
      {topAlbum ? (
        <div className="persona-album-signal">
          {topAlbum.album_image_url ? (
            <AlbumCover albumImageUrl={topAlbum.album_image_url} albumTitle={topAlbum.album} size="hero" />
          ) : null}
          <div>
            <span>Most revisited album signal</span>
            <strong>{topAlbum.album}</strong>
            <p>
              {topAlbum.plays.toLocaleString()} {source === "spotify" ? "signals" : "plays"} / {topAlbum.unique_songs.toLocaleString()} songs
            </p>
          </div>
        </div>
      ) : null}
    </div>
  );
}

function MiniMeter({ label, value }: { label: string; value: number }) {
  return (
    <div className="persona-meter">
      <div>
        <span>{label}</span>
        <strong>{Math.round(value)}</strong>
      </div>
      <i aria-hidden="true">
        <b style={{ width: `${Math.max(0, Math.min(value, 100))}%` }} />
      </i>
    </div>
  );
}

function MainCharactersVisual({ characters, topArtists, source }: { characters: PersonaMainCharacter[]; topArtists: TopArtist[]; source: MusicSource }) {
  const fallback = topArtists.slice(0, 3).map((artist, index) => ({
    artistName: artist.artist,
    role: index === 0 ? "The emotional anchor" : index === 1 ? "The recurring atmosphere" : "The reliable wildcard",
    line: artist.why_it_matters || artist.artist_loyalty_label,
  }));
  const visibleCharacters = (characters.length ? characters : fallback).slice(0, 3);

  return (
    <div className="persona-artist-cast">
      {visibleCharacters.map((character, index) => {
        const artist = findArtist(topArtists, character.artistName);
        return (
          <StoryReveal key={character.artistName} delay={index * 0.1} distance={30}>
            <article className="persona-artist-cast__item">
              <ArtistAvatar artistImageUrl={artist?.artist_image_url} artistName={character.artistName} size="hero" shape="rounded" fallbackLabel={initials(character.artistName)} />
              <div>
                <p>{character.role}</p>
                <h3>{character.artistName}</h3>
                <span>{artistMetric(artist, source)}</span>
                <small>{character.line}</small>
              </div>
            </article>
          </StoryReveal>
        );
      })}
    </div>
  );
}

function PlotTwistVisual({ rollingName, rollingCharacter, currentCharacter }: { rollingName: string; rollingCharacter: MusicCharacterResponse | null; currentCharacter: MusicCharacterResponse | null }) {
  const currentName = currentCharacter?.primary.name ?? "Current phase";
  const hasContrast = Boolean(rollingCharacter && currentCharacter && rollingCharacter.primary.id !== currentCharacter.primary.id);
  const sideSignals = rollingCharacter?.top_clusters.slice(1, 3).map((item) => item.name) ?? [];

  return (
    <div className="persona-plot-visual" data-contrast={hasContrast ? "true" : "false"}>
      <div>
        <span>Rolling year</span>
        <strong>{rollingName}</strong>
      </div>
      <em>{hasContrast ? "meets" : "echoes"}</em>
      <div>
        <span>{hasContrast ? "Current month" : "Side signal"}</span>
        <strong>{hasContrast ? currentName : sideSignals.join(" / ") || "Unusually consistent"}</strong>
      </div>
    </div>
  );
}

function ClosingVisual({ finalLine }: { finalLine: string }) {
  return (
    <div className="persona-closing-visual">
      <span>End credits</span>
      <p>{finalLine}</p>
    </div>
  );
}
