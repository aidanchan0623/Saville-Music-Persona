import { Album, ArrowDown, ArrowUp, Minus, Music2, Sparkles, UserRound, X } from "lucide-react";
import type { ReactNode } from "react";
import { useEffect, useState } from "react";
import { api } from "../api/client";
import { EmptyState } from "../components/EmptyState";
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

type TopPeriod = "this_month" | "month" | "rolling_year";

export function Top10Page({ source }: { source: MusicSource }) {
  const [period, setPeriod] = useState<TopPeriod>("this_month");
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

  if (!tracks && !artists && !albums && !loading) {
    return <EmptyState title="No rankings yet" body="Refresh your music data to build period rankings from detected plays." />;
  }

  return (
    <div className="space-y-10">
      <header className="overflow-hidden rounded-[2rem] border border-red-500/15 bg-[linear-gradient(135deg,rgba(37,9,9,0.96),rgba(5,5,5,0.99)_58%,rgba(17,8,8,0.98))] p-6 shadow-glow lg:p-8">
        <div className="flex flex-col gap-6 lg:flex-row lg:items-end lg:justify-between">
          <div className="max-w-4xl">
            <p className="text-sm font-semibold uppercase tracking-[0.24em] text-red-200">Music leaders</p>
            <h1 className="mt-3 text-5xl font-black leading-none text-white md:text-7xl">Top 10</h1>
            <p className="mt-4 max-w-3xl text-lg leading-8 text-mist">
              {source === "spotify" ? "Spotify-backed leaders from top items, saved music, playlists, and recent sync signals." : "The songs, artists, and albums currently defining this slice of your listening."}
            </p>
          </div>
          <div className="flex flex-wrap items-center gap-2 rounded-xl border border-white/10 bg-black/25 p-2">
          <PeriodButton active={period === "this_month"} label="This Month" onClick={() => setPeriod("this_month")} />
          <PeriodButton active={period === "month"} label="Select Month" onClick={() => setPeriod("month")} />
          <PeriodButton active={period === "rolling_year"} label="Rolling Year" onClick={() => setPeriod("rolling_year")} />
          {period === "month" ? (
            <select
              className="rounded-md border border-white/10 bg-ink px-3 py-2 text-sm text-white"
              value={selectedMonth ?? months.at(-1)?.value ?? ""}
              onChange={(event) => setSelectedMonth(event.target.value)}
            >
              {months.map((month) => (
                <option key={month.value} value={month.value}>{month.label}</option>
              ))}
            </select>
          ) : null}
          </div>
        </div>

        <div className="mt-7 flex flex-wrap gap-3 text-sm">
          <span className="rounded-full border border-white/10 bg-white/[0.07] px-4 py-2 font-semibold text-white">{activeLabel}</span>
          <span className="rounded-full border border-white/10 bg-white/[0.04] px-4 py-2 text-mist">{tracks?.period.start_date} to {tracks?.period.end_date}</span>
          <span className="rounded-full border border-white/10 bg-white/[0.04] px-4 py-2 text-mist">{(tracks?.total_play_count ?? 0).toLocaleString()} detected plays</span>
          {source === "spotify" ? <span className="rounded-full border border-white/10 bg-white/[0.04] px-4 py-2 text-mist">Top-item based, not exact Spotify history</span> : null}
          {loading ? <span className="rounded-full border border-red-400/20 bg-red-500/10 px-4 py-2 text-red-100">Updating...</span> : null}
        </div>
      </header>

      {(tracks?.sample_warning || albums?.sample_warning || error) ? (
        <section className="space-y-3">
          {tracks?.sample_warning ? <p className="rounded-xl border border-amber-200/10 bg-amber-200/10 p-4 text-sm text-amber-100">{tracks.sample_warning}</p> : null}
          {albums?.sample_warning ? <p className="rounded-xl border border-amber-200/10 bg-amber-200/10 p-4 text-sm text-amber-100">{albums.sample_warning}</p> : null}
          {error ? <p className="rounded-xl border border-red-300/10 bg-red-400/10 p-4 text-sm text-red-100">{error}</p> : null}
        </section>
      ) : null}

      <TopList
        title={`Top Songs - ${displayPeriodLabel(tracks?.period.label, period)}`}
        caption={source === "spotify" ? "Your clearest Spotify top-track signals. Exact lifetime play counts are not available from Spotify." : "Your clearest song leaders, ranked by local play history."}
        response={tracks}
        loading={loading}
        source={source}
      />

      <TopList
        title={`Top Artists - ${displayPeriodLabel(artists?.period.label, period)}`}
        caption={source === "spotify" ? "Official Spotify artist images and genres where available." : "The artists pulling the most attention in this period."}
        response={artists}
        loading={loading}
        artistList
        source={source}
        selectedArtist={selectedArtist}
        onViewSongs={setSelectedArtist}
      />

      {selectedArtist ? (
        <ArtistDrilldownPanel artist={selectedArtist} response={artistSongs} loading={artistLoading} onClose={() => setSelectedArtist(null)} />
      ) : null}

      <FavouriteAlbumsSection response={albums} loading={loading} selectedAlbum={selectedAlbum} onViewSongs={setSelectedAlbum} source={source} />

      {selectedAlbum ? (
        <AlbumDrilldownPanel album={selectedAlbum} response={albumSongs} loading={albumLoading} onClose={() => setSelectedAlbum(null)} />
      ) : null}
    </div>
  );
}

