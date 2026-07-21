import type { TopTrack } from "../types/api";
import { formatDate } from "../utils/format";
import { TrackArtwork } from "./Artwork";
import { GlowPanel } from "./GlowPanel";

export function TrackCard({ track }: { track: TopTrack }) {
  return (
    <GlowPanel as="article" variant="row" className="group grid grid-cols-[3rem_4.5rem_1fr] gap-4 p-4 transition">
      <div className="text-3xl font-black text-white/20">#{track.rank}</div>
      <TrackArtwork trackImageUrl={track.track_image_url} albumArtUrl={track.album_art_url} title={track.title} size="sm" fallbackLabel={`#${track.rank}`} className="track-card-artwork" />
      <div className="min-w-0">
        <h3 className="text-lg font-semibold leading-6 text-white">{track.title}</h3>
        <p className="mt-1 text-sm leading-5 text-red-100">{track.artist}</p>
        <p className="mt-1 text-sm leading-5 text-mist">{track.album || "Album unavailable"} {track.release_year ? `- ${track.release_year}` : ""}</p>
        <p className="mt-3 text-xs leading-5 text-mist">{track.play_count} detected plays / Last played {formatDate(track.last_played)}</p>
        <p className="mt-3 text-sm leading-6 text-mist">{track.why_it_ranked}</p>
      </div>
    </GlowPanel>
  );
}
