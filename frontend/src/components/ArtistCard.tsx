import type { TopArtist } from "../types/api";
import { Artwork } from "./Artwork";
import { GlowPanel } from "./GlowPanel";

export function ArtistCard({ artist }: { artist: TopArtist }) {
  return (
    <GlowPanel as="article" variant="card" className="p-5 transition">
      <div className="flex items-start gap-4">
        <Artwork src={artist.image} alt={artist.artist} kind="artist" size="md" fallbackLabel={artist.artist.slice(0, 2).toUpperCase()} />
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-3">
            <span className="text-2xl font-black text-white/20">#{artist.rank}</span>
            <h3 className="truncate text-2xl font-black text-white">{artist.artist}</h3>
          </div>
          <p className="mt-1 text-sm text-violet-200">{artist.artist_loyalty_label}</p>
        </div>
      </div>
      <dl className="mt-5 grid grid-cols-3 gap-3 text-sm">
        <div className="rounded-md bg-white/[0.04] p-3">
          <dt className="text-mist/70">Plays</dt>
          <dd className="mt-1 font-semibold text-white">{artist.play_count}</dd>
        </div>
        <div className="rounded-md bg-white/[0.04] p-3">
          <dt className="text-mist/70">Share</dt>
          <dd className="mt-1 font-semibold text-white">{artist.share_of_listens}%</dd>
        </div>
        <div className="rounded-md bg-white/[0.04] p-3">
          <dt className="text-mist/70">Songs</dt>
          <dd className="mt-1 font-semibold text-white">{artist.unique_songs_played}</dd>
        </div>
      </dl>
      <p className="mt-4 text-sm font-semibold text-violet-100">{artist.taste_role || artist.artist_loyalty_label}</p>
      <p className="mt-2 text-sm leading-6 text-mist">{artist.why_it_matters || artist.observation}</p>
      <p className="mt-3 text-xs text-mist/75">Most played: {artist.most_played_song || "Unavailable"}</p>
      <div className="mt-4 space-y-3">
        <ChipGroup title="Genre tags" items={artist.genre_profile?.display_genres?.length ? artist.genre_profile.display_genres : ["Still learning"]} muted={!artist.genre_profile?.display_genres?.length} />
        <ChipGroup title="Sound family" items={artist.broad_clusters?.length ? artist.broad_clusters : ["Still learning"]} muted={!artist.broad_clusters?.length} />
      </div>
    </GlowPanel>
  );
}

function ChipGroup({ title, items, muted = false }: { title: string; items: string[]; muted?: boolean }) {
  return (
    <div>
      <p className="mb-2 text-xs uppercase tracking-[0.14em] text-mist/60">{title}</p>
      <div className="flex flex-wrap gap-2">
        {items.map((item) => (
          <span key={item} className={`rounded-full border px-3 py-1 text-xs ${muted ? "border-white/10 text-mist/60" : "border-violet/25 bg-violet/10 text-violet-100"}`}>
            {item}
          </span>
        ))}
      </div>
    </div>
  );
}