function PeriodButton({ active, label, onClick }: { active: boolean; label: string; onClick: () => void }) {
  return (
    <button className={`rounded-lg px-3 py-2 text-sm font-semibold transition ${active ? "bg-red-600 text-white" : "text-mist hover:bg-white/10 hover:text-white"}`} onClick={onClick}>
      {label}
    </button>
  );
}

function TopList({
  title,
  caption,
  response,
  loading,
  artistList = false,
  selectedArtist,
  onViewSongs,
  source,
}: {
  title: string;
  caption: string;
  response: PeriodTopResponse | null;
  loading: boolean;
  artistList?: boolean;
  selectedArtist?: string | null;
  onViewSongs?: (artist: string) => void;
  source: MusicSource;
}) {
  return (
    <section className="rounded-[1.75rem] border border-line bg-panel/82 p-5 shadow-[0_20px_70px_rgba(0,0,0,0.22)] lg:p-7">
      <div className="mb-6 flex flex-col gap-2 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <h2 className="text-3xl font-black leading-tight text-white md:text-5xl">{title}</h2>
          <p className="mt-2 max-w-2xl text-base leading-7 text-mist">{caption}</p>
        </div>
        {loading ? <span className="text-sm text-mist">Loading...</span> : null}
      </div>
      <div className={artistList ? "grid gap-4 xl:grid-cols-2" : "space-y-4"}>
        {response?.items.length ? (
          response.items.map((item) => (
            <PeriodTopCard
              key={item.key}
              item={item}
              artistList={artistList}
              selected={artistList && selectedArtist === item.artist}
              onViewSongs={onViewSongs}
              source={source}
            />
          ))
        ) : (
          <div className="rounded-2xl border border-line bg-black/20 p-6 text-sm text-mist">No detected plays in this period.</div>
        )}
      </div>
    </section>
  );
}

