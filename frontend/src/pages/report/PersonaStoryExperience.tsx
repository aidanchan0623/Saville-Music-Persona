import { Sparkles } from "lucide-react";
import { useMemo, useRef } from "react";
import type { CSSProperties, ReactNode } from "react";
import { motion, useInView, useReducedMotion, useScroll, useSpring, useTransform } from "motion/react";
import { AlbumCover, ArtistAvatar } from "../../components/Artwork";
import type { MusicCharacterResponse, MusicSource, PersonaMainCharacter, TopAlbumItem, TopArtist } from "../../types/api";
import { PersonaAlbumDome } from "./PersonaAlbumDome";
import {
  artistMetric,
  buildAlbumDomeItems,
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
  prerequisitesModelReady: boolean;
  busy: boolean;
  onGenerate: (mode: GenerateMode) => void;
  source: MusicSource;
  titleAnimationKey: string;
};

const STORY_SPRING = { stiffness: 82, damping: 28, mass: 0.45 };
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
  prerequisitesModelReady,
  busy,
  onGenerate,
  source,
  titleAnimationKey,
}: PersonaStoryExperienceProps) {
  const storyRef = useRef<HTMLDivElement | null>(null);
  const reducedMotion = useReducedMotion();
  const { scrollYProgress } = useScroll({ target: storyRef, offset: ["start start", "end end"] });
  const smoothProgress = useSpring(scrollYProgress, STORY_SPRING);
  const domeAlbums = useMemo(() => buildAlbumDomeItems(favouriteAlbums), [favouriteAlbums]);
  const genreSegments = useMemo(() => buildGenreSegments(rollingCharacter), [rollingCharacter]);
  const topAlbum = favouriteAlbums.find((album) => album.album_image_url) ?? favouriteAlbums[0] ?? null;
  const repeatScore = scoreValue(rollingCharacter, "repeat");
  const discoveryScore = scoreValue(rollingCharacter, "discovery");
  const dominantSound = rollingCharacter?.top_clusters[0]?.name ?? genreSegments[0]?.label ?? "Your strongest sound-world";
  const traits = rollingCharacter?.sonic_traits.slice(0, 5) ?? [];

  const progressScale = reducedMotion ? scrollYProgress : smoothProgress;
  const domeY = useTransform(smoothProgress, [0, 0.3, 0.52, 0.78, 1], ["0vh", "-8vh", "-17vh", "-8vh", "2vh"]);
  const domeScale = useTransform(smoothProgress, [0, 0.3, 0.54, 0.76, 1], [1, 0.94, 0.82, 0.75, 0.9]);
  const domeOpacity = useTransform(smoothProgress, [0, 0.22, 0.42, 0.65, 0.88, 1], [0.72, 0.58, 0.25, 0.16, 0.28, 0.44]);
  const storyTone = useTransform(smoothProgress, [0, 0.28, 0.52, 0.74, 1], ["#090607", "#120608", "#070607", "#100608", "#080607"]);

  return (
    <div className="persona-report">
      <header className="persona-report__masthead" aria-label="Persona report controls">
        <div>
          <p className="persona-report__eyebrow">Persona Report</p>
          <p className="persona-report__meta">
            {story.sourceLabel}
            {!prerequisitesModelReady ? " / Gemma offline fallback available" : ""}
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

      <article ref={storyRef} className="persona-story" aria-label="Persona story report">
        <motion.div className="persona-story__tone" aria-hidden="true" style={reducedMotion ? undefined : { backgroundColor: storyTone }} />
        {domeAlbums.length ? (
          <div className="persona-story__album-field" aria-hidden="true">
            <div className="persona-story__album-sticky">
              <PersonaAlbumDome
                items={domeAlbums}
                priority
                style={reducedMotion ? { opacity: 0.34 } : { y: domeY, scale: domeScale, opacity: domeOpacity }}
              />
            </div>
          </div>
        ) : null}
        <motion.div className="persona-story-progress" aria-hidden="true" style={{ scaleY: progressScale }} />

        <OpeningSection
          story={story}
          dominantSound={dominantSound}
          traits={traits}
          titleAnimationKey={titleAnimationKey}
        />

        <EditorialSection
          id="core"
          label="Core Sound"
          headline={story.coreSound.headline}
          body={story.coreSound.body}
          pullQuote={story.coreSound.pullQuote}
          variant="core"
        >
          <CoreSoundVisual segments={genreSegments} traits={traits} />
        </EditorialSection>

        <EditorialSection
          id="comfort"
          label="Comfort Loop"
          headline={story.comfortLoop.headline}
          body={story.comfortLoop.body}
          pullQuote={story.comfortLoop.pullQuote}
          variant="comfort"
          reversed
        >
          <ComfortVisual repeatScore={repeatScore} discoveryScore={discoveryScore} topAlbum={topAlbum} />
        </EditorialSection>

        <EditorialSection
          id="characters"
          label="Main Characters"
          headline="The Names That Hold The Frame"
          body="These are not just top-list names. They are the recurring faces that give the story continuity, tension, and recognizable gravity."
          variant="characters"
        >
          <MainCharactersVisual characters={story.mainCharacters} topArtists={topArtists} source={source} />
        </EditorialSection>

        <EditorialSection
          id="twist"
          label="Plot Twist"
          headline={story.plotTwist.headline}
          body={story.plotTwist.body}
          variant="twist"
          reversed
        >
          <PlotTwistVisual rollingCharacter={rollingCharacter} currentCharacter={currentCharacter} />
        </EditorialSection>

        <EditorialSection
          id="closing"
          label="Closing Credits"
          headline={story.closing.headline}
          body={story.closing.body}
          pullQuote={story.closing.finalLine}
          variant="closing"
        >
          <ClosingVisual finalLine={story.closing.finalLine} />
        </EditorialSection>
      </article>
    </div>
  );
}

