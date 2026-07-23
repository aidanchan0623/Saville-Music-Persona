import { useMemo, useRef } from "react";
import { motion, useInView, useReducedMotion, useScroll, useSpring, useTransform } from "motion/react";
import { AlbumCover, ArtistAvatar } from "../../components/Artwork";
import type { PersonaGenre, PersonaReport } from "../../types/api";
import { PersonaAlbumDome } from "./PersonaAlbumDome";

interface Props {
  report: PersonaReport;
  modelReady: boolean;
  busy: boolean;
  onGenerate: (mode: "serious" | "playful" | "roast") => void;
  titleAnimationKey: string;
}

export function PersonaStoryExperience({ report, modelReady, busy, onGenerate, titleAnimationKey }: Props) {
  const rootRef = useRef<HTMLDivElement | null>(null);
  const { scrollYProgress } = useScroll({ target: rootRef, offset: ["start start", "end end"] });
  const progress = useSpring(scrollYProgress, { stiffness: 82, damping: 24, mass: 0.35 });
  const albumList = useMemo(() => report.backgroundAlbums, [report.backgroundAlbums]);

  return (
    <div ref={rootRef} className="persona-report-page">
      <PersonaAlbumDome albums={albumList} progress={progress} />
      <div className="persona-report-scrim" aria-hidden="true" />
      <main className="persona-scroll-story">
        <header className="persona-report__masthead">
          <div>
            <p className="persona-report__eyebrow">Persona Report</p>
            <p className="persona-report__meta">{report.period.label} &middot; {report.period.timezone}</p>
          </div>
          <div className="persona-report__actions" aria-label="Report writing tone">
            {(["serious", "playful", "roast"] as const).map((mode) => (
              <button key={mode} type="button" disabled={busy || !modelReady} className={report.mode === mode ? "persona-tone persona-tone--active" : "persona-tone"} onClick={() => onGenerate(mode)}>
                {busy && report.mode === mode ? "Writing..." : mode}
              </button>
            ))}
          </div>
        </header>

        <PersonalityScene report={report} titleAnimationKey={titleAnimationKey} />
        <ListeningWorldScene report={report} />
        <MusicalAgeScene report={report} />
        <TopFiveScene report={report} />
        <FinalRoastScene report={report} />

        <footer className="persona-report-footer">
          <strong>{report.personality.title}</strong>
          <span>Musical age {report.musicalAge.age}</span>
          <span>Top artist {report.topFive.artists[0]?.name || "Still forming"}</span>
        </footer>
      </main>
    </div>
  );
}

function PersonalityScene({ report, titleAnimationKey }: { report: PersonaReport; titleAnimationKey: string }) {
  const sceneRef = useRef<HTMLElement | null>(null);
  const reduced = useReducedMotion();
  const { scrollYProgress } = useScroll({ target: sceneRef, offset: ["start start", "end start"] });
  const scale = useTransform(scrollYProgress, [0, 0.72, 1], [1, 0.82, 0.72]);
  const x = useTransform(scrollYProgress, [0, 1], [0, -90]);
  return (
    <section ref={sceneRef} className="persona-scene-track persona-scene-track--opening" aria-labelledby="personality-title">
      <motion.div className="persona-scene-sticky persona-scene-sticky--center" style={reduced ? undefined : { scale, x }}>
        <div className="persona-text-scrim persona-opening-copy">
          <p className="persona-chapter-label">Your Musical Personality</p>
          <h1 id="personality-title" key={titleAnimationKey}>{report.personality.title}</h1>
          <p className="persona-lede">{report.personality.shortDescription}</p>
          <p className="persona-personality-roast">{report.personality.roastDescription}</p>
          <span className="persona-period-pill">{report.period.label}</span>
          <small className="persona-scroll-cue">Scroll to enter your listening world</small>
        </div>
      </motion.div>
    </section>
  );
}