function PeriodTopCard({ item, artistList, selected, onViewSongs, source }: { item: PeriodTopItem; artistList: boolean; selected?: boolean; onViewSongs?: (artist: string) => void; source: MusicSource }) {
  const title = artistList ? item.artist : item.title ?? "Unknown track";
  const rank = `#${String(item.rank).padStart(2, "0")}`;

  if (artistList) {
    return (
      <article className={`rounded-2xl border bg-black/20 p-5 transition hover:border-red-400/45 ${selected ? "border-red-400/70" : "border-white/10"}`} data-testid="top-artist-card">
        <div className="grid gap-5 sm:grid-cols-[7rem_1fr]">
          <Artwork src={item.thumbnail} label={title} fallback={initials(item.artist)} icon={UserRound} rounded="rounded-full" sizeClass="h-28 w-28" />
          <div className="min-w-0">
            <div className="flex flex-wrap items-center gap-3">
              <span className="text-2xl font-black text-red-200">{rank}</span>
              <span className="rounded-full border border-red-400/25 bg-red-500/10 px-3 py-1 text-xs font-semibold text-red-100">{displayListLabel(item.interpretation_label, true)}</span>
            </div>
            <h3 className="mt-3 truncate text-2xl font-black leading-tight text-white md:text-3xl">{title}</h3>
            <p className="mt-2 text-sm leading-6 text-mist">
              {item.unique_songs ?? 0} unique songs{item.most_played_song ? ` - top song: ${item.most_played_song}` : ""}
            </p>
            <div className="mt-5 flex flex-wrap items-center gap-3">
              <span className="text-2xl font-black text-white">{spotifyEvidenceLabel(item, source, true)}</span>
              {detectedMinutesLabel(item) ? <span className="rounded-full bg-white/10 px-3 py-1 text-xs text-mist">{detectedMinutesLabel(item)}</span> : null}
              <span className="rounded-full bg-white/10 px-3 py-1 text-xs text-mist">{item.share_of_period}% share</span>
              <Movement movement={item.movement} />
            </div>
            {onViewSongs ? (
              <button
                aria-label={`View songs by ${item.artist}`}
                className="mt-5 rounded-lg border border-white/10 px-4 py-2.5 text-sm font-semibold text-white transition hover:border-red-400/50 hover:bg-red-500/15"
                type="button"
                onClick={() => onViewSongs(item.artist)}
              >
                View songs
              </button>
            ) : null}
          </div>
        </div>
      </article>
    );
  }

  return (
    <article className="rounded-2xl border border-white/10 bg-black/20 p-4 transition hover:border-red-400/45" data-testid="top-song-card">
      <div className="grid gap-5 sm:grid-cols-[7rem_1fr] lg:grid-cols-[8rem_1fr_auto] lg:items-center">
        <Artwork src={item.thumbnail} label={title} fallback={rank} icon={Music2} rounded="rounded-2xl" sizeClass="h-28 w-28 md:h-32 md:w-32" />
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-3">
            <span className="text-3xl font-black text-red-200">{rank}</span>
            <span className="rounded-full border border-red-400/25 bg-red-500/10 px-3 py-1 text-xs font-semibold text-red-100">{displayListLabel(item.interpretation_label, false)}</span>
          </div>
          <h3 className="mt-3 truncate text-2xl font-black leading-tight text-white md:text-3xl">{title}</h3>
          <p className="mt-2 truncate text-base font-semibold text-mist">{item.artist}</p>
          {item.album ? <p className="mt-1 truncate text-sm text-mist/75">{item.album}</p> : null}
        </div>
        <div className="flex flex-wrap items-center gap-3 lg:flex-col lg:items-end">
          <span className="text-2xl font-black text-white">{spotifyEvidenceLabel(item, source, false)}</span>
          {detectedMinutesLabel(item) ? <span className="rounded-full bg-white/10 px-3 py-1 text-xs text-mist">{detectedMinutesLabel(item)}</span> : null}
          <Movement movement={item.movement} />
        </div>
      </div>
    </article>
  );
}

function FavouriteAlbumsSection({ response, loading, selectedAlbum, onViewSongs, source }: { response: TopAlbumsResponse | null; loading: boolean; selectedAlbum: TopAlbumItem | null; onViewSongs: (album: TopAlbumItem) => void; source: MusicSource }) {
  return (
    <section className="rounded-[1.75rem] border border-line bg-panel/82 p-5 shadow-[0_20px_70px_rgba(0,0,0,0.22)] lg:p-7">
      <div className="mb-6 flex flex-col gap-2 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <h2 className="text-3xl font-black leading-tight text-white md:text-5xl">Favourite Albums</h2>
          <p className="mt-2 max-w-2xl text-base leading-7 text-mist">{source === "spotify" ? "Projects with the strongest album-level signal from Spotify top tracks, saved music, playlists, and recent sync data." : "Projects with the strongest pull across your local plays."}</p>
        </div>
        {loading ? <span className="text-sm text-mist">Loading...</span> : null}
      </div>
      {response?.albums.length ? (
        <div className="grid gap-4 xl:grid-cols-2">
          {response.albums.map((album) => (
            <AlbumCard key={album.key} album={album} selected={selectedAlbum?.key === album.key} onViewSongs={onViewSongs} source={source} />
          ))}
        </div>
      ) : (
        <div className="rounded-2xl border border-line bg-black/20 p-6 text-sm text-mist">Album data is unavailable for this period.</div>
      )}
    </section>
  );
}

