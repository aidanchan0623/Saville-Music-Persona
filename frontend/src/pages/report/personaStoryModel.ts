import type {
  MusicCharacterResponse,
  MusicSource,
  PersonaMainCharacter,
  PersonaReport,
  PersonaStoryChapter,
  TopAlbumItem,
  TopArtist,
} from "../../types/api";
import type { OrbitImageItem } from "../../components/reactbits/OrbitImages/OrbitImages";

export type PersonaStory = {
  personaName: string;
  openingHook: string;
  coreSound: Required<PersonaStoryChapter>;
  comfortLoop: Required<PersonaStoryChapter>;
  mainCharacters: PersonaMainCharacter[];
  plotTwist: { headline: string; body: string };
  closing: { headline: string; body: string; finalLine: string };
  sourceLabel: string;
  usedFallback: boolean;
};

export type GenreSegment = {
  label: string;
  value: number;
  color: string;
};

export function buildPersonaStory(
  report: PersonaReport | null,
  rolling: MusicCharacterResponse | null,
  current: MusicCharacterResponse | null,
  topArtists: TopArtist[],
): PersonaStory | null {
  const fallback = fallbackStoryFromCharacter(rolling, current, topArtists);
  if (report && report.personaReportSchemaVersion === 2) {
    return {
      personaName: cleanText(report.personaName || report.headline || fallback?.personaName || "Saville Music Persona"),
      openingHook: cleanText(report.openingHook || fallback?.openingHook || report.subheadline || "Your listening has a character read."),
      coreSound: storyChapter(report.coreSound, fallback?.coreSound),
      comfortLoop: storyChapter(report.comfortLoop, fallback?.comfortLoop),
      mainCharacters: normaliseStoryCharacters(report.mainCharacters, fallback?.mainCharacters ?? [], topArtists),
      plotTwist: {
        headline: cleanText(report.plotTwist?.headline || fallback?.plotTwist.headline || "The Signal Stays Honest"),
        body: cleanText(report.plotTwist?.body || fallback?.plotTwist.body || "There is not enough contrast to claim a dramatic twist yet."),
      },
      closing: {
        headline: cleanText(report.closing?.headline || fallback?.closing.headline || report.personaName || "Closing Credits"),
        body: cleanText(report.closing?.body || fallback?.closing.body || report.summary || "The report is ready, but the story needs more refreshed listening data to sharpen."),
        finalLine: cleanText(report.closing?.finalLine || fallback?.closing.finalLine || "Roll the next song with intent."),
      },
      sourceLabel: report.fallback || !report.model ? "Deterministic story fallback" : `Gemma story: ${report.model}`,
      usedFallback: Boolean(report.fallback || !report.model),
    };
  }

  if (fallback) return fallback;
  if (!report) return null;

  return {
    personaName: cleanText(report.headline || "Saville Music Persona"),
    openingHook: cleanText(report.subheadline || report.friendly_roast || "Your saved report needs a fresh story rewrite."),
    coreSound: storyChapter(undefined, { headline: report.headline || "Saved Report", body: report.core_identity_paragraph || report.summary || "", pullQuote: "" }),
    comfortLoop: storyChapter(undefined, { headline: "Listening Pattern", body: report.music_movement_paragraph || report.listening_habits || "", pullQuote: "" }),
    mainCharacters: normaliseStoryCharacters(undefined, [], topArtists),
    plotTwist: { headline: "Saved Format", body: "This cached report came from an older schema. Generate a fresh story to unlock the full cinematic layout." },
    closing: { headline: "Closing Credits", body: report.summary || report.core_identity || "Generate a fresh report for a sharper closing read.", finalLine: "Fresh data deserves fresh credits." },
    sourceLabel: "Older saved report",
    usedFallback: true,
  };
}

export function buildOrbitAlbums(albums: TopAlbumItem[]): OrbitImageItem[] {
  const seen = new Set<string>();
  const result: OrbitImageItem[] = [];
  for (const album of albums) {
    if (!album.album_image_url) continue;
    const key = normaliseName(album.album_id || album.key || `${album.album} ${album.artist}`);
    if (!key || seen.has(key)) continue;
    seen.add(key);
    result.push({
      src: album.album_image_url,
      alt: `${album.album} by ${album.artist}`,
    });
    if (result.length >= 8) break;
  }
  return result;
}

export function buildGenreSegments(character: MusicCharacterResponse | null): GenreSegment[] {
  const palette = ["#ef2b2d", "#9f1620", "#5f1b21", "#73737b", "#c6c6ce"];
  const raw = (character?.top_clusters ?? []).filter((item) => item.share > 0).slice(0, 5);
  const segments: GenreSegment[] = [];
  let used = 0;
  for (const item of raw) {
    if (used >= 99.5) break;
    const value = roundShare(Math.max(0, Math.min(item.share, 100 - used)));
    if (value <= 0) continue;
    segments.push({ label: item.name, value, color: palette[segments.length % palette.length] });
    used += value;
  }
  const remaining = roundShare(Math.max(0, 100 - used));
  if (segments.length && remaining >= 0.5) {
    segments.push({ label: "Other / unclassified", value: remaining, color: "#29292e" });
  }
  return segments;
}

export function scoreValue(character: MusicCharacterResponse | null, key: string) {
  const value = character?.key_scores?.[key];
  return Number.isFinite(value) ? Number(value) : 0;
}

export function findArtist(artists: TopArtist[], name: string) {
  const normalized = normaliseName(name);
  return artists.find((artist) => normaliseName(artist.artist) === normalized);
}

