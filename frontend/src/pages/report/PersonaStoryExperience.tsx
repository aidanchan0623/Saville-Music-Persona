import { useEffect, useMemo, useRef, useState } from "react";
import { motion, useInView, useReducedMotion, useScroll, useSpring, useTransform } from "motion/react";
import { AlbumCover, ArtistAvatar } from "../../components/Artwork";
import type { PersonaGenre, PersonaReport } from "../../types/api";
import { PersonaAlbumDome } from "./PersonaAlbumDome";

interface Props {
  report: PersonaReport;
  busy: boolean;
  onGenerate: () => Promise<{ ok: boolean; message: string }>;
  titleAnimationKey: string;
}

export function PersonaStoryExperience({ report, busy, onGenerate, titleAnimationKey }: Props) {
  const rootRef = useRef<HTMLDivElement | null>(null);
  const { scrollYProgress } = useScroll({ target: rootRef, offset: ["start start", "end end"] });
  const progress = useSpring(scrollYProgress, { stiffness: 82, damping: 24, mass: 0.35 });
  const albumList = useMemo(() => report.backgroundAlbums, [report.backgroundAlbums]);
  const [explainer, setExplainer] = useState<"ages" | "personalities" | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const regenerate = async () => setNotice((await onGenerate()).message);

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
          <div className="persona-report__actions">
            <button type="button" disabled={busy} className="persona-tone persona-tone--active" onClick={regenerate}>{busy ? "Regenerating..." : "Regenerate report"}</button>
            {notice && <span className="persona-generation-notice" role="status">{notice}</span>}
          </div>
        </header>

        <PersonalityScene report={report} titleAnimationKey={titleAnimationKey} onLearnMore={() => setExplainer("personalities")} />
        <ListeningWorldScene report={report} />
        <MusicalAgeScene report={report} onLearnMore={() => setExplainer("ages")} />
        <TopFiveScene report={report} />
        <FinalRoastScene report={report} />

      </main>
      {explainer && <ExplainerModal report={report} kind={explainer} onClose={() => setExplainer(null)} />}
    </div>
  );
}

function PersonalityScene({ report, titleAnimationKey, onLearnMore }: { report: PersonaReport; titleAnimationKey: string; onLearnMore: () => void }) {
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
          <button className="persona-explainer-button" type="button" onClick={onLearnMore}>Learn more</button>
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

function MusicalAgeScene({ report, onLearnMore }: { report: PersonaReport; onLearnMore: () => void }) {
  return (
    <RevealScene id="musical-age" direction="zoom" className="persona-age-scene">
      <div className="persona-age-orbit" aria-hidden="true" />
      <div className="persona-text-scrim persona-age-copy">
        <p className="persona-chapter-label">Musical Age</p>
        <p className="persona-age-number">{report.musicalAge.age}</p>
        <h2 id="musical-age-title">{report.musicalAge.title}</h2>
        <button className="persona-explainer-button" type="button" onClick={onLearnMore}>Learn more</button>
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
        <p className="persona-chapter-label">Closing Summary</p>
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

function ExplainerModal({ report, kind, onClose }: { report: PersonaReport; kind: "ages" | "personalities"; onClose: () => void }) {
  const closeRef = useRef<HTMLButtonElement | null>(null);
  const dialogRef = useRef<HTMLElement | null>(null);
  const restoreFocus = useRef<HTMLElement | null>(document.activeElement instanceof HTMLElement ? document.activeElement : null);
  const isAges = kind === "ages";
  useEffect(() => {
    closeRef.current?.focus();
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") { onClose(); return; }
      if (event.key !== "Tab" || !dialogRef.current) return;
      const focusable = Array.from(dialogRef.current.querySelectorAll<HTMLElement>("button, [href], input, select, textarea, [tabindex]:not([tabindex='-1'])"));
      if (!focusable.length) return;
      const first = focusable[0]; const last = focusable[focusable.length - 1];
      if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last.focus(); }
      else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first.focus(); }
    };
    window.addEventListener("keydown", onKeyDown);
    return () => { window.removeEventListener("keydown", onKeyDown); restoreFocus.current?.focus(); };
  }, [onClose]);
  const heading = isAges ? "Musical Age guide" : "Musical Personality guide";
  return <div className="persona-explainer-backdrop" onMouseDown={(event) => { if (event.target === event.currentTarget) onClose(); }}>
    <section ref={dialogRef} className="persona-explainer-modal" role="dialog" aria-modal="true" aria-labelledby="persona-explainer-title">
      <header><h2 id="persona-explainer-title">{heading}</h2><button ref={closeRef} type="button" aria-label="Close guide" onClick={onClose}>Close</button></header>
      <div className="persona-explainer-scroll">
        {isAges ? report.explainers.musicalAges.map((item) => <article key={item.title} className={report.musicalAge.age >= item.minAge && report.musicalAge.age <= item.maxAge ? "is-current" : ""}><p>{item.minAge}-{item.maxAge}</p><h3>{item.title}</h3><span>{item.summary}</span></article>) : report.explainers.personalities.map((item) => <article key={item.id} className={report.personality.id === item.id ? "is-current" : ""}><p>{item.category}</p><h3>{item.name}</h3><span>{item.profile}</span><ul>{item.triggerRules.map((rule) => <li key={rule}>{rule}</li>)}</ul></article>)}
      </div>
    </section>
  </div>;
}
