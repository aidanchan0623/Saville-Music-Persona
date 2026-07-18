import { ExternalLink, Music2 } from "lucide-react";
import type { MusicSource, SpotifyStatus } from "../../types/api";

interface SourceControlProps {
  source: MusicSource;
  spotifyStatus: SpotifyStatus | null;
  onChange: (source: MusicSource) => void;
  onConnectSpotify: () => void;
}

export function SourceControl({ source, spotifyStatus, onChange, onConnectSpotify }: SourceControlProps) {
  const spotifyDisabled = !spotifyStatus?.connected;

  return (
    <section className="sticky top-0 z-20 mb-6 border-b border-white/10 bg-[#050303]/82 py-3 backdrop-blur-2xl lg:top-0">
      <div className="flex flex-col gap-3 rounded-lg border border-white/10 bg-white/[0.035] p-3 md:flex-row md:items-center md:justify-between">
        <div className="flex items-center gap-3">
          <span className="grid h-10 w-10 shrink-0 place-items-center rounded-lg border border-red-400/25 bg-red-500/12 text-red-100">
            <Music2 size={18} />
          </span>
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.2em] text-mist/60">Music source</p>
            <p className="mt-1 text-sm font-semibold text-white">
              Analysing <span className="text-red-100">{source === "spotify" ? "Spotify" : "YouTube Music"}</span>
            </p>
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <button type="button" className={sourceButtonClass(source === "youtube")} onClick={() => onChange("youtube")}>
            YouTube Music
          </button>
          <button type="button" className={sourceButtonClass(source === "spotify")} onClick={() => onChange("spotify")} aria-describedby={spotifyDisabled ? "spotify-source-note" : undefined}>
            Spotify
          </button>
          {spotifyDisabled ? (
            <button type="button" className="btn-secondary" onClick={onConnectSpotify}>
              <ExternalLink size={16} /> Connect
            </button>
          ) : null}
        </div>
      </div>
      {source === "spotify" ? (
        <p id="spotify-source-note" className="mt-2 text-xs leading-5 text-mist/75">
          Spotify uses top items, saved music, playlists, and recent sync signals. Full historical play counts are not exposed by Spotify.
        </p>
      ) : null}
    </section>
  );
}

function sourceButtonClass(active: boolean) {
  return `rounded-md px-3 py-2 text-sm font-semibold transition focus:outline-none focus-visible:ring-2 focus-visible:ring-red-400 ${
    active ? "bg-red-600 text-white shadow-[0_0_22px_rgba(220,38,38,0.28)]" : "bg-white/[0.06] text-mist hover:bg-white/[0.1] hover:text-white"
  }`;
}