export function artistMetric(artist: TopArtist | undefined, source: MusicSource) {
  if (!artist) return source === "spotify" ? "Spotify profile signal" : "YouTube Music signal";
  const plays = artist.play_count ? `${artist.play_count} plays` : "";
  const songs = artist.unique_songs_played ? `${artist.unique_songs_played} songs` : "";
  return [plays, songs].filter(Boolean).join(" / ") || artist.artist_loyalty_label;
}

export function initials(value: string) {
  return value
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0]?.toUpperCase())
    .join("") || "A";
}

export function formatShare(value: number) {
  return `${Number.isInteger(value) ? value.toFixed(0) : value.toFixed(1)}%`;
}

function fallbackStoryFromCharacter(
  rolling: MusicCharacterResponse | null,
  current: MusicCharacterResponse | null,
  topArtists: TopArtist[],
): PersonaStory | null {
  if (!rolling) return null;
  const dominantSound = rolling.top_clusters[0]?.name ?? "your strongest sound-world";
  const secondarySound = rolling.top_clusters[1]?.name ?? rolling.secondary?.name ?? "a smaller side quest";
  const traits = rolling.sonic_traits.slice(0, 4).join(" / ") || "recurring sonic traits";
  const repeat = scoreValue(rolling, "repeat");
  const discovery = scoreValue(rolling, "discovery");
  const hasContrast = Boolean(current && current.primary.id !== rolling.primary.id);
  const topArtistNames = joinList(topArtists.slice(0, 3).map((artist) => artist.artist)) || "the anchor artists";
  return {
    personaName: rolling.primary.name,
    openingHook: rolling.primary.roast || `Your headphones keep circling ${dominantSound} with intent.`,
    coreSound: {
      headline: `${dominantSound} Holds The Centre`,
      body: `The main world is ${dominantSound}, with ${traits} shaping the atmosphere. ${topArtistNames} give that world a recognizable cast without turning the whole report into a leaderboard.`,
      pullQuote: traits,
    },
    comfortLoop: {
      headline: repeat >= discovery ? "The Songs Earn Their Return" : "Discovery Keeps The Door Open",
      body: `Repeat score ${Math.round(repeat)} and discovery score ${Math.round(discovery)} point to ${
        repeat >= discovery ? "a listener who lets trusted songs stay in rotation" : "a listener who keeps testing new doors while holding onto a clear centre"
      }. The pattern is about fit, not random churn.`,
      pullQuote: repeat >= discovery ? "Comfort, but with standards." : "New songs need the right lighting.",
    },
    mainCharacters: topArtists.slice(0, 3).map((artist, index) => ({
      artistName: artist.artist,
      role: index === 0 ? "The emotional anchor" : index === 1 ? "The recurring atmosphere" : "The reliable wildcard",
      line: artist.why_it_matters || artist.artist_loyalty_label,
    })),
    plotTwist: {
      headline: hasContrast ? "This Month Changes The Lighting" : "Consistency Is The Twist",
      body:
        hasContrast && current
          ? `Long-term you read as ${rolling.primary.name}, while this month leans ${current.primary.name}. That looks like a real phase shift in the current sample, not a whole personality costume change.`
          : `There is no need to invent a surprise. ${dominantSound} keeps the centre steady, while ${secondarySound} adds a smaller orbit around the same identity.`,
    },
    closing: {
      headline: `${rolling.primary.name}, In The Credits`,
      body: `${rolling.primary.name} is a story of ${dominantSound}, repeat-worthy anchors, and ${traits}. The strongest read is not one statistic; it is the way the same musical weather keeps returning with different lighting.`,
      finalLine: "Roll the next song with intent.",
    },
    sourceLabel: "Deterministic Music Character",
    usedFallback: true,
  };
}

function storyChapter(value: PersonaStoryChapter | undefined, fallback?: Required<PersonaStoryChapter>): Required<PersonaStoryChapter> {
  return {
    headline: cleanText(value?.headline || fallback?.headline || "The Signal Is Still Forming"),
    body: cleanText(value?.body || fallback?.body || "Refresh your listening data to sharpen this chapter."),
    pullQuote: cleanText(value?.pullQuote || fallback?.pullQuote || ""),
  };
}

function normaliseStoryCharacters(
  characters: PersonaMainCharacter[] | undefined,
  fallback: PersonaMainCharacter[],
  topArtists: TopArtist[],
) {
  const allowed = new Map(topArtists.map((artist) => [normaliseName(artist.artist), artist.artist]));
  const result: PersonaMainCharacter[] = [];
  const used = new Set<string>();
  for (const character of characters ?? []) {
    const name = allowed.get(normaliseName(character.artistName));
    if (!name || used.has(normaliseName(name))) continue;
    result.push({
      artistName: name,
      role: cleanText(character.role || "The anchor"),
      line: cleanText(character.line || "A recurring name in the story."),
    });
    used.add(normaliseName(name));
    if (result.length >= 3) break;
  }
  for (const character of fallback) {
    if (result.length >= 3) break;
    const normalized = normaliseName(character.artistName);
    if (!normalized || used.has(normalized)) continue;
    result.push(character);
    used.add(normalized);
  }
  return result;
}

function cleanText(value: string | null | undefined) {
  return String(value || "").replace(/\s+/g, " ").trim();
}

function joinList(items: (string | null | undefined)[]) {
  const clean = items.map((item) => cleanText(item)).filter(Boolean);
  if (clean.length <= 1) return clean[0] || "";
  if (clean.length === 2) return `${clean[0]} and ${clean[1]}`;
  return `${clean.slice(0, -1).join(", ")}, and ${clean[clean.length - 1]}`;
}

function normaliseName(value: string | null | undefined) {
  return cleanText(value).toLocaleLowerCase();
}

function roundShare(value: number) {
  return Math.round(value * 10) / 10;
}
