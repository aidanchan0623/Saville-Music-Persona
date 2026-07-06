import type {
  AuthStatus,
  Charts,
  Overview,
  PersonaReport,
  Prerequisites,
  Recommendation,
  ScoreMetric,
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
  overview: () => request<Overview>("/analysis/overview"),
  topTracks: () => request<TopTrack[]>("/analysis/top-tracks"),
  topArtists: () => request<TopArtist[]>("/analysis/top-artists"),
  scores: () => request<ScoreMetric[]>("/analysis/scores"),
  charts: () => request<Charts>("/analysis/charts"),
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