function OpeningSection({
  story,
  dominantSound,
  traits,
  titleAnimationKey,
}: {
  story: PersonaStory;
  dominantSound: string;
  traits: string[];
  titleAnimationKey: string;
}) {
  const sectionRef = useRef<HTMLElement | null>(null);
  const reducedMotion = useReducedMotion();
  const isInView = useInView(sectionRef, { amount: 0.36, margin: "-8% 0px -18% 0px" });
  const { scrollYProgress } = useScroll({ target: sectionRef, offset: ["start start", "end start"] });
  const copyY = useSpring(useTransform(scrollYProgress, [0, 1], [0, -34]), STORY_SPRING);
  const visualY = useSpring(useTransform(scrollYProgress, [0, 1], [24, -28]), STORY_SPRING);
  const copyOpacity = useTransform(scrollYProgress, [0, 0.72, 1], [1, 0.9, 0.48]);

  return (
    <section
      ref={sectionRef}
      id="persona-opening"
      className="persona-section persona-section--opening"
      aria-labelledby="persona-opening-title"
      data-in-view={isInView ? "true" : "false"}
    >
      <motion.div className="persona-section__copy persona-section__copy--opening" style={reducedMotion ? undefined : { y: copyY, opacity: copyOpacity }}>
        <p className="persona-section__label">Your Music Persona</p>
        <h1 id="persona-opening-title" key={titleAnimationKey}>
          {story.personaName}
        </h1>
        <MotionReveal className="persona-opening-hook">
          <p>{story.openingHook}</p>
        </MotionReveal>
        <div className="persona-opening-signal">
          <span>Dominant sound</span>
          <strong>{dominantSound}</strong>
        </div>
        <p className="persona-scroll-cue">Scroll to enter your listening story</p>
      </motion.div>
      <motion.aside className="persona-opening-atmosphere" aria-label="Opening sound details" style={reducedMotion ? undefined : { y: visualY }}>
        <span>Sound weather</span>
        <strong>{dominantSound}</strong>
        {traits.length ? <p>{traits.join(" / ")}</p> : null}
      </motion.aside>
    </section>
  );
}

type EditorialSectionProps = {
  id: string;
  label: string;
  headline: string;
  body: string;
  pullQuote?: string;
  children: ReactNode;
  variant: string;
  reversed?: boolean;
};

