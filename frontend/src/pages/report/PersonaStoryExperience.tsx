import { ArrowDown, ChevronLeft, ChevronRight, RotateCcw, Sparkles } from "lucide-react";
import { forwardRef, useEffect, useMemo, useRef, useState } from "react";
import type { CSSProperties, ReactNode } from "react";
import { ArtistAvatar } from "../../components/Artwork";
import { OrbitImages } from "../../components/reactbits/OrbitImages/OrbitImages";
import type { OrbitImageItem } from "../../components/reactbits/OrbitImages/OrbitImages";
import { ScrollReveal } from "../../components/reactbits/ScrollReveal/ScrollReveal";
import { ScrollStack, ScrollStackItem } from "../../components/reactbits/ScrollStack/ScrollStack";
import type { MusicCharacterResponse, MusicSource, PersonaMainCharacter, TopAlbumItem, TopArtist } from "../../types/api";
import {
  artistMetric,
  buildGenreSegments,
  buildOrbitAlbums,
  findArtist,
  formatShare,
  initials,
  scoreValue,
} from "./personaStoryModel";
import type { GenreSegment, PersonaStory } from "./personaStoryModel";

const CHAPTERS = [
  { id: "opening", label: "Opening", title: "Your Musical Character" },
  { id: "core", label: "Core Sound", title: "Where Your Taste Lives" },
  { id: "comfort", label: "Comfort Loop", title: "What You Return To" },
  { id: "characters", label: "Main Characters", title: "Your Anchor Artists" },
  { id: "twist", label: "Plot Twist", title: "Discovery and Unexpected Signals" },
  { id: "closing", label: "Closing Credits", title: "Final Persona Summary" },
] as const;

