import { Sparkles } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { api } from "../api/client";
import { EmptyState } from "../components/EmptyState";
import { LineWaves } from "../components/LineWaves";
import type { MusicCharacter, MusicCharacterResponse, MusicSource, PersonaReport, PersonaReportCard, Prerequisites, TopArtist } from "../types/api";

interface Props {
  report: PersonaReport | null;
  prerequisites: Prerequisites | null;
  busy: boolean;
  topArtists: TopArtist[];
  onGenerate: (mode: "serious" | "playful" | "roast") => void;
  source: MusicSource;
}

interface PersonaProfile {
  headline: string;
  subheadline: string;
  summary: string;
  cards: PersonaReportCard[];
  tasteWorld: string;
  movement: string;
  currentVsLongTerm: string;
  roast: string;
  sourceLabel: string;
}

export function ReportPage({ report, prerequisites, busy, topArtists, onGenerate, source }: Props) {
  const [rollingCharacter, setRollingCharacter] = useState<MusicCharacterResponse | null>(null);
  const [currentCharacter, setCurrentCharacter] = useState<MusicCharacterResponse | null>(null);
  const [characterError, setCharacterError] = useState<string | null>(null);
  const [loadingCharacter, setLoadingCharacter] = useState(false);
  const modelReady = Boolean(prerequisites?.model_installed);
  const disabled = busy || !modelReady;

  useEffect(() => {
    let active = true;
    setLoadingCharacter(true);
    Promise.allSettled([api.musicCharacter("rolling_year", null, source), api.musicCharacter("this_month", null, source)])
      .then(([rolling, current]) => {
        if (!active) return;
        if (rolling.status === "fulfilled") setRollingCharacter(rolling.value);
        if (current.status === "fulfilled") setCurrentCharacter(current.value);
        if (rolling.status === "rejected" && current.status === "rejected") {
          setCharacterError(rolling.reason instanceof Error ? rolling.reason.message : "Music Character is unavailable.");
        } else {
          setCharacterError(null);
        }
      })
      .finally(() => {
        if (active) setLoadingCharacter(false);
      });
    return () => {
      active = false;
    };
  }, [source]);

  const profile = useMemo(
    () => buildPersonaProfile(report, rollingCharacter, currentCharacter),
    [report, rollingCharacter, currentCharacter],
  );

  if (!profile && loadingCharacter) {
    return <EmptyState title="Reading your music character" body="Building the deterministic persona profile from your local listening data." />;
  }

  if (!profile) {
    return (
      <EmptyState
        title="No persona profile yet"
        body={characterError || (source === "spotify" ? "Connect Spotify and refresh Spotify data, then return here for a Music Character based persona read." : "Refresh YouTube Music data or import Google Takeout history, then return here for a Music Character based persona read.")}
      />
    );
  }

  return (
    <div className="space-y-8">
      <header className="relative overflow-hidden rounded-lg border border-white/10 bg-[linear-gradient(135deg,rgba(41,9,9,0.96),rgba(5,5,5,0.99)_58%,rgba(18,8,8,0.98))] shadow-glow">
        <LineWaves className="opacity-50" amplitude={20} speed={0.0001} waveCount={6} />
        <div className="relative p-6 lg:p-9">
          <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_22%_0%,rgba(239,68,68,0.24),transparent_35%)]" />
          <div className="relative flex flex-col gap-7 xl:flex-row xl:items-end xl:justify-between">
            <div className="max-w-5xl">
              <p className="section-label">Persona Report</p>
              <h1 className="mt-4 font-display text-5xl uppercase leading-[0.9] tracking-[0.03em] text-white md:text-7xl">{profile.headline}</h1>
              <p className="mt-5 max-w-4xl text-xl font-semibold leading-8 text-red-100">{profile.subheadline}</p>
              <p className="mt-5 max-w-4xl text-lg leading-8 text-mist">{profile.summary}</p>
            </div>
            <div className="flex flex-wrap gap-2 rounded-xl border border-white/10 bg-black/25 p-2">
              <button className="btn-secondary" disabled={disabled} onClick={() => onGenerate("serious")}>
                <Sparkles size={16} /> Editorial Rewrite
              </button>
              <button className="btn-secondary" disabled={disabled} onClick={() => onGenerate("playful")}>More Playful</button>
              <button className="btn-secondary" disabled={disabled} onClick={() => onGenerate("roast")}>Light Roast</button>
            </div>
          </div>
          <div className="relative mt-7 flex flex-wrap gap-3 text-sm">
            <span className="rounded-full border border-white/10 bg-white/[0.07] px-4 py-2 font-semibold text-white">{profile.sourceLabel}</span>
            <span className="rounded-full border border-white/10 bg-white/[0.04] px-4 py-2 text-mist">Character rules stay deterministic</span>
            {!modelReady ? <span className="rounded-full border border-amber-300/20 bg-amber-300/10 px-4 py-2 text-amber-100">Expanded Gemma rewrite unavailable - Ollama is offline</span> : null}
          </div>
        </div>
      </header>

      <section className="grid gap-4 lg:grid-cols-3">
        {profile.cards.map((card) => (
          <article key={card.title} className="rounded-lg border border-white/10 bg-white/[0.04] p-5 shadow-[0_16px_60px_rgba(0,0,0,0.22)]">
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-red-200">{card.title.split(":", 1)[0]}</p>
            <h2 className="mt-3 text-2xl font-black leading-tight text-white">{card.title.includes(":") ? card.title.split(":").slice(1).join(":").trim() : card.title}</h2>
            <p className="mt-3 text-sm leading-7 text-mist">{card.body}</p>
          </article>
        ))}
      </section>

      {topArtists.length ? (
        <section className="editorial-panel p-5 lg:p-6">
          <div className="flex flex-col gap-2 sm:flex-row sm:items-end sm:justify-between">
            <div>
              <p className="text-xs font-semibold uppercase tracking-[0.18em] text-red-200">Anchor artists</p>
              <h2 className="mt-2 text-3xl font-black text-white">The faces in the sound-world</h2>
            </div>
            <p className="max-w-xl text-sm leading-6 text-mist">
              {source === "spotify" ? "Official Spotify artist images are used where the account data provides them; otherwise initials keep the profile clean." : "Official artist images are used when YouTube Music metadata has them; otherwise initials keep the profile clean."}
            </p>
          </div>
          <div className="mt-5 grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
            {topArtists.slice(0, 4).map((artist) => (
              <ArtistAvatarCard key={artist.artist} artist={artist} />
            ))}
          </div>
        </section>
      ) : null}

      <section className="grid gap-5 xl:grid-cols-[1.08fr_0.92fr]">
        <InterpretationBlock title="What your taste actually feels like" body={profile.tasteWorld} featured />
        <InterpretationBlock title="How you move through music" body={profile.movement} />
      </section>

      <section className="grid gap-5 xl:grid-cols-[0.92fr_1.08fr]">
        <InterpretationBlock title="Current month vs long-term self" body={profile.currentVsLongTerm} />
        <InterpretationBlock title="Friendly roast" body={profile.roast} featured />
      </section>
    </div>
  );
}

