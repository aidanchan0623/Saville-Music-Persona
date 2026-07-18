import { ArrowDown, ArrowUp, Minus, Sparkles, X } from "lucide-react";
import type { ReactNode } from "react";
import { useEffect, useState } from "react";
import { api } from "../api/client";
import { EmptyState } from "../components/EmptyState";
import { Artwork } from "../components/ui/Artwork";
import { MetricBlock } from "../components/ui/MetricBlock";
import { PageHeader } from "../components/ui/PageHeader";
import { PeriodSelector, type PeriodValue, standardPeriodOptions } from "../components/ui/PeriodSelector";
import type {
  MusicSource,
  PeriodTopItem,
  PeriodTopResponse,
  TopAlbumItem,
  TopAlbumSongsResponse,
  TopAlbumsResponse,
  TopArtistSongsResponse,
  TopDrilldownSong,
} from "../types/api";
import { formatDate } from "../utils/format";

export function Top10Page({ source }: { source: MusicSource }) {
  const [period, setPeriod] = useState<PeriodValue>("this_month");
  const [selectedMonth, setSelectedMonth] = useState<string | null>(null);
  const [tracks, setTracks] = useState<PeriodTopResponse | null>(null);
  const [artists, setArtists] = useState<PeriodTopResponse | null>(null);
  const [albums, setAlbums] = useState<TopAlbumsResponse | null>(null);
  const [selectedArtist, setSelectedArtist] = useState<string | null>(null);
  const [artistSongs, setArtistSongs] = useState<TopArtistSongsResponse | null>(null);
  const [selectedAlbum, setSelectedAlbum] = useState<TopAlbumItem | null>(null);
  const [albumSongs, setAlbumSongs] = useState<TopAlbumSongsResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [artistLoading, setArtistLoading] = useState(false);
  const [albumLoading, setAlbumLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    Promise.all([
      api.periodTop(period, "tracks", period === "month" ? selectedMonth : null, source),
      api.periodTop(period, "artists", period === "month" ? selectedMonth : null, source),
      api.topAlbums(period, period === "month" ? selectedMonth : null, source),
    ])
      .then(([nextTracks, nextArtists, nextAlbums]) => {
        if (cancelled) return;
        setTracks(nextTracks);
        setArtists(nextArtists);
        setAlbums(nextAlbums);
        const availableMonths = nextTracks.period.available_months.length ? nextTracks.period.available_months : nextAlbums.period.available_months;
        if (!selectedMonth && availableMonths.length) {
          setSelectedMonth(availableMonths[availableMonths.length - 1].value);
        }
      })
      .catch((nextError: Error) => {
        if (!cancelled) setError(nextError.message);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [period, selectedMonth, source]);

  useEffect(() => {
    if (!selectedArtist) {
      setArtistSongs(null);
      return;
    }
    let cancelled = false;
    setArtistLoading(true);
    api.artistSongs(selectedArtist, period, period === "month" ? selectedMonth : null, source)
      .then((next) => {
        if (!cancelled) setArtistSongs(next);
      })
      .catch(() => {
        if (!cancelled) setArtistSongs(null);
      })
      .finally(() => {
        if (!cancelled) setArtistLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [selectedArtist, period, selectedMonth, source]);

  useEffect(() => {
    if (!selectedAlbum) {
      setAlbumSongs(null);
      return;
    }
    let cancelled = false;
    setAlbumLoading(true);
    api.albumSongs(selectedAlbum.album, selectedAlbum.artist, period, period === "month" ? selectedMonth : null, source)
      .then((next) => {
        if (!cancelled) setAlbumSongs(next);
      })
      .catch(() => {
        if (!cancelled) setAlbumSongs(null);
      })
      .finally(() => {
        if (!cancelled) setAlbumLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [selectedAlbum, period, selectedMonth, source]);

  const months = tracks?.period.available_months ?? artists?.period.available_months ?? albums?.period.available_months ?? [];
  const activeLabel = displayPeriodLabel(tracks?.period.label ?? albums?.period.label, period);
  const detectedPlayLabel = source === "spotify" ? "local signals" : "detected plays";

  if (!tracks && !artists && !albums && !loading) {
    return <EmptyState title="No rankings yet" body="Refresh your music data to build period rankings from detected plays." />;
  }

  return (
    <div className="space-y-9">
      <section className="editorial-panel overflow-hidden">
        <div className="p-5 md:p-8">
          <PageHeader
            eyebrow="Music leaders"
            title="Top 10"
            description={source === "spotify" ? "Spotify-backed leaders from top items, saved music, playlists, and recent sync signals." : "The songs, artists, and albums defining this slice of your listening."}
            action={<PeriodSelector value={period} onChange={setPeriod} month={selectedMonth} months={months} onMonthChange={setSelectedMonth} options={standardPeriodOptions} />}
            meta={
              <>
                <span className="subtle-pill border-red-400/20 bg-red-500/10 text-red-100">{activeLabel}</span>
                <span className="subtle-pill">{tracks?.period.start_date} to {tracks?.period.end_date}</span>
                <span className="subtle-pill">{(tracks?.total_play_count ?? 0).toLocaleString()} {detectedPlayLabel}</span>
                {loading ? <span className="subtle-pill border-red-400/20 bg-red-500/10 text-red-100">Updating</span> : null}
              </>
            }
          />
        </div>
        <div className="grid gap-px border-t border-white/10 bg-white/10 md:grid-cols-3">
          <MetricBlock label="Ranked plays" value={(tracks?.ranked_music_play_count ?? 0).toLocaleString()} caption="Music-only events in this period" index={1} />
          <MetricBlock label="Top song" value={tracks?.items[0]?.title ?? "Still forming"} caption={tracks?.items[0]?.artist ?? "No detected leader"} index={2} />
          <MetricBlock label="Top artist" value={artists?.items[0]?.artist ?? "Still forming"} caption={artists?.items[0]?.most_played_song ?? "No artist anchor yet"} index={3} />
        </div>
      </section>

      {(tracks?.sample_warning || albums?.sample_warning || error) ? (
        <section className="space-y-3">
          {tracks?.sample_warning ? <p className="rounded-lg border border-amber-200/10 bg-amber-200/10 p-4 text-sm text-amber-100">{tracks.sample_warning}</p> : null}
          {albums?.sample_warning ? <p className="rounded-lg border border-amber-200/10 bg-amber-200/10 p-4 text-sm text-amber-100">{albums.sample_warning}</p> : null}
          {error ? <p className="rounded-lg border border-red-300/10 bg-red-400/10 p-4 text-sm text-red-100">{error}</p> : null}
        </section>
      ) : null}

      <TopSongsPanel response={tracks} loading={loading} source={source} />
      <TopArtistsPanel response={artists} loading={loading} selectedArtist={selectedArtist} onViewSongs={setSelectedArtist} source={source} />

      {selectedArtist ? <ArtistDrilldownPanel artist={selectedArtist} response={artistSongs} loading={artistLoading} onClose={() => setSelectedArtist(null)} /> : null}

      <FavouriteAlbumsSection response={albums} loading={loading} selectedAlbum={selectedAlbum} onViewSongs={setSelectedAlbum} source={source} />

      {selectedAlbum ? <AlbumDrilldownPanel album={selectedAlbum} response={albumSongs} loading={albumLoading} onClose={() => setSelectedAlbum(null)} /> : null}
    </div>
  );
}

function TopSongsPanel({ response, loading, source }: { response: PeriodTopResponse | null; loading: boolean; source: MusicSource }) {
  const maxCount = Math.max(...(response?.items.map((item) => item.play_count) ?? [1]), 1);
  return (
    <section className="editorial-panel p-5 md:p-7">
      <PanelIntro title="Top Songs" caption={source === "spotify" ? "Your strongest Spotify top-track signals. Exact lifetime play counts are not available from Spotify." : "Your clearest song leaders, ranked by local play history."} loading={loading} />
      <div className="mt-6 space-y-3">
        {response?.items.length ? response.items.map((item) => <RankedSongRow key={item.key} item={item} maxCount={maxCount} source={source} />) : <EmptyRanking text="No detected songs in this period." />}
      </div>
    </section>
  );
}

function TopArtistsPanel({
  response,
  loading,
  selectedArtist,
  onViewSongs,
  source,
}: {
  response: PeriodTopResponse | null;
  loading: boolean;
  selectedArtist: string | null;
  onViewSongs: (artist: string) => void;
  source: MusicSource;
}) {
  return (
    <section className="editorial-panel p-5 md:p-7">
      <PanelIntro title="Top Artists" caption={source === "spotify" ? "Official Spotify artist images and genres where available." : "The artists pulling the most attention in this period."} loading={loading} />
      <div className="mt-6 grid gap-4 xl:grid-cols-2">
        {response?.items.length ? (
          response.items.map((item) => <RankedArtistCard key={item.key} item={item} selected={selectedArtist === item.artist} onViewSongs={onViewSongs} source={source} />)
        ) : (
          <EmptyRanking text="No detected artists in this period." />
        )}
      </div>
    </section>
  );
}

function RankedSongRow({ item, maxCount, source }: { item: PeriodTopItem; maxCount: number; source: MusicSource }) {
  const title = item.title ?? "Unknown track";
  const width = Math.max(5, (item.play_count / maxCount) * 100);
  return (
    <article className="group rounded-lg border border-white/10 bg-black/20 p-4 transition hover:border-red-400/45" data-testid="top-song-card">
      <div className="grid gap-4 sm:grid-cols-[5.5rem_1fr] lg:grid-cols-[6rem_1fr_auto] lg:items-center">
        <Artwork src={item.thumbnail} alt={title} className="h-24 w-24" />
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            <span className="font-display text-3xl leading-none text-red-200">#{String(item.rank).padStart(2, "0")}</span>
            <span className="rounded-full border border-red-400/25 bg-red-500/10 px-3 py-1 text-xs font-semibold text-red-100">{displayListLabel(item.interpretation_label, false)}</span>
          </div>
          <h3 className="mt-3 truncate text-2xl font-black leading-tight text-white">{title}</h3>
          <p className="truncate text-sm font-semibold text-mist">{item.artist}</p>
          {item.album ? <p className="mt-1 truncate text-xs text-mist/70">{item.album}</p> : null}
          <div className="mt-4 h-1.5 overflow-hidden rounded-full bg-white/10">
            <div className="h-full rounded-full bg-gradient-to-r from-red-800 via-red-500 to-red-200" style={{ width: `${width}%` }} />
          </div>
        </div>
        <div className="flex flex-wrap items-center gap-3 lg:flex-col lg:items-end">
          <span className="text-2xl font-black text-white">{spotifyEvidenceLabel(item, source, false)}</span>
          <Movement movement={item.movement} />
        </div>
      </div>
    </article>
  );
}

function RankedArtistCard({ item, selected, onViewSongs, source }: { item: PeriodTopItem; selected: boolean; onViewSongs: (artist: string) => void; source: MusicSource }) {
  return (
    <article className={`rounded-lg border bg-black/20 p-5 transition hover:border-red-400/45 ${selected ? "border-red-400/70" : "border-white/10"}`} data-testid="top-artist-card">
      <div className="grid gap-5 sm:grid-cols-[6.5rem_1fr]">
        <Artwork src={item.thumbnail} alt={item.artist} rounded="circle" className="h-28 w-28" />
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-3">
            <span className="font-display text-3xl leading-none text-red-200">#{String(item.rank).padStart(2, "0")}</span>
            <span className="rounded-full border border-red-400/25 bg-red-500/10 px-3 py-1 text-xs font-semibold text-red-100">{displayListLabel(item.interpretation_label, true)}</span>
          </div>
          <h3 className="mt-3 truncate text-2xl font-black leading-tight text-white">{item.artist}</h3>
          <p className="mt-2 text-sm leading-6 text-mist">
            {item.unique_songs ?? 0} unique songs{item.most_played_song ? `, top song: ${item.most_played_song}` : ""}
          </p>
          <MetricPills items={[spotifyEvidenceLabel(item, source, true), item.detected_minutes_formatted, item.share_of_period ? `${item.share_of_period}% share` : null]} />
          <button className="mt-5 rounded-md border border-white/10 px-4 py-2.5 text-sm font-semibold text-white transition hover:border-red-400/50 hover:bg-red-500/15" type="button" onClick={() => onViewSongs(item.artist)}>
            View songs
          </button>
        </div>
      </div>
    </article>
  );
}

function FavouriteAlbumsSection({ response, loading, selectedAlbum, onViewSongs, source }: { response: TopAlbumsResponse | null; loading: boolean; selectedAlbum: TopAlbumItem | null; onViewSongs: (album: TopAlbumItem) => void; source: MusicSource }) {
  return (
    <section className="editorial-panel p-5 md:p-7">
      <PanelIntro title="Favourite Albums" caption={source === "spotify" ? "Projects with the strongest album-level signal from Spotify top tracks, saved music, playlists, and recent sync data." : "Projects with the strongest pull across your local plays."} loading={loading} />
      {response?.albums.length ? (
        <div className="mt-6 grid gap-4 xl:grid-cols-2">
          {response.albums.map((album) => <AlbumCard key={album.key} album={album} selected={selectedAlbum?.key === album.key} onViewSongs={onViewSongs} source={source} />)}
        </div>
      ) : (
        <EmptyRanking text="Album data is unavailable for this period." />
      )}
    </section>
  );
}

function AlbumCard({ album, selected, onViewSongs, source }: { album: TopAlbumItem; selected: boolean; onViewSongs: (album: TopAlbumItem) => void; source: MusicSource }) {
  return (
    <article className={`rounded-lg border bg-black/20 p-5 transition hover:border-red-400/45 ${selected ? "border-red-400/70" : "border-white/10"}`} data-testid="top-album-card">
      <div className="grid gap-5 sm:grid-cols-[7rem_1fr] lg:grid-cols-[8rem_1fr_auto]">
        <Artwork src={album.thumbnail} alt={album.album} className="h-28 w-28 md:h-32 md:w-32" />
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-3">
            <span className="font-display text-3xl leading-none text-red-200">#{String(album.rank).padStart(2, "0")}</span>
            <span className="rounded-full border border-red-400/25 bg-red-500/10 px-3 py-1 text-xs font-semibold text-red-100">{album.label}</span>
          </div>
          <h3 className="mt-3 truncate text-2xl font-black leading-tight text-white">{album.album}</h3>
          <p className="mt-2 truncate text-base font-semibold text-mist">{album.artist}</p>
          <MetricPills items={[source === "spotify" ? `${album.plays.toLocaleString()} signals` : `${album.plays.toLocaleString()} plays`, `${album.unique_songs} songs`, album.detected_minutes_formatted]} />
          <p className="mt-3 text-sm leading-6 text-mist/90">{album.album_signal_note}</p>
        </div>
        <div className="flex items-start justify-end">
          <button className="whitespace-nowrap rounded-md border border-white/10 px-4 py-2.5 text-sm font-semibold text-white transition hover:border-red-400/50 hover:bg-red-500/15" type="button" onClick={() => onViewSongs(album)}>
            View songs
          </button>
        </div>
      </div>
    </article>
  );
}

function ArtistDrilldownPanel({ artist, response, loading, onClose }: { artist: string; response: TopArtistSongsResponse | null; loading: boolean; onClose: () => void }) {
  return (
    <DrilldownShell
      title={`Songs by ${artist}`}
      subtitle={response?.period_label ?? "Selected Period"}
      visual={<Artwork src={response?.artist_thumbnail} alt={artist} rounded="circle" className="h-24 w-24" />}
      loading={loading}
      onClose={onClose}
      emptyMessage="Song-level data for this artist is not available in the selected period."
      summary={response ? [`${response.total_plays} total plays`, `${response.unique_songs} unique songs`, response.most_replayed_song ? `Most replayed: ${response.most_replayed_song}` : null] : []}
      songs={response?.songs ?? []}
    />
  );
}

function AlbumDrilldownPanel({ album, response, loading, onClose }: { album: TopAlbumItem; response: TopAlbumSongsResponse | null; loading: boolean; onClose: () => void }) {
  return (
    <DrilldownShell
      title={`Songs from ${album.album}`}
      subtitle={response?.period_label ?? album.artist}
      visual={<Artwork src={album.thumbnail} alt={album.album} className="h-24 w-24" />}
      loading={loading}
      onClose={onClose}
      emptyMessage="Album data is unavailable for this period."
      summary={response ? [`${response.total_plays} total plays`, `${response.unique_songs} unique songs`, response.most_played_song ? `Most played: ${response.most_played_song}` : null] : []}
      songs={response?.songs ?? []}
    />
  );
}

function DrilldownShell({
  title,
  subtitle,
  visual,
  loading,
  onClose,
  emptyMessage,
  summary,
  songs,
}: {
  title: string;
  subtitle: string;
  visual?: ReactNode;
  loading: boolean;
  onClose: () => void;
  emptyMessage: string;
  summary: (string | null)[];
  songs: TopDrilldownSong[];
}) {
  return (
    <section className="editorial-panel p-5 md:p-6" data-testid="songs-drilldown">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div className="flex flex-col gap-4 sm:flex-row sm:items-center">
          {visual}
          <div>
            <p className="section-label">Drilldown</p>
            <h2 className="mt-2 text-3xl font-black text-white">{title}</h2>
            <p className="mt-1 text-sm text-mist">{subtitle}</p>
          </div>
        </div>
        <button className="inline-flex items-center gap-2 rounded-md border border-white/10 px-3 py-2 text-sm font-semibold text-white hover:border-red-400/50 hover:bg-white/10" onClick={onClose}>
          <X size={16} /> Close
        </button>
      </div>
      {summary.length ? <MetricPills items={summary} /> : null}
      {loading ? <p className="mt-5 rounded-lg border border-white/10 bg-white/[0.04] p-4 text-sm text-mist">Loading songs...</p> : null}
      {!loading && songs.length ? (
        <div className="mt-5 space-y-2">
          {songs.map((song) => <DrilldownSongRow key={`${song.rank}-${song.track_id ?? song.title}`} song={song} />)}
        </div>
      ) : null}
      {!loading && !songs.length ? <p className="mt-5 rounded-lg border border-white/10 bg-white/[0.04] p-4 text-sm text-mist">{emptyMessage}</p> : null}
    </section>
  );
}

function DrilldownSongRow({ song }: { song: TopDrilldownSong }) {
  return (
    <article className="grid gap-4 rounded-lg border border-white/10 bg-white/[0.035] p-3 sm:grid-cols-[4.5rem_1fr]">
      <Artwork src={song.thumbnail} alt={song.title ?? "Song"} className="h-16 w-16" />
      <div className="min-w-0">
        <div className="flex flex-wrap items-center gap-2">
          <span className="rounded-full bg-white/10 px-2.5 py-1 text-xs font-black text-white/70">#{song.rank}</span>
          <h3 className="truncate text-base font-semibold text-white">{song.title ?? "Unknown track"}</h3>
        </div>
        <p className="mt-1 truncate text-sm text-mist">{song.artist ?? "Unknown Artist"}{song.album ? `, ${song.album}` : ""}</p>
        <MetricPills items={[`${song.plays} plays`, song.last_played ? `Last ${formatDate(song.last_played)}` : null, song.first_played ? `First ${formatDate(song.first_played)}` : null]} />
      </div>
    </article>
  );
}

function PanelIntro({ title, caption, loading }: { title: string; caption: string; loading: boolean }) {
  return (
    <div className="flex flex-col gap-2 sm:flex-row sm:items-end sm:justify-between">
      <div>
        <p className="section-label">{title}</p>
        <h2 className="mt-2 text-3xl font-black leading-tight text-white md:text-5xl">{title}</h2>
        <p className="mt-2 max-w-2xl text-base leading-7 text-mist">{caption}</p>
      </div>
      {loading ? <span className="text-sm text-mist">Loading...</span> : null}
    </div>
  );
}

function EmptyRanking({ text }: { text: string }) {
  return <div className="rounded-lg border border-line bg-black/20 p-6 text-sm text-mist">{text}</div>;
}

function MetricPills({ items }: { items: (string | null | undefined)[] }) {
  const visible = items.filter(Boolean);
  if (!visible.length) return null;
  return (
    <div className="mt-3 flex flex-wrap gap-2 text-xs text-mist">
      {visible.map((item) => <span key={item} className="rounded-full bg-white/10 px-3 py-1">{item}</span>)}
    </div>
  );
}

function Movement({ movement }: { movement: PeriodTopItem["movement"] }) {
  if (!movement) return null;
  const Icon = movement.direction === "up" ? ArrowUp : movement.direction === "down" ? ArrowDown : movement.direction === "new" ? Sparkles : Minus;
  return (
    <span className="inline-flex items-center gap-1 rounded-full bg-white/10 px-3 py-1 text-xs text-mist">
      <Icon size={13} /> {movement.label}
    </span>
  );
}

function displayPeriodLabel(label: string | undefined, period: PeriodValue) {
  if (period === "rolling_year") return "Rolling Year";
  return label ?? standardPeriodOptions.find((option) => option.value === period)?.label ?? "Selected Period";
}

function displayListLabel(label: string, artistList: boolean) {
  if (artistList && label === "Comfort favourite") return "Stable favourite";
  return label;
}

function spotifyEvidenceLabel(item: PeriodTopItem, source: MusicSource, artistList: boolean) {
  if (source !== "spotify") return `${item.play_count.toLocaleString()} plays`;
  if (artistList) return item.play_count > 1 ? `${item.play_count.toLocaleString()} signals` : "Spotify top artist";
  return item.spotify_signal_label || (item.play_count > 1 ? `${item.play_count.toLocaleString()} signals` : "Spotify top track");
}
