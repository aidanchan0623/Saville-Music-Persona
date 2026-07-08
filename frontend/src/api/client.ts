import type {
  AuthStatus,
  Charts,
  ListeningMinutes,
  Overview,
  PersonaReport,
  TopAlbumSongsResponse,
  TopAlbumsResponse,
  TopArtistSongsResponse,
  PeriodTopResponse,
  Prerequisites,
  Recommendation,
  ScoreMetric,
  TasteDnaComparison,
  TasteDnaExplorer,
  TopArtist,
  TopTrack,
} from "../types/api";

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000/api";

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
  authStatus: () => request<AuthStatus>("/auth/status"),
  authSetup: () => request<Record<string, unknown>>("/auth/setup", { method: "POST", body: "{}" }),
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
  overview: () => request<Overview>("/analysis/overview"),
  topTracks: () => request<TopTrack[]>("/analysis/top-tracks"),
  topArtists: () => request<TopArtist[]>("/analysis/top-artists"),
  scores: (period = "rolling_year", month?: string | null) => {
    const params = new URLSearchParams({ period });
    if (month) params.set("month", month);
    return request<ScoreMetric[]>(`/analysis/scores?${params.toString()}`);
  },
  charts: (period = "rolling_year", month?: string | null) => {
    const params = new URLSearchParams({ period });
    if (month) params.set("month", month);
    return request<Charts>(`/analysis/charts?${params.toString()}`);
  },
  listeningMinutes: (period = "rolling_year", month?: string | null) => {
    const params = new URLSearchParams({ period });
    if (month) params.set("month", month);
    return request<ListeningMinutes>(`/analytics/listening-minutes?${params.toString()}`);
  },
  periodTop: (period = "this_month", type: "tracks" | "artists" = "tracks", month?: string | null) => {
    const params = new URLSearchParams({ period, type });
    if (month) params.set("month", month);
    return request<PeriodTopResponse>(`/top?${params.toString()}`);
  },
  topAlbums: (period = "this_month", month?: string | null) => {
    const params = new URLSearchParams({ period });
    if (month) params.set("month", month);
    return request<TopAlbumsResponse>(`/top/albums?${params.toString()}`);
  },
  artistSongs: (artist: string, period = "this_month", month?: string | null) => {
    const params = new URLSearchParams({ artist, period });
    if (month) params.set("month", month);
    return request<TopArtistSongsResponse>(`/top/artist-songs?${params.toString()}`);
  },
  albumSongs: (album: string, artist: string | null | undefined, period = "this_month", month?: string | null) => {
    const params = new URLSearchParams({ album, period });
    if (artist) params.set("artist", artist);
    if (month) params.set("month", month);
    return request<TopAlbumSongsResponse>(`/top/album-songs?${params.toString()}`);
  },
  tasteDna: (period = "rolling_year", month?: string | null) => {
    const params = new URLSearchParams({ period });
    if (month) params.set("month", month);
    return request<TasteDnaExplorer>(`/taste-dna?${params.toString()}`);
  },
  tasteDnaCompare: (base = "rolling_year", compare = "this_month", month?: string | null) => {
    const params = new URLSearchParams({ base, compare });
    if (month) params.set("month", month);
    return request<TasteDnaComparison>(`/taste-dna/compare?${params.toString()}`);
  },
  scoreInterpretations: (period = "rolling_year", month?: string | null) => {
    const params = new URLSearchParams({ period });
    if (month) params.set("month", month);
    return request<ScoreMetric[]>(`/scores/interpretations?${params.toString()}`);
  },
  latestReport: () => request<PersonaReport>("/report/latest"),
  generateReport: (mode: "serious" | "playful" | "roast") =>
    request<PersonaReport>("/report/generate", { method: "POST", body: JSON.stringify({ mode }) }),
  recommendations: () => request<Recommendation[]>("/recommendations"),
  generateRecommendations: () => request<Recommendation[]>("/recommendations/generate", { method: "POST", body: "{}" }),
  createPlaylist: (title: string) =>
    request<{ playlist_id: string; title: string; added_count: number; message: string }>("/recommendations/create-playlist", {
      method: "POST",
      body: JSON.stringify({ confirm: true, title }),
    }),
};