function InterpretationBlock({ title, body, featured = false }: { title: string; body: string; featured?: boolean }) {
  return (
    <article className={`rounded-lg border p-6 ${featured ? "border-red-500/20 bg-red-950/20" : "border-white/10 bg-white/[0.04]"}`}>
      <h2 className="text-3xl font-black leading-tight text-white">{title}</h2>
      <p className="mt-4 text-base leading-8 text-mist">{body}</p>
    </article>
  );
}

function ArtistAvatarCard({ artist }: { artist: TopArtist }) {
  const [failed, setFailed] = useState(false);
  useEffect(() => setFailed(false), [artist.image]);
  return (
    <article className="flex items-center gap-4 rounded-lg border border-white/10 bg-black/20 p-4">
      <div className="grid h-20 w-20 shrink-0 place-items-center overflow-hidden rounded-full border border-white/10 bg-red-950/70 text-xl font-black text-white">
        {artist.image && !failed ? (
          <img className="h-full w-full object-cover object-center" src={artist.image} alt={artist.artist} onError={() => setFailed(true)} />
        ) : (
          <span>{initials(artist.artist)}</span>
        )}
      </div>
      <div className="min-w-0">
        <h3 className="truncate text-lg font-black text-white">{artist.artist}</h3>
        <p className="mt-1 line-clamp-2 text-sm leading-6 text-mist">{artist.why_it_matters || artist.artist_loyalty_label}</p>
      </div>
    </article>
  );
}

