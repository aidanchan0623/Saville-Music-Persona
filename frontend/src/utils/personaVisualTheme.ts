import type { Overview, TasteDnaExplorer } from "../types/api";

export type PersonaThemeImage = {
  src: string;
  alt: string;
  position?: string;
};

export type PersonaVisualTheme = {
  themeKey: string;
  primaryImage: PersonaThemeImage;
  secondaryImages: PersonaThemeImage[];
  overlayStrength: number;
  position: string;
  accentLabel: string;
};

type ThemeDefinition = PersonaVisualTheme & {
  aliases: string[];
  traitWords: string[];
  energyBias?: "high" | "low";
  discoveryBias?: "comfort" | "discovery";
};

const THEMES: ThemeDefinition[] = [
  {
    themeKey: "alternative-atmospheric",
    aliases: ["alternative", "indie", "rock", "emo", "post-hardcore", "metalcore", "pop punk"],
    traitWords: ["cathartic", "melodic", "anthemic", "dramatic", "guitar", "high-energy", "atmospheric"],
    energyBias: "high",
    discoveryBias: "comfort",
    accentLabel: "Guitar-driven atmosphere",
    overlayStrength: 0.78,
    position: "center",
    primaryImage: {
      src: "/persona-backgrounds/alternative-guitar-01.webp",
      alt: "Close-up electric guitar detail",
      position: "center",
    },
    secondaryImages: [
      { src: "/persona-backgrounds/headphones-chill-01.webp", alt: "Headphones in a quiet listening setup", position: "center" },
      { src: "/persona-backgrounds/rehearsal-stage-01.webp", alt: "Small music stage with dim rehearsal-room light", position: "center" },
      { src: "/persona-backgrounds/rain-night-01.webp", alt: "Rainy city street at night", position: "center" },
    ],
  },
  {
    themeKey: "classical-piano",
    aliases: ["classical", "piano", "orchestra", "soundtrack", "cinematic"],
    traitWords: ["elegant", "cinematic", "instrumental", "melodic", "restrained"],
    energyBias: "low",
    accentLabel: "Piano and concert-room restraint",
    overlayStrength: 0.7,
    position: "center",
    primaryImage: { src: "/persona-backgrounds/classical-piano-01.webp", alt: "Hands playing piano keys", position: "center" },
    secondaryImages: [
      { src: "/persona-backgrounds/vinyl-soul-01.webp", alt: "Vinyl record detail", position: "center" },
      { src: "/persona-backgrounds/studio-mic-01.webp", alt: "Studio microphone with pop shield", position: "center" },
    ],
  },
  {
    themeKey: "jazz-late-night",
    aliases: ["jazz", "swing", "bebop", "brass"],
    traitWords: ["warm", "late-night", "improvised", "intimate"],
    energyBias: "low",
    accentLabel: "Late-night club intimacy",
    overlayStrength: 0.74,
    position: "center",
    primaryImage: { src: "/persona-backgrounds/jazz-club-01.webp", alt: "Intimate jazz club interior and stage", position: "center" },
    secondaryImages: [
      { src: "/persona-backgrounds/studio-mic-01.webp", alt: "Studio microphone with pop shield", position: "center" },
      { src: "/persona-backgrounds/vinyl-soul-01.webp", alt: "Vinyl record detail", position: "center" },
    ],
  },
  {
    themeKey: "electronic-ambient",
    aliases: ["electronic", "ambient", "edm", "dance", "house", "techno", "synth"],
    traitWords: ["atmospheric", "neon", "textural", "minimal", "high-energy", "hypnotic"],
    discoveryBias: "discovery",
    accentLabel: "Synth atmosphere and motion",
    overlayStrength: 0.76,
    position: "center",
    primaryImage: { src: "/persona-backgrounds/electronic-synth-01.webp", alt: "Close-up of a synthesizer", position: "center" },
    secondaryImages: [
      { src: "/persona-backgrounds/rain-night-01.webp", alt: "Rainy city street at night", position: "center" },
      { src: "/persona-backgrounds/rehearsal-stage-01.webp", alt: "Small music stage with dim rehearsal-room light", position: "center" },
    ],
  },
  {
    themeKey: "studio-rap-rnb",
    aliases: ["hip-hop", "rap", "r&b", "rnb", "soul", "pop"],
    traitWords: ["studio", "warm", "polished", "smooth", "rhythmic"],
    accentLabel: "Studio and vinyl warmth",
    overlayStrength: 0.72,
    position: "center",
    primaryImage: { src: "/persona-backgrounds/studio-mic-01.webp", alt: "Studio microphone with pop shield", position: "center" },
    secondaryImages: [
      { src: "/persona-backgrounds/vinyl-soul-01.webp", alt: "Vinyl record detail", position: "center" },
      { src: "/persona-backgrounds/headphones-chill-01.webp", alt: "Headphones in a quiet listening setup", position: "center" },
    ],
  },
  {
    themeKey: "neutral-private-listening",
    aliases: ["unknown", "music"],
    traitWords: ["comfort", "quiet", "late-night", "introspective"],
    discoveryBias: "comfort",
    accentLabel: "Private listening room",
    overlayStrength: 0.76,
    position: "center",
    primaryImage: { src: "/persona-backgrounds/headphones-chill-01.webp", alt: "Headphones in a quiet listening setup", position: "center" },
    secondaryImages: [
      { src: "/persona-backgrounds/vinyl-soul-01.webp", alt: "Vinyl record detail", position: "center" },
      { src: "/persona-backgrounds/rain-night-01.webp", alt: "Rainy city street at night", position: "center" },
    ],
  },
];

