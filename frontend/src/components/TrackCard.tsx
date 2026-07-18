import type { TopTrack } from "../types/api";
import { formatDate } from "../utils/format";

export function TrackCard({ track }: { track: TopTrack }) {
  return (
    <article className="group grid grid-cols-[3rem_4.5rem_1fr] gap-4 rounded-lg border border-line bg-panel/80 p-4 transition hover:border-violet/40 hover:bg-panelSoft/85">
      <div className="text-3xl font-black text-white/20">#{track.rank}</div>
      <div className="h-[4.5rem] w-[4.5rem] overflow-hidden rounded-md bg-white/10">
        {track.thumbnail ? <img className="h-full w-full object-cover" src={track.thumbnail} alt="" /> : <div className="h-full w-full bg-violet/20" />}
      </div>
      <div className="min-w-0">
        <h3 className="truncate text-lg font-semibold text-white">{track.title}</h3>
        <p className="mt-1 truncate text-sm text-violet-100">{track.artist}</p>
        <p className="mt-1 truncate text-sm text-mist">{track.album || "Album unavailable"} {track.release_year ? `- ${track.release_year}` : ""}</p>
        <div className="mt-3 flex flex-wrap gap-2 text-xs text-mist">
          <span className="rounded-full bg-white/10 px-3 py-1">{track.play_count} detected plays</span>
          <span className="rounded-full bg-white/10 px-3 py-1">Last played {formatDate(track.last_played)}</span>
        </div>
        <p className="mt-3 text-sm leading-6 text-mist">{track.why_it_ranked}</p>
      </div>
    </article>
  );
}