function buildPersonaProfile(
  report: PersonaReport | null,
  rolling: MusicCharacterResponse | null,
  current: MusicCharacterResponse | null,
): PersonaProfile | null {
  if (report && (report.core_identity_paragraph || report.taste_world_paragraph || report.listener_type_cards?.length)) {
    return {
      headline: report.headline || rolling?.primary.name || "Saville Music Persona",
      subheadline: report.subheadline || report.friendly_roast || rolling?.primary.roast || "Your listening has a character read.",
      summary: report.core_identity_paragraph || report.summary || rolling?.primary.profile || "",
      cards: normaliseCards(report.listener_type_cards, rolling),
      tasteWorld: report.taste_world_paragraph || report.core_identity || buildTasteWorld(rolling),
      movement: report.music_movement_paragraph || report.listening_habits || buildMovement(rolling),
      currentVsLongTerm: report.current_vs_long_term_paragraph || report.current_era || buildCurrentContrast(rolling, current),
      roast: report.friendly_roast || report.subheadline || rolling?.primary.roast || "The profile is opinionated, but politely.",
      sourceLabel: report.model ? `Gemma rewrite: ${report.model}` : "Deterministic Music Character",
    };
  }

  if (rolling) {
    const primary = rolling.primary;
    return {
      headline: primary.name,
      subheadline: primary.roast,
      summary: buildIdentitySummary(rolling),
      cards: cardsFromCharacter(rolling),
      tasteWorld: buildTasteWorld(rolling),
      movement: buildMovement(rolling),
      currentVsLongTerm: buildCurrentContrast(rolling, current),
      roast: primary.roast,
      sourceLabel: "Deterministic Music Character",
    };
  }

  if (report) {
    return {
      headline: report.headline || "Saville Music Persona",
      subheadline: report.friendly_roast || report.subheadline || "Your report is saved from an earlier version.",
      summary: report.summary || report.core_identity || "",
      cards: normaliseCards(report.listener_type_cards, null),
      tasteWorld: report.taste_world_paragraph || report.core_identity || report.summary || "",
      movement: report.music_movement_paragraph || report.listening_habits || "",
      currentVsLongTerm: report.current_vs_long_term_paragraph || report.current_era || "",
      roast: report.friendly_roast || report.subheadline || "",
      sourceLabel: report.model ? `Saved rewrite: ${report.model}` : "Saved report",
    };
  }

  return null;
}

function normaliseCards(cards: PersonaReportCard[] | undefined, character: MusicCharacterResponse | null): PersonaReportCard[] {
  if (cards?.length) return cards.slice(0, 3);
  if (character) return cardsFromCharacter(character);
  return [
    { title: "Primary: Music identity", body: "The report needs refreshed character data for a sharper read." },
    { title: "Secondary: Still forming", body: "No secondary character is available yet." },
    { title: "Modifier: Still forming", body: "No behaviour modifier is available yet." },
  ];
}

function cardsFromCharacter(character: MusicCharacterResponse): PersonaReportCard[] {
  return [
    characterCard("Primary", character.primary),
    character.secondary
      ? characterCard("Secondary", character.secondary)
      : { title: "Secondary: Still forming", body: "The primary character carries most of the signal for this period." },
    character.modifier
      ? characterCard("Modifier", character.modifier)
      : { title: "Modifier: No strong modifier", body: "No separate replay, album, artist, or discovery pattern is loud enough to label on its own." },
  ];
}