export function resolvePersonaVisualTheme(overview: Overview | null, currentTaste?: TasteDnaExplorer | null): PersonaVisualTheme {
  if (!overview) return THEMES[THEMES.length - 1];

  const taste = overview.taste_interpretation;
  const genreSignals = [
    overview.top_genre_cluster,
    ...taste.core_genre_families.map((item) => item.name),
    ...taste.secondary_genre_families.map((item) => item.name),
    ...taste.side_quests.map((item) => item.name),
    ...taste.canonical_genre_shares.map((item) => item.name),
    currentTaste?.core_identity,
  ].filter(Boolean).map(normalise);

  const traitSignals = [
    ...(taste.sonic_traits ?? []),
    ...(overview.taste_dna?.sonic_traits ?? []),
    ...(currentTaste?.traits ?? []).map((item) => item.trait),
  ].filter(Boolean).map(normalise);

  const repeatValue = Number(overview.repeat_score?.value ?? 0);
  const discoveryValue = Number(overview.discovery_score?.value ?? 0);
  const comfortMode = repeatValue >= discoveryValue;

  let bestTheme = THEMES[THEMES.length - 1];
  let bestScore = -Infinity;
  for (const theme of THEMES) {
    const aliasScore = genreSignals.reduce((sum, signal) => sum + scoreWords(signal, theme.aliases, 8), 0);
    const traitScore = traitSignals.reduce((sum, signal) => sum + scoreWords(signal, theme.traitWords, 3), 0);
    const energyScore = theme.energyBias === "high" && traitSignals.some((signal) => signal.includes("high") || signal.includes("anthemic")) ? 4 : 0;
    const discoveryScore = theme.discoveryBias === "comfort" && comfortMode ? 2 : theme.discoveryBias === "discovery" && !comfortMode ? 2 : 0;
    const score = aliasScore + traitScore + energyScore + discoveryScore;
    if (score > bestScore) {
      bestScore = score;
      bestTheme = theme;
    }
  }

  return {
    themeKey: bestTheme.themeKey,
    primaryImage: bestTheme.primaryImage,
    secondaryImages: bestTheme.secondaryImages,
    overlayStrength: bestTheme.overlayStrength,
    position: bestTheme.position,
    accentLabel: bestTheme.accentLabel,
  };
}

function scoreWords(signal: string, words: string[], weight: number) {
  return words.some((word) => signal.includes(normalise(word))) ? weight : 0;
}

function normalise(value: unknown) {
  return String(value ?? "").toLowerCase().replace(/[^a-z0-9]+/g, " ").trim();
}
