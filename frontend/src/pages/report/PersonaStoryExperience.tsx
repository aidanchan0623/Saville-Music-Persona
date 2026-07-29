import { useEffect, useMemo, useRef, useState } from "react";
import { Crown } from "lucide-react";
import { motion, useInView, useReducedMotion, useScroll, useSpring, useTransform } from "motion/react";
import { AlbumCover, ArtistAvatar } from "../../components/Artwork";
import ShimmerText from "../../components/ui/shimmer-text";
import type { PersonaGenre, PersonaReport, PersonaReportPeriodKey, PersonaTopArtist, PersonaTopSong } from "../../types/api";
import { PersonaAlbumDome } from "./PersonaAlbumDome";

interface Props {
  report: PersonaReport;
  busy: boolean;
  onGenerate: (period: PersonaReportPeriodKey) => Promise<{ ok: boolean; message: string }>;
  titleAnimationKey: string;
}

export function PersonaStoryExperience({ report, busy, onGenerate, titleAnimationKey }: Props) {
  const rootRef = useRef<HTMLDivElement | null>(null);
  const { scrollYProgress } = useScroll({ target: rootRef, offset: ["start start", "end end"] });
  const progress = useSpring(scrollYProgress, { stiffness: 82, damping: 24, mass: 0.35 });
  const albumList = useMemo(() => report.backgroundAlbums, [report.backgroundAlbums]);
  const [explainer, setExplainer] = useState<"ages" | "personalities" | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [selectedPeriod, setSelectedPeriod] = useState<PersonaReportPeriodKey>(report.period.key === "this_month" ? "this_month" : "rolling_year");
  useEffect(() => setSelectedPeriod(report.period.key === "this_month" ? "this_month" : "rolling_year"), [report.period.key]);
  const regenerate = async () => setNotice((await onGenerate(selectedPeriod)).message);

  return (
    <div ref={rootRef} className="persona-report-page">
      <PersonaAlbumDome albums={albumList} progress={progress} />
      <div className="persona-report-scrim" aria-hidden="true" />
      <main className="persona-scroll-story">
        <header className="persona-report__masthead">
          <div className="persona-report__heading">
            <p className="persona-report__eyebrow">Persona Report</p>
            <ShimmerText><h1>Your listening habits, professionally overanalysed.</h1></ShimmerText>
            <p className="persona-report__meta">{report.source === "spotify" ? "Spotify" : "YouTube Music"} &middot; showing {report.period.label.toLowerCase()} &middot; {report.period.timezone}</p>
          </div>
          <div className="persona-report__actions">
            <div className="persona-period-picker" role="group" aria-label="Report generation period">
              <button type="button" className={`persona-tone${selectedPeriod === "rolling_year" ? " persona-tone--active" : ""}`} disabled={busy} onClick={() => setSelectedPeriod("rolling_year")}>Rolling year</button>
              <button type="button" className={`persona-tone${selectedPeriod === "this_month" ? " persona-tone--active" : ""}`} disabled={busy} onClick={() => setSelectedPeriod("this_month")}>This month</button>
            </div>
            <button type="button" disabled={busy} className="persona-generate-button" onClick={regenerate}>{busy ? "Writing the roast..." : report.period.key === selectedPeriod ? "Regenerate" : `Generate ${selectedPeriod === "this_month" ? "this month" : "rolling year"}`}</button>
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
          <ShimmerText className="max-w-full"><h1 id="personality-title" key={titleAnimationKey}>{report.personality.title}</h1></ShimmerText>
          <button className="persona-explainer-button" type="button" onClick={onLearnMore}>Learn more</button>
          <p className="persona-lede">{report.personality.shortDescription}</p>
          {report.personality.habits.length > 0 && <div className="persona-habit-chips" aria-label="Listening habits">{report.personality.habits.map((habit) => <span key={habit}>{habit}</span>)}</div>}
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
          <ShimmerText><h2 id="listening-world-title">{report.listeningWorld.formattedTime} detected</h2></ShimmerText>
          <p className="persona-period-line">{report.period.label}</p>
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
        <ShimmerText><h2 id="musical-age-title">{report.musicalAge.title}</h2></ShimmerText>
        <button className="persona-explainer-button" type="button" onClick={onLearnMore}>Learn more</button>
        <div className="persona-age-facts">
          <span>Typical range <strong>{report.musicalAge.likelyMin}-{report.musicalAge.likelyMax} years</strong></span>
          <span>Dominant decade <strong>{report.musicalAge.dominantDecade}</strong></span>
          <span>{report.musicalAge.confidenceLabel}</span>
        </div>
        <p className="persona-body">{report.musicalAge.explanation}</p>
        <p className="persona-period-line">Musical Age measures how old your music is and which eras dominate. It is not your real age.</p>
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
            <RankingPodium kind="artists" items={report.topFive.artists} />
          </RankingPanel>
          <RankingPanel title="Top Songs" period={report.period.label} side="songs">
            <RankingPodium kind="songs" items={report.topFive.songs} />
          </RankingPanel>
        </motion.div>
      </div>
    </section>
  );
}