function EditorialSection({ id, label, headline, body, pullQuote, children, variant, reversed = false }: EditorialSectionProps) {
  const sectionRef = useRef<HTMLElement | null>(null);
  const reducedMotion = useReducedMotion();
  const isInView = useInView(sectionRef, { amount: 0.32, margin: "-12% 0px -18% 0px" });
  const { scrollYProgress } = useScroll({ target: sectionRef, offset: ["start end", "end start"] });
  const copyY = useSpring(useTransform(scrollYProgress, [0, 0.34, 0.78, 1], [36, 0, -8, -24]), STORY_SPRING);
  const copyOpacity = useTransform(scrollYProgress, [0, 0.2, 0.72, 1], [0.34, 1, 1, 0.55]);
  const visualScale = useSpring(useTransform(scrollYProgress, [0, 0.38, 0.82, 1], [0.95, 1, 1, 0.98]), STORY_SPRING);

  return (
    <section
      ref={sectionRef}
      id={`persona-${id}`}
      className={`persona-section persona-section--${variant}${reversed ? " persona-section--reversed" : ""}`}
      aria-labelledby={`persona-${id}-title`}
      data-in-view={isInView ? "true" : "false"}
    >
      <motion.div className="persona-section__copy" style={reducedMotion ? undefined : { y: copyY, opacity: copyOpacity }}>
        <p className="persona-section__label">{label}</p>
        <MotionReveal>
          <h2 id={`persona-${id}-title`}>{headline}</h2>
        </MotionReveal>
        <p className="persona-section__body">{body}</p>
        {pullQuote ? (
          <MotionReveal className="persona-section__quote">
            <blockquote>{pullQuote}</blockquote>
          </MotionReveal>
        ) : null}
      </motion.div>
      <motion.div className="persona-section__visual" style={reducedMotion ? undefined : { scale: visualScale }}>
        {children}
      </motion.div>
    </section>
  );
}

function MotionReveal({ children, className = "" }: { children: ReactNode; className?: string }) {
  const reducedMotion = useReducedMotion();

  if (reducedMotion) {
    return <div className={className}>{children}</div>;
  }

  return (
    <motion.div
      className={className}
      initial={{ opacity: 0, y: 24 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, amount: 0.42 }}
      transition={{ duration: 0.72, ease: [0.22, 1, 0.36, 1] }}
    >
      {children}
    </motion.div>
  );
}

function CoreSoundVisual({ segments, traits }: { segments: GenreSegment[]; traits: string[] }) {
  const visibleSegments = segments.length ? segments : [{ label: "Signal forming", value: 100, color: "#343036" }];

  return (
    <div className="persona-sound-visual">
      <div className="persona-genre-ribbon" aria-label="Top sound clusters">
        {visibleSegments.map((segment, index) => (
          <span
            key={segment.label}
            className="persona-genre-ribbon__segment"
            style={
              {
                "--segment-share": `${segment.value}%`,
                "--segment-color": segment.color,
                "--segment-delay": `${index * 90}ms`,
              } as CSSProperties
            }
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
            <strong>{formatShare(segment.value)}</strong>
          </span>
        ))}
      </div>
      {traits.length ? <p className="persona-trait-line">{traits.join(" / ")}</p> : null}
    </div>
  );
}

function ComfortVisual({ repeatScore, discoveryScore, topAlbum }: { repeatScore: number; discoveryScore: number; topAlbum: TopAlbumItem | null }) {
  return (
    <div className="persona-comfort-visual">
      <div className="persona-main-number">
        <span>Repeat score</span>
        <strong>{Math.round(repeatScore)}</strong>
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
              {topAlbum.plays} plays / {topAlbum.unique_songs} songs
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
          <article key={character.artistName} className="persona-artist-cast__item" style={{ "--artist-offset": `${index * 2.8}rem` } as CSSProperties}>
            <ArtistAvatar artistImageUrl={artist?.artist_image_url} artistName={character.artistName} size="hero" shape="rounded" fallbackLabel={initials(character.artistName)} />
            <div>
              <p>{character.role}</p>
              <h3>{character.artistName}</h3>
              <span>{artistMetric(artist, source)}</span>
              <small>{character.line}</small>
            </div>
          </article>
        );
      })}
    </div>
  );
}

function PlotTwistVisual({ rollingCharacter, currentCharacter }: { rollingCharacter: MusicCharacterResponse | null; currentCharacter: MusicCharacterResponse | null }) {
  const rollingName = rollingCharacter?.primary.name ?? "Long-term character";
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
