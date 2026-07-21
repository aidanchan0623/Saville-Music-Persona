import type { TopArtist } from "../types/api";
import { ArtistAvatar } from "./Artwork";
import { GlowPanel } from "./GlowPanel";

export function ArtistCard({ artist }: { artist: TopArtist }) {
  return (
    <GlowPanel as="article" variant="card" className="p-5 transition">
      <div className="flex items-start gap-4">
        <ArtistAvatar artistImageUrl={artist.artist_image_url} artistName={artist.artist} size="md" fallbackLabel={artist.artist.slice(0, 2).toUpperCase()} />
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-3">
            <span className="text-2xl font-black text-white/20">#{artist.rank}</span>
            <h3 className="text-2xl font-black leading-tight text-white">{artist.artist}</h3>
          </div>
          <p className="mt-1 text-sm text-red-100">{artist.artist_loyalty_label}</p>
        </div>
      </div>
      <dl className="mt-5 grid grid-cols-3 gap-3 border-t border-white/10 pt-4 text-sm">
        <div>
          <dt className="text-mist/70">Plays</dt>
          <dd className="mt-1 font-semibold text-white">{artist.play_count}</dd>
        </div>
        <div>
          <dt className="text-mist/70">Share</dt>
          <dd className="mt-1 font-semibold text-white">{artist.share_of_listens}%</dd>
        </div>
        <div>
          <dt className="text-mist/70">Songs</dt>
          <dd className="mt-1 font-semibold text-white">{artist.unique_songs_played}</dd>
        </div>
      </dl>
      <p className="mt-4 text-sm font-semibold text-red-100">{artist.taste_role || artist.artist_loyalty_label}</p>
      <p className="mt-2 text-sm leading-6 text-mist">{artist.why_it_matters || artist.observation}</p>
      <p className="mt-3 text-xs text-mist/75">Most played: {artist.most_played_song || "Unavailable"}</p>
      <div className="mt-4 space-y-3">
        <InlineGroup title="Genre tags" items={artist.genre_profile?.display_genres?.length ? artist.genre_profile.display_genres : ["Still learning"]} />
        <InlineGroup title="Sound family" items={artist.broad_clusters?.length ? artist.broad_clusters : ["Still learning"]} />
      </div>
    </GlowPanel>
  );
}

function InlineGroup({ title, items }: { title: string; items: string[] }) {
  return (
    <div>
      <p className="mb-2 text-xs uppercase tracking-[0.14em] text-mist/60">{title}</p>
      <p className="text-sm leading-6 text-mist">{items.join(" / ")}</p>
    </div>
  );
}