function RankingPanel({ title, period, side, children }: { title: string; period: string; side: string; children: React.ReactNode }) {
  const [scope, ...dateParts] = period.split("·");
  const dates = dateParts.join("·").trim();
  return <div className={`persona-ranking-panel persona-ranking-panel--${side}`}><div className="persona-ranking-heading persona-text-scrim"><p className="persona-chapter-label">The five-repeat hall of fame</p><ShimmerText><h2>{title}</h2></ShimmerText><p className="persona-ranking-period"><span>{dates ? scope.trim() : "Listening period"}</span><b>{dates || scope.trim()}</b></p></div><div className="persona-ranking-podium-shell">{children}</div></div>;
}

function RankingPodium({ kind, items }: { kind: "artists"; items: PersonaTopArtist[] } | { kind: "songs"; items: PersonaTopSong[] }) {
  const reduced = useReducedMotion();
  return (
    <div className={`persona-podium persona-podium--${kind}`} aria-label={`Top five ${kind}`}>
      {items.slice(0, 5).map((item) => {
        const rank = Math.min(5, Math.max(1, item.rank));
        const visualColumn = ({ 1: 3, 2: 2, 3: 4, 4: 1, 5: 5 } as const)[rank as 1 | 2 | 3 | 4 | 5];
        const isArtist = kind === "artists";
        const artist = isArtist ? item as PersonaTopArtist : null;
        const song = !isArtist ? item as PersonaTopSong : null;
        const title = artist?.name ?? song?.title ?? "Unknown";
        const subtitle = artist
          ? `${artist.detectedPlays.toLocaleString()} plays · ${artist.uniqueSongs} songs`
          : `${song?.artist ?? "Unknown artist"} · ${song?.detectedPlays.toLocaleString() ?? 0} plays`;
        return (
          <motion.article
            className={`persona-podium-entry persona-podium-entry--rank-${rank}`}
            key={artist?.name ?? `${song?.title}-${song?.artist}`}
            initial={reduced ? false : { opacity: 0, x: (3 - visualColumn) * 76, y: 46, scale: 0.84 }}
            whileInView={{ opacity: 1, x: 0, y: 0, scale: 1 }}
            viewport={{ once: true, amount: 0.35 }}
            transition={{ type: "spring", stiffness: 105, damping: 17, delay: rank === 1 ? 0.06 : 0.12 + visualColumn * 0.055 }}
          >
            <div className="persona-podium-profile">
              {rank === 1 ? <span className="persona-podium-crown" aria-label="First place"><Crown aria-hidden="true" /></span> : null}
              {artist
                ? <ArtistAvatar artistImageUrl={artist.artistImageUrl} artistName={artist.name} size={rank === 1 ? "hero" : "lg"} shape="circle" priority={rank <= 2} />
                : <AlbumCover albumImageUrl={song?.albumImageUrl} fallbackImageUrl={song?.trackImageUrl} albumTitle={song?.album || song?.title || "Song"} size={rank === 1 ? "hero" : "lg"} priority={rank <= 2} />}
              <h3 title={title}>{title}</h3>
              <p>{subtitle}</p>
              {song?.detectedMinutes ? <small>{song.formattedMinutes} detected</small> : null}
            </div>
            <motion.div
              className="persona-podium-step"
              initial={reduced ? false : { scaleY: 0.08 }}
              whileInView={{ scaleY: 1 }}
              viewport={{ once: true, amount: 0.35 }}
              transition={{ duration: 0.62, ease: [0.22, 1, 0.36, 1], delay: 0.08 + visualColumn * 0.05 }}
            >
              <span>{rank}</span>
            </motion.div>
          </motion.article>
        );
      })}
    </div>
  );
}

function FinalRoastScene({ report }: { report: PersonaReport }) {
  const reduced = useReducedMotion();
  return (
    <section className="persona-final-scene" aria-labelledby="final-roast-title">
      <motion.div className="persona-text-scrim persona-final-copy" initial={reduced ? false : { opacity: 0, y: 28 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true, amount: 0.35 }} transition={{ duration: 0.72 }}>
        <p className="persona-chapter-label">Closing Summary</p>
        <ShimmerText className="max-w-full"><h2 id="final-roast-title">{report.summary.headline}</h2></ShimmerText>
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
        {isAges ? report.explainers.musicalAges.map((item) => <article key={item.title} className={report.musicalAge.age >= item.minAge && report.musicalAge.age <= item.maxAge ? "is-current" : ""}><p>{item.minAge}-{item.maxAge} years</p><h3>{item.title}</h3><span>{item.summary}</span></article>) : report.explainers.personalities.map((item) => <article key={item.id} className={report.personality.id === item.id ? "is-current" : ""}><p>{item.category}</p><h3>{item.name}</h3><span>{item.profile}</span></article>)}
      </div>
    </section>
  </div>;
}