function AlbumCard({ album, selected, onViewSongs, source }: { album: TopAlbumItem; selected: boolean; onViewSongs: (album: TopAlbumItem) => void; source: MusicSource }) {
  const rank = `#${String(album.rank).padStart(2, "0")}`;
  return (
    <article className={`rounded-2xl border bg-black/20 p-5 transition hover:border-red-400/45 ${selected ? "border-red-400/70" : "border-white/10"}`} data-testid="top-album-card">
      <div className="grid gap-5 sm:grid-cols-[7rem_1fr] lg:grid-cols-[8rem_1fr_auto]">
        <Artwork src={album.thumbnail} label={album.album} fallback={rank} icon={Album} rounded="rounded-2xl" sizeClass="h-28 w-28 md:h-32 md:w-32" />
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-3">
            <span className="text-2xl font-black text-red-200">{rank}</span>
            <span className="rounded-full border border-red-400/25 bg-red-500/10 px-3 py-1 text-xs font-semibold text-red-100">{album.label}</span>
          </div>
          <h3 className="mt-3 truncate text-2xl font-black leading-tight text-white md:text-3xl">{album.album}</h3>
          <p className="mt-2 truncate text-base font-semibold text-mist">{album.artist}</p>
          <div className="mt-5 flex flex-wrap items-center gap-3">
            <span className="text-2xl font-black text-white">{source === "spotify" ? `${album.plays.toLocaleString()} signals` : `${album.plays.toLocaleString()} plays`}</span>
            <span className="rounded-full bg-white/10 px-3 py-1 text-xs text-mist">{album.unique_songs} songs</span>
          </div>
          <p className="mt-3 text-sm leading-6 text-mist/90">{album.album_signal_note}</p>
          {album.most_played_song ? <p className="mt-2 text-xs text-mist/75">Most played: {album.most_played_song}</p> : null}
        </div>
        <div className="flex items-start justify-end">
          <button
            aria-label={`View songs from ${album.album}`}
            className="whitespace-nowrap rounded-lg border border-white/10 px-4 py-2.5 text-sm font-semibold text-white transition hover:border-red-400/50 hover:bg-red-500/15"
            type="button"
            onClick={() => onViewSongs(album)}
          >
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
      title={`Songs by ${artist} - ${response?.period_label ?? "Selected Period"}`}
      subtitle="Song-level data for this artist in the selected period."
      visual={<Artwork src={response?.artist_thumbnail} label={artist} fallback={initials(artist)} icon={UserRound} rounded="rounded-full" sizeClass="h-24 w-24" />}
      loading={loading}
      onClose={onClose}
      emptyMessage="Song-level data for this artist is not available in the selected period."
      summary={response ? [
        `${response.total_plays} total plays`,
        `${response.unique_songs} unique songs`,
        response.most_replayed_song ? `Most replayed: ${response.most_replayed_song}` : null,
      ] : []}
      songs={response?.songs ?? []}
    />
  );
}