function ListeningWorldScene({ report }: { report: PersonaReport }) {
  return (
    <RevealScene id="listening-world" direction="right" className="persona-listening-scene">
      <div className="persona-scene-grid">
        <div className="persona-text-scrim">
          <p className="persona-chapter-label">Your Listening World</p>
          <h2 id="listening-world-title">{report.listeningWorld.formattedTime} detected</h2>
          <p className="persona-period-line">{report.period.label}</p>
          <p className="persona-body">{report.listeningWorld.interpretation}</p>
          <div className="persona-coverage-line">
            <span>Duration coverage <strong>{formatPercent(report.listeningWorld.durationCoverage)}</strong></span>
            <span>Genre coverage <strong>{formatPercent(report.listeningWorld.genreCoverage)}</strong></span>
          </div>
        </div>
        <GenreComposition genres={report.listeningWorld.genres} />
      </div>
    </RevealScene>
  );
}

function GenreComposition({ genres }: { genres: PersonaGenre[] }) {
  const ref = useRef<HTMLDivElement | null>(null);
  const inView = useInView(ref, { once: true, amount: 0.35 });
  const reduced = useReducedMotion();
  const colors = ["#f04b52", "#d83665", "#b5507f", "#8b5c96", "#5c6d9c", "#3f6578", "#47474f"];
  return (
    <div ref={ref} className="persona-genre-composition" aria-label="Genre family shares">
      <div className="persona-genre-bar">
        {genres.map((genre, index) => (
          <motion.span key={genre.key} title={`${genre.label}: ${genre.percentage}%`} initial={reduced ? false : { scaleX: 0 }} animate={reduced || inView ? { scaleX: 1 } : { scaleX: 0 }} transition={{ duration: 0.78, delay: index * 0.06 }} style={{ width: `${genre.percentage}%`, backgroundColor: colors[index % colors.length], transformOrigin: "left" }} />
        ))}
      </div>
      <ol className="persona-genre-list">
        {genres.map((genre, index) => (
          <li key={genre.key}><i style={{ backgroundColor: colors[index % colors.length] }} /><span>{genre.label}</span><strong>{genre.percentage.toFixed(1)}%</strong></li>
        ))}
      </ol>
    </div>
  );
}

function MusicalAgeScene({ report }: { report: PersonaReport }) {
  return (
    <RevealScene id="musical-age" direction="zoom" className="persona-age-scene">
      <div className="persona-age-orbit" aria-hidden="true" />
      <div className="persona-text-scrim persona-age-copy">
        <p className="persona-chapter-label">Musical Age</p>
        <p className="persona-age-number">{report.musicalAge.age}</p>
        <h2 id="musical-age-title">{report.musicalAge.title}</h2>
        <div className="persona-age-facts">
          <span>Likely range <strong>{report.musicalAge.likelyMin}-{report.musicalAge.likelyMax}</strong></span>
          <span>{report.musicalAge.confidenceLabel}</span>
        </div>
        <p className="persona-body">{report.musicalAge.explanation}</p>
        <p className="persona-period-line">Source: {report.musicalAge.sourcePeriod.label}</p>
      </div>
    </RevealScene>
  );
}

