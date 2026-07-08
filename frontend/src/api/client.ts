import type {
  AuthStatus,
  Charts,
  ListeningMinutes,
  MusicSource,
  MusicCharacterResponse,
  MusicCharacterRewrite,
  Overview,
  PersonaReport,
  TopAlbumSongsResponse,
  TopAlbumsResponse,
  TopArtistSongsResponse,
  PeriodTopResponse,
  Prerequisites,
  Recommendation,
  ScoreMetric,
  SpotifyStatus,
  TasteDnaComparison,
  TasteDnaExplorer,
  TopArtist,
  TopTrack,
} from "../types/api";

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000/api";

function paramsWithSource(source: MusicSource = "youtube", values: Record<string, string | null | undefined> = {}) {
  const params = new URLSearchParams({ source });
  for (const [key, value] of Object.entries(values)) {
    if (value) params.set(key, value);
  }
  return params;
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json", ...(init?.headers ?? {}) },
    ...init,
  });
  if (!response.ok) {
    let message = `${response.status} ${response.statusText}`;
    try {
      const data = await response.json();
      const detail = data.detail;
      if (typeof detail === "string") message = detail;
      if (detail?.detail) message = detail.detail;
      if (detail?.error) message = `${detail.error}: ${message}`;
    } catch {
      // Keep the HTTP status message.
    }
    throw new Error(message);
  }
  return response.json() as Promise<T>;
}

export const api = {
  health: () => request<{ ok: boolean }>("/health"),
  prerequisites: () => request<Prerequisites>("/prerequisites"),
  authStatus: (live = false) => request<AuthStatus>(`/auth/status${live ? "?live=true" : ""}`),
  authSetup: () => request<Record<string, unknown>>("/auth/setup", { method: "POST", body: "{}" }),
  spotifyStatus: () => request<SpotifyStatus>("/spotify/status"),
  spotifyLoginUrl: () => `${API_BASE}/spotify/login`,
  spotifyRefresh: () =>
    request<{ refreshed_at: string; warnings: string[]; coverage: unknown; track_count: number; play_count: number; profile: Record<string, unknown> }>("/spotify/refresh", {
      method: "POST",
      body: "{}",
    }),
  spotifyDisconnect: () => request<{ connected: boolean; message: string }>("/spotify/disconnect", { method: "POST", body: "{}" }),
  refresh: (useDemo: boolean) =>
    request<{ refreshed_at: string; warnings: string[]; coverage: unknown; track_count: number; play_count: number }>("/data/refresh", {
      method: "POST",
      body: JSON.stringify({ use_demo: useDemo }),
    }),
  importTakeout: async (file: File) => {
    const form = new FormData();
    form.append("file", file);
    const response = await fetch(`${API_BASE}/data/import-takeout`, { method: "POST", body: form });
    if (!response.ok) {
      let message = `${response.status} ${response.statusText}`;
      try {
        const data = await response.json();
        message = data.detail?.detail || data.detail?.error || message;
      } catch {
        // Keep HTTP status message.
      }
      throw new Error(message);
    }
    return response.json() as Promise<{ imported_count: number; earliest_play: string | null; latest_play: string | null; message: string }>;
  },
  overview: (source: MusicSource = "youtube") => request<Overview>(`/analysis/overview?${paramsWithSource(source).toString()}`),
  topTracks: (source: MusicSource = "youtube") => request<TopTrack[]>(`/analysis/top-tracks?${paramsWithSource(source).toString()}`),
  topArtists: (source: MusicSource = "youtube") => request<TopArtist[]>(`/analysis/top-artists?${paramsWithSource(source).toString()}`),
  scores: (period = "rolling_year", month?: string | null, source: MusicSource = "youtube") => {
    const params = paramsWithSource(source, { period, month });
    return request<ScoreMetric[]>(`/analysis/scores?${params.toString()}`);
  },
  charts: (period = "rolling_year", month?: string | null, source: MusicSource = "youtube") => {
    const params = paramsWithSource(source, { period, month });
    return request<Charts>(`/analysis/charts?${params.toString()}`);
  },
  listeningMinutes: (period = "rolling_year", month?: string | null, source: MusicSource = "youtube") => {
    const params = paramsWithSource(source, { period, month });
    return request<ListeningMinutes>(`/analytics/listening-minutes?${params.toString()}`);
  },
  periodTop: (period = "this_month", type: "tracks" | "artists" = "tracks", month?: string | null, source: MusicSource = "youtube") => {
    const params = paramsWithSource(source, { period, type, month });
    return request<PeriodTopResponse>(`/top?${params.toString()}`);
  },
  topAlbums: (period = "this_month", month?: string | null, source: MusicSource = "youtube") => {
    const params = paramsWithSource(source, { period, month });
    return request<TopAlbumsResponse>(`/top/albums?${params.toString()}`);
  },
  artistSongs: (artist: string, period = "this_month", month?: string | null, source: MusicSource = "youtube") => {
    const params = paramsWithSource(source, { artist, period, month });
    return request<TopArtistSongsResponse>(`/top/artist-songs?${params.toString()}`);
  },
  albumSongs: (album: string, artist: string | null | undefined, period = "this_month", month?: string | null, source: MusicSource = "youtube") => {
    const params = paramsWithSource(source, { album, artist, period, month });
    return request<TopAlbumSongsResponse>(`/top/album-songs?${params.toString()}`);
  },
  tasteDna: (period = "rolling_year", month?: string | null, source: MusicSource = "youtube") => {
    const params = paramsWithSource(source, { period, month });
    return request<TasteDnaExplorer>(`/taste-dna?${params.toString()}`);
  },
  tasteDnaCompare: (base = "rolling_year", compare = "this_month", month?: string | null, source: MusicSource = "youtube") => {
    const params = paramsWithSource(source, { base, compare, month });
    return request<TasteDnaComparison>(`/taste-dna/compare?${params.toString()}`);
  },
  scoreInterpretations: (period = "rolling_year", month?: string | null, source: MusicSource = "youtube") => {
    const params = paramsWithSource(source, { period, month });
    return request<ScoreMetric[]>(`/scores/interpretations?${params.toString()}`);
  },
  musicCharacter: (period = "rolling_year", month?: string | null, source: MusicSource = "youtube") => {
    const params = paramsWithSource(source, { period, month });
    return request<MusicCharacterResponse>(`/persona/character?${params.toString()}`);
  },
  rewriteMusicCharacter: (period = "rolling_year", month?: string | null, mode = "playful", source: MusicSource = "youtube") =>
    request<MusicCharacterRewrite>("/persona/character/rewrite", {
      method: "POST",
      body: JSON.stringify({ period, month, mode, source }),
    }),
  latestReport: (source: MusicSource = "youtube") => request<PersonaReport>(`/report/latest?${paramsWithSource(source).toString()}`),
  generateReport: (mode: "serious" | "playful" | "roast", source: MusicSource = "youtube") =>
    request<PersonaReport>("/report/generate", { method: "POST", body: JSON.stringify({ mode, source }) }),
  recommendations: () => request<Recommendation[]>("/recommendations"),
  generateRecommendations: () => request<Recommendation[]>("/recommendations/generate", { method: "POST", body: "{}" }),
  createPlaylist: (title: string) =>
    request<{ playlist_id: string; title: string; added_count: number; message: string }>("/recommendations/create-playlist", {
      method: "POST",
      body: JSON.stringify({ confirm: true, title }),
    }),
};