function characterCard(label: string, character: MusicCharacter): PersonaReportCard {
  const evidence = character.evidence.slice(0, 2).join("; ");
  return {
    title: `${label}: ${character.name}`,
    body: `${character.profile}${evidence ? ` Why it fits: ${evidence}.` : ""}`,
  };
}

function buildIdentitySummary(character: MusicCharacterResponse) {
  const clusters = joinList(character.top_clusters.slice(0, 3).map((item) => item.name));
  const traits = joinList(character.sonic_traits.slice(0, 4));
  const centre = clusters || "your strongest sound families";
  const texture = traits || "recurring sonic traits";
  return `${character.primary.profile} The read is centred on ${centre}, with ${texture} giving the profile its shape.`;
}

function buildTasteWorld(character: MusicCharacterResponse | null) {
  if (!character) return "The taste-world needs refreshed Music Character data before it can be read confidently.";
  const clusters = joinList(character.top_clusters.slice(0, 4).map((item) => item.name));
  const traits = joinList(character.sonic_traits.slice(0, 5));
  const artists = joinList(character.top_artists.slice(0, 3).map((item) => item.name));
  return `Your taste does not scatter randomly. It keeps circling a sound-world around ${clusters || "its strongest mapped clusters"}, then uses ${traits || "recurring textures"} as the emotional lighting. ${artists ? `${artists} act as anchors, but the larger pattern is the world they belong to.` : "The larger pattern feels sound-led rather than locked to one name."}`;
}

function buildMovement(character: MusicCharacterResponse | null) {
  if (!character) return "Movement patterns need refreshed score data.";
  const repeat = character.key_scores.repeat ?? 0;
  const discovery = character.key_scores.discovery ?? 0;
  const loyalty = character.key_scores.artist_loyalty ?? 0;
  const nostalgia = character.key_scores.nostalgia ?? 0;
  const replayLine = repeat >= 55
    ? "You are not a disposable-listening type; once a song proves itself, it stays in rotation."
    : "You leave room for movement instead of making every favourite live on repeat forever.";
  const discoveryLine = discovery >= 55
    ? "Discovery is active, but it still seems to look for music that fits the emotional shape you already like."
    : "Discovery is selective: new music gets in through fit, not random novelty.";
  const loyaltyLine = loyalty >= 65
    ? "Artists matter as anchors, so the profile has a strong cast of recurring names."
    : "The profile feels more sound-led than single-artist dependent.";
  const nostalgiaLine = nostalgia >= 50 ? "There is a noticeable era-memory pull in the profile." : "Nostalgia adds colour without taking over the whole identity.";
  return `${replayLine} ${discoveryLine} ${loyaltyLine} ${nostalgiaLine}`;
}

function buildCurrentContrast(rolling: MusicCharacterResponse | null, current: MusicCharacterResponse | null) {
  if (!rolling || !current) return "Current-month contrast will appear once both rolling-year and monthly character reads are available.";
  if (rolling.primary.id !== current.primary.id) {
    return `Long-term you read as ${rolling.primary.name}, while this month leans ${current.primary.name}. That suggests a current phase changing the lighting, not necessarily a full identity switch.`;
  }
  return `The current month lines up with the long-term self: ${current.primary.name} still sits at the centre. This is continuity, not a sudden rewrite.`;
}

function joinList(items: (string | null | undefined)[]) {
  const clean = items.map((item) => String(item || "").trim()).filter(Boolean);
  if (clean.length <= 1) return clean[0] || "";
  if (clean.length === 2) return `${clean[0]} and ${clean[1]}`;
  return `${clean.slice(0, -1).join(", ")}, and ${clean[clean.length - 1]}`;
}

function initials(value: string) {
  return value
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0]?.toUpperCase())
    .join("") || "A";
}
