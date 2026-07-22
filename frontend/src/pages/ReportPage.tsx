import { useEffect, useMemo, useState } from "react";
import { api } from "../api/client";
import type { MusicCharacterResponse, MusicSource, PersonaReport, Prerequisites, TopAlbumItem, TopArtist } from "../types/api";
import { PersonaStoryExperience } from "./report/PersonaStoryExperience";
import { buildPersonaStory } from "./report/personaStoryModel";
import "./ReportPage.css";

interface Props {
  report: PersonaReport | null;
  prerequisites: Prerequisites | null;
  busy: boolean;
  topArtists: TopArtist[];
  onGenerate: (mode: "serious" | "playful" | "roast") => void;
  source: MusicSource;
  titleAnimationKey: string;
}

export function ReportPage({ report, prerequisites, busy, topArtists, onGenerate, source, titleAnimationKey }: Props) {
  const [rollingCharacter, setRollingCharacter] = useState<MusicCharacterResponse | null>(null);
  const [currentCharacter, setCurrentCharacter] = useState<MusicCharacterResponse | null>(null);
  const [favouriteAlbums, setFavouriteAlbums] = useState<TopAlbumItem[]>([]);
  const [characterError, setCharacterError] = useState<string | null>(null);
  const [loadingCharacter, setLoadingCharacter] = useState(true);

  useEffect(() => {
    let active = true;
    setLoadingCharacter(true);
    setFavouriteAlbums([]);
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

  useEffect(() => {
    let active = true;
    setFavouriteAlbums([]);
    api.topAlbums("rolling_year", null, source)
      .then((albums) => {
        if (active) setFavouriteAlbums(albums.albums);
      })
      .catch(() => {
        if (active) setFavouriteAlbums([]);
      });
    return () => {
      active = false;
    };
  }, [source]);

  const story = useMemo(
    () => buildPersonaStory(report, rollingCharacter, currentCharacter, topArtists),
    [report, rollingCharacter, currentCharacter, topArtists],
  );
  const reportEvidenceAlbums = useMemo(() => albumsFromReportEvidence(report), [report]);
  const storyAlbums = favouriteAlbums.length ? favouriteAlbums : reportEvidenceAlbums;
  const modelReady = Boolean(prerequisites?.ollama_reachable && prerequisites.model_installed);

  if (!story && loadingCharacter) {
    return (
      <section className="persona-report-empty" aria-live="polite">
        <p className="persona-report-empty__eyebrow">Persona Report</p>
        <h1 key={titleAnimationKey}>Reading your music character</h1>
        <p>Building the deterministic persona profile from your local listening data.</p>
      </section>
    );
  }

  if (!story) {
    return (
      <section className="persona-report-empty">
        <p className="persona-report-empty__eyebrow">Persona Report</p>
        <h1 key={titleAnimationKey}>No persona story yet</h1>
        <p>
          {characterError ||
            (source === "spotify"
              ? "Connect Spotify and refresh Spotify data, then return here for a music persona story."
              : "Refresh YouTube Music data or import Google Takeout history, then return here for a music persona story.")}
        </p>
      </section>
    );
  }

  return (
    <PersonaStoryExperience
      story={story}
      rollingCharacter={rollingCharacter}
      currentCharacter={currentCharacter}
      favouriteAlbums={storyAlbums}
      topArtists={topArtists}
      prerequisitesModelReady={modelReady}
      busy={busy}
      onGenerate={onGenerate}
      source={source}
      titleAnimationKey={titleAnimationKey}
    />
  );
}

function albumsFromReportEvidence(report: PersonaReport | null): TopAlbumItem[] {
  const evidence = report?.evidence as { favourite_albums?: unknown } | undefined;
  const items = Array.isArray(evidence?.favourite_albums) ? evidence.favourite_albums : [];
  const albums: TopAlbumItem[] = [];
  for (const item of items) {
    if (!item || typeof item !== "object") continue;
    const record = item as Record<string, unknown>;
    const album = String(record.album || "").trim();
    const artist = String(record.artist || "").trim();
    const albumImageUrl = String(record.album_image_url || "").trim();
    if (!album || !artist || !albumImageUrl) continue;
    const albumId = String(record.album_id || "").trim() || null;
    const plays = Number(record.plays || 0);
    const uniqueSongs = Number(record.unique_songs || 0);
    albums.push({
      rank: albums.length + 1,
      key: albumId || `${album}::${artist}`,
      album,
      artist,
      album_id: albumId,
      thumbnail: albumImageUrl,
      album_image_url: albumImageUrl,
      album_image_source: "report_evidence",
      plays: Number.isFinite(plays) ? plays : 0,
      detected_minutes: 0,
      detected_minutes_formatted: "",
      unique_songs: Number.isFinite(uniqueSongs) ? uniqueSongs : 0,
      most_played_song: null,
      share: Number(record.share || 0),
      duration_coverage_percent: 0,
      last_played: null,
      label: "Saved report album signal",
      album_signal_note: "Album cover carried from saved report evidence.",
    });
    if (albums.length >= 8) break;
  }
  return albums;
}
