export interface Coverage {
  earliest_detected_play: string | null;
  latest_detected_play: string | null;
  earliest_available_play: string | null;
  days_represented: number;
  full_365_day_analysis: boolean;
  dated_history_items: number;
  undated_history_items: number;
  history_items_returned: number;
  date_data_available: boolean;
  history_coverage_status: string;
  notes: string[];
}

export interface ScoreMetric {
  key: string;
  name: string;
  value: number;
  label: string;
  explanation: string;
  formula: string;
  inputs: Record<string, unknown>;
}

export interface TopTrack {
  rank: number;
  track_id: string;
  video_id: string | null;
  title: string;
  artist: string;
  artists: string[];
  album: string | null;
  release_year: number | null;
  thumbnail: string | null;
  play_count: number;
  last_played: string | null;
  why_it_ranked: string;
  genre_clusters: string[];
}

export interface TopArtist {
  rank: number;
  artist: string;
  artist_id: string | null;
  image: string | null;
  play_count: number;
  share_of_listens: number;
  unique_songs_played: number;
  most_played_song: string | null;
  artist_loyalty_label: string;
  related_genres: string[];
  observation: string;
}

export interface Overview {
  headline_persona: string;
  top_3_artists: TopArtist[];
  top_3_tracks: TopTrack[];
  top_genre_cluster: string;
  favourite_decade: string;
  repeat_score: ScoreMetric;
  discovery_score: ScoreMetric;
  taste_confidence: ScoreMetric;
  last_refreshed_at: string | null;
  coverage: Coverage;
  total_detected_plays: number;
  unique_tracks: number;
  unique_artists: number;
  use_demo: boolean;
  warnings: string[];
}

export interface ChartPoint {
  name: string;
  value: number;
}

export interface Charts {
  release_decades: ChartPoint[];
  top_genre_clusters: ChartPoint[];
  top_artists: ChartPoint[];
  most_repeated_songs: ChartPoint[];
  artist_concentration: ChartPoint[];
  playlist_influence: ChartPoint[];
  coverage_timeline: ChartPoint[];
}

export interface PrerequisiteItem {
  name: string;
  available: boolean;
  detail: string;
}

export interface Prerequisites {
  ok: boolean;
  items: PrerequisiteItem[];
  ollama_model: string;
  ollama_reachable: boolean;
  model_installed: boolean;
}

export interface AuthStatus {
  connected: boolean;
  auth_file_exists: boolean;
  auth_file_path: string;
  oauth_client_configured: boolean;
  account_name: string | null;
  message: string;
}

export interface PersonaTag {
  tag: string;
  reason: string;
}

export interface PersonaReport {
  headline: string;
  summary: string;
  current_era: string;
  core_identity: string;
  listening_habits: string;
  comfort_artists: string;
  personality_tags: PersonaTag[];
  report_sections: string[];
  recommendation_explanations: Record<string, string>[];
  mode: string;
  model: string;
  evidence: Record<string, unknown>;
  generated_at: string;
}

export interface Recommendation {
  rank: number;
  track_title: string;
  artist: string;
  artists: string[];
  album: string | null;
  album_art: string | null;
  release_year: number | null;
  video_id: string | null;
  recommendation_type: "Safe" | "Adjacent" | "Discovery" | string;
  why_this_fits: string;
  source_reason: string;
  score: number;
}