function TopFiveScene({ report }: { report: PersonaReport }) {
  const ref = useRef<HTMLElement | null>(null);
  const reduced = useReducedMotion();
  const { scrollYProgress } = useScroll({ target: ref, offset: ["start start", "end end"] });
  const x = useTransform(scrollYProgress, [0.12, 0.78], ["0%", "-50%"]);
  return (
    <section ref={ref} className="persona-scene-track persona-scene-track--rankings" aria-labelledby="top-five-title">
      <div className="persona-scene-sticky persona-ranking-viewport">
        <h2 id="top-five-title" className="sr-only">Top Artists and Songs</h2>
        <motion.div className="persona-ranking-panels" style={reduced ? undefined : { x }}>
          <RankingPanel title="Top Artists" period={report.period.label} side="artists">
            {report.topFive.artists.map((artist, index) => (
              <motion.article className="persona-ranking-row persona-ranking-row--artist" key={artist.name} initial={reduced ? false : { opacity: 0, x: 50 }} whileInView={{ opacity: 1, x: 0 }} viewport={{ once: true }} transition={{ delay: index * 0.07 }}>
                <span className="persona-rank">{artist.rank.toString().padStart(2, "0")}</span>
                <ArtistAvatar artistImageUrl={artist.artistImageUrl} artistName={artist.name} size={index === 0 ? "hero" : "lg"} shape="rounded" priority={index < 2} />
                <div><h3>{artist.name}</h3><p>{artist.detectedPlays.toLocaleString()} detected plays &middot; {artist.uniqueSongs} songs</p></div>
              </motion.article>
            ))}
          </RankingPanel>
          <RankingPanel title="Top Songs" period={report.period.label} side="songs">
            {report.topFive.songs.map((song, index) => (
              <motion.article className="persona-ranking-row persona-ranking-row--song" key={`${song.title}-${song.artist}`} initial={reduced ? false : { opacity: 0, x: -50 }} whileInView={{ opacity: 1, x: 0 }} viewport={{ once: true }} transition={{ delay: index * 0.07 }}>
                <span className="persona-rank">{song.rank.toString().padStart(2, "0")}</span>
                <AlbumCover albumImageUrl={song.albumImageUrl || song.trackImageUrl} albumTitle={song.album || song.title} size={index === 0 ? "hero" : "lg"} priority={index < 2} />
                <div><h3>{song.title}</h3><p>{song.artist}{song.album ? ` / ${song.album}` : ""}</p><small>{song.detectedPlays.toLocaleString()} detected plays{song.detectedMinutes > 0 ? ` / ${song.formattedMinutes} detected` : ""}</small></div>
              </motion.article>
            ))}
          </RankingPanel>
        </motion.div>
      </div>
    </section>
  );
}

function RankingPanel({ title, period, side, children }: { title: string; period: string; side: string; children: React.ReactNode }) {
  return <div className={`persona-ranking-panel persona-ranking-panel--${side}`}><div className="persona-ranking-heading persona-text-scrim"><p className="persona-chapter-label">Top Artists and Songs</p><h2>{title}</h2><p>{period}</p></div><div className="persona-ranking-list">{children}</div></div>;
}

function FinalRoastScene({ report }: { report: PersonaReport }) {
  const reduced = useReducedMotion();
  return (
    <section className="persona-final-scene" aria-labelledby="final-roast-title">
      <motion.div className="persona-text-scrim persona-final-copy" initial={reduced ? false : { opacity: 0, y: 28 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true, amount: 0.35 }} transition={{ duration: 0.72 }}>
        <p className="persona-chapter-label">Final Roast</p>
        <h2 id="final-roast-title">{report.summary.headline}</h2>
        <p className="persona-final-body">{report.summary.body}</p>
        <blockquote>{report.summary.finalLine}</blockquote>
      </motion.div>
    </section>
  );
}

function RevealScene({ id, direction, className, children }: { id: string; direction: "right" | "zoom"; className: string; children: React.ReactNode }) {
  const ref = useRef<HTMLElement | null>(null);
  const reduced = useReducedMotion();
  const { scrollYProgress } = useScroll({ target: ref, offset: ["start end", "center center"] });
  const x = useTransform(scrollYProgress, [0, 0.78], [direction === "right" ? 180 : 0, 0]);
  const scale = useTransform(scrollYProgress, [0, 0.78], [direction === "zoom" ? 0.76 : 0.96, 1]);
  const opacity = useTransform(scrollYProgress, [0, 0.45], [0, 1]);
  return <section ref={ref} className={`persona-scene-track ${className}`} aria-labelledby={`${id}-title`}><motion.div className="persona-scene-sticky" style={reduced ? undefined : { x, scale, opacity }}>{children}</motion.div></section>;
}

function formatPercent(value: number) { return `${Math.round(value * 100)}%`; }
