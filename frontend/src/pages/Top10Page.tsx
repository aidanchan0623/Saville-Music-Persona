import { ArtistCard } from "../components/ArtistCard";
import { EmptyState } from "../components/EmptyState";
import { TrackCard } from "../components/TrackCard";
import type { TopArtist, TopTrack } from "../types/api";

export function Top10Page({ tracks, artists }: { tracks: TopTrack[]; artists: TopArtist[] }) {
  if (!tracks.length && !artists.length) {
    return <EmptyState title="No rankings yet" body="Refresh your music data to build ranked songs and artists from detected plays." />;
  }
  return (
    <div className="space-y-10">
      <section>
        <div className="mb-5">
          <h1 className="text-3xl font-bold text-white">Top 10 Songs</h1>
          <p className="mt-2 text-mist">Ranked mainly by detected play count, with recency used only as a tie-breaker.</p>
        </div>
        <div className="grid gap-4">{tracks.map((track) => <TrackCard key={track.track_id} track={track} />)}</div>
      </section>
      <section>
        <div className="mb-5">
          <h1 className="text-3xl font-bold text-white">Top 10 Artists</h1>
          <p className="mt-2 text-mist">Artist share, unique songs, comfort labels, and evidence-based observations.</p>
        </div>
        <div className="grid gap-4 lg:grid-cols-2">{artists.map((artist) => <ArtistCard key={artist.artist} artist={artist} />)}</div>
      </section>
    </div>
  );
}