function AlbumDrilldownPanel({ album, response, loading, onClose }: { album: TopAlbumItem; response: TopAlbumSongsResponse | null; loading: boolean; onClose: () => void }) {
  return (
    <DrilldownShell
      title={`Songs from ${album.album} - ${response?.period_label ?? "Selected Period"}`}
      subtitle={album.artist}
      visual={<Artwork src={album.thumbnail} label={album.album} fallback={initials(album.album)} icon={Album} rounded="rounded-2xl" sizeClass="h-24 w-24" />}
      loading={loading}
      onClose={onClose}
      emptyMessage="Album data is unavailable for this period."
      summary={response ? [
        `${response.total_plays} total plays`,
        `${response.unique_songs} unique songs`,
        response.most_played_song ? `Most played: ${response.most_played_song}` : null,
      ] : []}
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
    <section className="rounded-[1.5rem] border border-line bg-panel/85 p-5 shadow-glow lg:p-6" data-testid="songs-drilldown">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div className="flex flex-col gap-4 sm:flex-row sm:items-center">
          {visual}
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-red-200">Drilldown</p>
            <h2 className="mt-2 text-3xl font-black text-white">{title}</h2>
            <p className="mt-1 text-sm text-mist">{subtitle}</p>
          </div>
        </div>
        <button className="inline-flex items-center gap-2 rounded-lg border border-white/10 px-3 py-2 text-sm font-semibold text-white hover:border-red-400/50 hover:bg-white/10" onClick={onClose}>
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
    <article className="grid gap-4 rounded-xl border border-white/10 bg-white/[0.035] p-3 sm:grid-cols-[4.5rem_1fr]">
      <Artwork src={song.thumbnail} label={song.title ?? "Song"} fallback={`#${song.rank}`} icon={Music2} rounded="rounded-xl" sizeClass="h-16 w-16" />
      <div className="min-w-0">
        <div className="flex flex-wrap items-center gap-2">
          <span className="rounded-full bg-white/10 px-2.5 py-1 text-xs font-black text-white/70">#{song.rank}</span>
          <h3 className="truncate text-base font-semibold text-white">{song.title ?? "Unknown track"}</h3>
        </div>
        <p className="mt-1 truncate text-sm text-mist">{song.artist ?? "Unknown Artist"}{song.album ? ` - ${song.album}` : ""}</p>
        <MetricPills
          items={[
            `${song.plays} plays`,
            song.last_played ? `Last ${formatDate(song.last_played)}` : null,
            song.first_played ? `First ${formatDate(song.first_played)}` : null,
          ]}
        />
      </div>
    </article>
  );
}

function Artwork({
  src,
  label,
  fallback,
  icon: Icon = Music2,
  rounded = "rounded-lg",
  sizeClass = "h-16 w-16",
}: {
  src: string | null | undefined;
  label: string;
  fallback?: string;
  icon?: typeof Music2;
  rounded?: string;
  sizeClass?: string;
}) {
  const [failed, setFailed] = useState(false);
  useEffect(() => setFailed(false), [src]);
  return (
    <div className={`relative grid shrink-0 place-items-center overflow-hidden border border-white/10 bg-[linear-gradient(135deg,rgba(127,29,29,0.9),rgba(5,5,5,0.95))] text-white shadow-[0_18px_50px_rgba(0,0,0,0.32)] ${sizeClass} ${rounded}`}>
      {src && !failed ? <img className="h-full w-full object-cover object-center" src={src} alt={label} onError={() => setFailed(true)} /> : (
        <div className="grid h-full w-full place-items-center">
          {fallback ? <span className="text-base font-black text-white/85">{fallback}</span> : <Icon size={24} />}
        </div>
      )}
    </div>
  );
}

function MetricPills({ items }: { items: (string | null | undefined)[] }) {
  const visible = items.filter(Boolean);
  if (!visible.length) return null;
  return (
    <div className="mt-3 flex flex-wrap gap-2 text-xs text-mist">
      {visible.map((item) => (
        <span key={item} className="rounded-full bg-white/10 px-3 py-1">{item}</span>
      ))}
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

function displayPeriodLabel(label: string | undefined, period: TopPeriod) {
  if (period === "rolling_year") return "Rolling Year";
  return label ?? "Selected Period";
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

function detectedMinutesLabel(item: PeriodTopItem) {
  if (!item.detected_minutes || item.detected_minutes <= 0) return null;
  return item.detected_minutes_formatted || `${Math.round(item.detected_minutes)} min detected`;
}

function initials(value: string) {
  const parts = value.split(/\s+/).filter(Boolean);
  return (parts[0]?.[0] ?? "?") + (parts[1]?.[0] ?? "");
}