type PersonaStoryExperienceProps = {
  story: PersonaStory;
  rollingCharacter: MusicCharacterResponse | null;
  currentCharacter: MusicCharacterResponse | null;
  favouriteAlbums: TopAlbumItem[];
  topArtists: TopArtist[];
  prerequisitesModelReady: boolean;
  busy: boolean;
  onGenerate: (mode: "serious" | "playful" | "roast") => void;
  source: MusicSource;
  titleAnimationKey: string;
};

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
  const [activeChapter, setActiveChapter] = useState(0);
  const chapterRefs = useRef<(HTMLElement | null)[]>([]);
  const orbitAlbums = useMemo(() => buildOrbitAlbums(favouriteAlbums), [favouriteAlbums]);
  const genreSegments = useMemo(() => buildGenreSegments(rollingCharacter), [rollingCharacter]);
  const topAlbum = favouriteAlbums.find((album) => album.album_image_url) ?? favouriteAlbums[0] ?? null;

  useEffect(() => {
    const nodes = chapterRefs.current.filter(Boolean) as HTMLElement[];
    if (!nodes.length) return;
    const updateActiveChapter = () => {
      const probeY = window.scrollY + window.innerHeight * 0.38;
      let nextActive = 0;
      nodes.forEach((node, index) => {
        if (node.offsetTop <= probeY) nextActive = index;
      });
      setActiveChapter(nextActive);
    };
    const observer = new IntersectionObserver(
      () => updateActiveChapter(),
      { threshold: [0.34, 0.5, 0.66], rootMargin: "-18% 0px -45% 0px" },
    );
    nodes.forEach((node) => observer.observe(node));
    window.addEventListener("scroll", updateActiveChapter, { passive: true });
    updateActiveChapter();
    return () => {
      observer.disconnect();
      window.removeEventListener("scroll", updateActiveChapter);
    };
  }, [story]);

  const scrollToChapter = (index: number) => {
    const next = Math.max(0, Math.min(CHAPTERS.length - 1, index));
    const node = chapterRefs.current[next];
    if (!node) return;
    const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    node.scrollIntoView({ behavior: reducedMotion ? "auto" : "smooth", block: "start" });
  };

  const repeatScore = scoreValue(rollingCharacter, "repeat");
  const discoveryScore = scoreValue(rollingCharacter, "discovery");
  const dominantSound = rollingCharacter?.top_clusters[0]?.name ?? genreSegments[0]?.label ?? "Your strongest sound-world";
  const traits = rollingCharacter?.sonic_traits.slice(0, 5) ?? [];

  return (
    <div className="persona-report">
      <header className="persona-report__masthead">
        <div>
          <p className="persona-report__eyebrow">Persona Report</p>
          <h1 key={titleAnimationKey}>{story.personaName}</h1>
          <p className="persona-report__hook">{story.openingHook}</p>
          <p className="persona-report__meta">
            {story.sourceLabel}
            {!prerequisitesModelReady ? " / Gemma offline fallback available" : ""}
          </p>
        </div>
        <div className="persona-report__actions" aria-label="Generate persona report">
          <button className="btn-secondary" disabled={busy} onClick={() => onGenerate("serious")}>
            <Sparkles size={16} /> Generate Story
          </button>
          <button className="btn-secondary" disabled={busy} onClick={() => onGenerate("playful")}>Playful</button>
          <button className="btn-secondary" disabled={busy} onClick={() => onGenerate("roast")}>Light Roast</button>
        </div>
      </header>

      <PersonaStoryNavigation activeChapter={activeChapter} busy={busy} onNavigate={scrollToChapter} />

      <ScrollStack className="persona-story" aria-label="Persona story chapters">
        <PersonaChapter
          ref={(node) => {
            chapterRefs.current[0] = node;
          }}
          chapterIndex={0}
          label="Your Music Persona"
          headline={story.personaName}
          body={story.openingHook}
          pullQuote={dominantSound}
          orbitAlbums={orbitAlbums}
          orbitActive={activeChapter === 0}
          orbitPriority
          visual={<OpeningVisual dominantSound={dominantSound} traits={traits} onNext={() => scrollToChapter(1)} />}
        />

        <PersonaChapter
          ref={(node) => {
            chapterRefs.current[1] = node;
          }}
          chapterIndex={1}
          label="Core Sound"
          headline={story.coreSound.headline}
          body={story.coreSound.body}
          pullQuote={story.coreSound.pullQuote}
          visual={<CoreSoundVisual segments={genreSegments} traits={traits} />}
        />

        <PersonaChapter
          ref={(node) => {
            chapterRefs.current[2] = node;
          }}
          chapterIndex={2}
          label="The Comfort Loop"
          headline={story.comfortLoop.headline}
          body={story.comfortLoop.body}
          pullQuote={story.comfortLoop.pullQuote}
          orbitAlbums={orbitAlbums}
          orbitActive={activeChapter === 2}
          visual={<ComfortVisual repeatScore={repeatScore} discoveryScore={discoveryScore} topAlbum={topAlbum} />}
        />

        <PersonaChapter
          ref={(node) => {
            chapterRefs.current[3] = node;
          }}
          chapterIndex={3}
          label="Main Characters"
          headline="The Names That Hold The Frame"
          body="These are not just top-list names. They are the recurring faces that give the story continuity, tension, and recognizable gravity."
          visual={<MainCharactersVisual characters={story.mainCharacters} topArtists={topArtists} source={source} />}
        />

        <PersonaChapter
          ref={(node) => {
            chapterRefs.current[4] = node;
          }}
          chapterIndex={4}
          label="The Plot Twist"
          headline={story.plotTwist.headline}
          body={story.plotTwist.body}
          visual={<PlotTwistVisual rollingCharacter={rollingCharacter} currentCharacter={currentCharacter} />}
        />

        <PersonaChapter
          ref={(node) => {
            chapterRefs.current[5] = node;
          }}
          chapterIndex={5}
          label="Closing Credits"
          headline={story.closing.headline}
          body={story.closing.body}
          pullQuote={story.closing.finalLine}
          orbitAlbums={orbitAlbums}
          orbitActive={activeChapter === 5}
          visual={<ClosingVisual finalLine={story.closing.finalLine} onRestart={() => scrollToChapter(0)} />}
        />
      </ScrollStack>
    </div>
  );
}

type PersonaChapterProps = {
  chapterIndex: number;
  label: string;
  headline: string;
  body: string;
  pullQuote?: string;
  visual: ReactNode;
  orbitAlbums?: OrbitImageItem[];
  orbitActive?: boolean;
  orbitPriority?: boolean;
};

const PersonaChapter = forwardRef<HTMLElement, PersonaChapterProps>(function PersonaChapter(
  { chapterIndex, label, headline, body, pullQuote, visual, orbitAlbums, orbitActive, orbitPriority },
  ref,
) {
  return (
    <ScrollStackItem ref={ref} id={`persona-${CHAPTERS[chapterIndex].id}`} data-chapter-index={chapterIndex}>
      <article className="persona-chapter">
        {orbitAlbums?.length ? <AlbumOrbitBackground albums={orbitAlbums} active={orbitActive} priority={orbitPriority} /> : null}
        <div className="persona-chapter__shade" aria-hidden="true" />
        <div className="persona-chapter__copy">
          <p className="persona-chapter__label">{label}</p>
          <ScrollReveal>
            <h2>{headline}</h2>
          </ScrollReveal>
          <p className="persona-chapter__body">{body}</p>
          {pullQuote ? (
            <ScrollReveal className="persona-chapter__quote">
              <blockquote>{pullQuote}</blockquote>
            </ScrollReveal>
          ) : null}
        </div>
        <div className="persona-chapter__visual">{visual}</div>
      </article>
    </ScrollStackItem>
  );
});

function PersonaStoryNavigation({ activeChapter, busy, onNavigate }: { activeChapter: number; busy: boolean; onNavigate: (index: number) => void }) {
  return (
    <nav className="persona-story-nav" aria-label="Persona story navigation">
      <button className="persona-story-nav__button" type="button" disabled={activeChapter === 0 || busy} onClick={() => onNavigate(activeChapter - 1)} aria-label="Go to previous persona chapter">
        <ChevronLeft size={16} /> Previous
      </button>
      <div className="persona-story-nav__chapters" role="list" aria-label="Persona chapters">
        {CHAPTERS.map((chapter, index) => (
          <button
            key={chapter.id}
            type="button"
            className={`persona-story-nav__dot${activeChapter === index ? " persona-story-nav__dot--active" : ""}`}
            aria-label={`Go to ${chapter.label}: ${chapter.title}`}
            aria-current={activeChapter === index ? "step" : undefined}
            onClick={() => onNavigate(index)}
          >
            <span>{index + 1}</span>
          </button>
        ))}
      </div>
      <button className="persona-story-nav__button" type="button" disabled={activeChapter === CHAPTERS.length - 1 || busy} onClick={() => onNavigate(activeChapter + 1)} aria-label="Go to next persona chapter">
        Next <ChevronRight size={16} />
      </button>
      <button className="persona-story-nav__restart" type="button" disabled={busy} onClick={() => onNavigate(0)} aria-label="Restart persona story">
        <RotateCcw size={16} /> Restart Story
      </button>
    </nav>
  );
}

function OpeningVisual({ dominantSound, traits, onNext }: { dominantSound: string; traits: string[]; onNext: () => void }) {
  return (
    <div className="persona-opening-visual">
      <p>Dominant sound</p>
      <strong>{dominantSound}</strong>
      {traits.length ? <span>{traits.slice(0, 5).join(" / ")}</span> : null}
      <button type="button" className="persona-scroll-cue" onClick={onNext} aria-label="Continue to Core Sound chapter">
        Continue the story <ArrowDown size={16} />
      </button>
    </div>
  );
}

function CoreSoundVisual({ segments, traits }: { segments: GenreSegment[]; traits: string[] }) {
  return (
    <div className="persona-sound-visual">
      <div className="persona-genre-stack" aria-label="Top sound clusters">
        {segments.map((segment, index) => (
          <span
            key={segment.label}
            className="persona-genre-stack__segment"
            style={
              {
                "--segment-share": `${segment.value}%`,
                "--segment-color": segment.color,
                "--segment-delay": `${index * 80}ms`,
              } as CSSProperties
            }
            title={`${segment.label}: ${formatShare(segment.value)}`}
            aria-label={`${segment.label}: ${formatShare(segment.value)}`}
          />
        ))}
      </div>
      <div className="persona-genre-stack__legend">
        {segments.map((segment) => (
          <span key={segment.label}>
            <i style={{ backgroundColor: segment.color }} aria-hidden="true" />
            {segment.label}
            <strong>{formatShare(segment.value)}</strong>
          </span>
        ))}
      </div>
      {traits.length ? <p className="persona-trait-line">{traits.slice(0, 5).join(" / ")}</p> : null}
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
          <span>Most revisited album signal</span>
          <strong>{topAlbum.album}</strong>
          <p>
            {topAlbum.plays} plays / {topAlbum.unique_songs} songs
          </p>
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
  const visibleCharacters = characters.length ? characters : fallback;

  return (
    <div className="persona-artist-cast">
      {visibleCharacters.slice(0, 3).map((character) => {
        const artist = findArtist(topArtists, character.artistName);
        return (
          <article key={character.artistName} className="persona-artist-cast__item">
            <ArtistAvatar artistImageUrl={artist?.artist_image_url} artistName={character.artistName} size="lg" fallbackLabel={initials(character.artistName)} />
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
      <div>
        <span>{hasContrast ? "Current month" : "Side signal"}</span>
        <strong>{hasContrast ? currentName : sideSignals.join(" / ") || "Unusually consistent"}</strong>
      </div>
    </div>
  );
}

function ClosingVisual({ finalLine, onRestart }: { finalLine: string; onRestart: () => void }) {
  return (
    <div className="persona-closing-visual">
      <ScrollReveal>
        <p>{finalLine}</p>
      </ScrollReveal>
      <button type="button" className="btn-primary" onClick={onRestart}>
        <RotateCcw size={16} /> Restart Story
      </button>
    </div>
  );
}

function AlbumOrbitBackground({ albums, active, priority }: { albums: OrbitImageItem[]; active?: boolean; priority?: boolean }) {
  return (
    <div className="persona-album-orbit">
      <OrbitImages items={albums} active={active} priority={priority} />
    </div>
  );
}
