import { Album, ArrowDown, ArrowUp, Minus, Music2, Sparkles, UserRound, X } from "lucide-react";
import { useEffect, useState } from "react";
import { api } from "../api/client";
import { EmptyState } from "../components/EmptyState";
import type {
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

export function Top10Page() {
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
      api.periodTop(period, "tracks", period === "month" ? selectedMonth : null),
      api.periodTop(period, "artists", period === "month" ? selectedMonth : null),
      api.topAlbums(period, period === "month" ? selectedMonth : null),
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
  }, [period, selectedMonth]);

  useEffect(() => {
    if (!selectedArtist) {
      setArtistSongs(null);
      return;
    }
    let cancelled = false;
    setArtistLoading(true);
    api.artistSongs(selectedArtist, period, period === "month" ? selectedMonth : null)
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
  }, [selectedArtist, period, selectedMonth]);

  useEffect(() => {
    if (!selectedAlbum) {
      setAlbumSongs(null);
      return;
    }
    let cancelled = false;
    setAlbumLoading(true);
    api.albumSongs(selectedAlbum.album, selectedAlbum.artist, period, period === "month" ? selectedMonth : null)
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
  }, [selectedAlbum, period, selectedMonth]);

  const months = tracks?.period.available_months ?? artists?.period.available_months ?? albums?.period.available_months ?? [];
  const activeLabel = displayPeriodLabel(tracks?.period.label ?? albums?.period.label, period);

  if (!tracks && !artists && !albums && !loading) {
    return <EmptyState title="No rankings yet" body="Refresh your music data to build period rankings from detected plays." />;
  }

  return (
    <div className="space-y-8">
      <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
        <div>
          <h1 className="text-3xl font-bold text-white">Top 10</h1>
          <p className="mt-2 max-w-3xl text-mist">
            Songs, artists, and albums shaping this period of your listening.
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2 rounded-lg border border-line bg-panel/80 p-2">
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

      <section className="rounded-lg border border-line bg-panel/82 p-5">
        <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
          <div>
            <p className="text-sm uppercase tracking-[0.16em] text-violet-200">Analysing</p>
            <h2 className="mt-1 text-2xl font-black text-white">{activeLabel}</h2>
            <p className="mt-1 text-sm text-mist">
              {tracks?.period.start_date} to {tracks?.period.end_date}
            </p>
          </div>
          <div className="flex flex-wrap gap-2 text-xs text-mist">
            <span className="rounded-full bg-white/10 px-3 py-1">{tracks?.total_play_count ?? 0} detected plays</span>
          </div>
        </div>
        {tracks?.sample_warning ? <p className="mt-4 rounded-md border border-amber-200/10 bg-amber-200/10 p-3 text-sm text-amber-100">{tracks.sample_warning}</p> : null}
        {albums?.sample_warning ? <p className="mt-4 rounded-md border border-amber-200/10 bg-amber-200/10 p-3 text-sm text-amber-100">{albums.sample_warning}</p> : null}
        {error ? <p className="mt-4 rounded-md border border-red-300/10 bg-red-400/10 p-3 text-sm text-red-100">{error}</p> : null}
      </section>

      <section className="grid gap-7 xl:grid-cols-2">
        <TopList title={`Top Songs - ${displayPeriodLabel(tracks?.period.label, period)}`} response={tracks} loading={loading} />
        <TopList
          title={`Top Artists - ${displayPeriodLabel(artists?.period.label, period)}`}
          response={artists}
          loading={loading}
          artistList
          selectedArtist={selectedArtist}
          onViewSongs={setSelectedArtist}
        />
      </section>

      {selectedArtist ? (
        <ArtistDrilldownPanel artist={selectedArtist} response={artistSongs} loading={artistLoading} onClose={() => setSelectedArtist(null)} />
      ) : null}

      <FavouriteAlbumsSection response={albums} loading={loading} selectedAlbum={selectedAlbum} onViewSongs={setSelectedAlbum} />

      {selectedAlbum ? (
        <AlbumDrilldownPanel album={selectedAlbum} response={albumSongs} loading={albumLoading} onClose={() => setSelectedAlbum(null)} />
      ) : null}
    </div>
  );
}

function PeriodButton({ active, label, onClick }: { active: boolean; label: string; onClick: () => void }) {
  return (
    <button className={`rounded-md px-3 py-2 text-sm font-semibold transition ${active ? "bg-violet text-white" : "text-mist hover:bg-white/10 hover:text-white"}`} onClick={onClick}>
      {label}
    </button>
  );
}

function TopList({
  title,
  response,
  loading,
  artistList = false,
  selectedArtist,
  onViewSongs,
}: {
  title: string;
  response: PeriodTopResponse | null;
  loading: boolean;
  artistList?: boolean;
  selectedArtist?: string | null;
  onViewSongs?: (artist: string) => void;
}) {
  return (
    <div>
      <div className="mb-4 flex items-center justify-between gap-3">
        <h2 className="text-2xl font-bold text-white">{title}</h2>
        {loading ? <span className="text-sm text-mist">Loading...</span> : null}
      </div>
      <div className="space-y-3">
        {response?.items.length ? (
          response.items.map((item) => (
            <PeriodTopCard
              key={item.key}
              item={item}
              artistList={artistList}
              selected={artistList && selectedArtist === item.artist}
              onViewSongs={onViewSongs}
            />
          ))
        ) : (
          <div className="rounded-lg border border-line bg-panel/80 p-5 text-sm text-mist">No detected plays in this period.</div>
        )}
      </div>
    </div>
  );
}

function PeriodTopCard({ item, artistList, selected, onViewSongs }: { item: PeriodTopItem; artistList: boolean; selected?: boolean; onViewSongs?: (artist: string) => void }) {
  const title = artistList ? item.artist : item.title ?? "Unknown track";
  const subtitle = artistList
    ? `${item.unique_songs ?? 0} unique songs${item.most_played_song ? ` - top: ${item.most_played_song}` : ""}`
    : `${item.artist}${item.album ? ` - ${item.album}` : ""}`;

  return (
    <article className={`rounded-lg border bg-panel/80 p-3 transition hover:border-violet/45 ${selected ? "border-violet/60" : "border-line"}`} data-testid={artistList ? "top-artist-card" : "top-song-card"}>
      <div className="grid gap-4 sm:grid-cols-[4.5rem_1fr_auto]">
        <Artwork src={item.thumbnail} label={title} fallback={artistList ? initials(item.artist) : `#${item.rank}`} icon={artistList ? UserRound : Music2} rounded={artistList ? "rounded-full" : "rounded-lg"} />
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            <span className="rounded-full bg-white/10 px-2.5 py-1 text-xs font-black text-white/70">#{item.rank}</span>
            <span className="rounded-full border border-violet/30 bg-violet/10 px-3 py-1 text-xs font-semibold text-violet-100">{displayListLabel(item.interpretation_label, artistList)}</span>
          </div>
          <h3 className="mt-2 truncate text-lg font-semibold text-white">{title}</h3>
          <p className="mt-1 truncate text-sm text-mist">{subtitle}</p>
          <MetricPills
            items={[
              `${item.play_count} plays`,
              item.last_played ? `Last ${formatDate(item.last_played)}` : null,
            ]}
          />
        </div>
        <div className="flex flex-row items-center gap-2 sm:flex-col sm:items-end">
          <Movement movement={item.movement} />
          {artistList && onViewSongs ? (
            <button
              aria-label={`View songs by ${item.artist}`}
              className="w-full whitespace-nowrap rounded-md border border-white/10 px-3 py-2 text-sm font-semibold text-white transition hover:border-violet/50 hover:bg-violet/15 sm:w-auto"
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

function FavouriteAlbumsSection({ response, loading, selectedAlbum, onViewSongs }: { response: TopAlbumsResponse | null; loading: boolean; selectedAlbum: TopAlbumItem | null; onViewSongs: (album: TopAlbumItem) => void }) {
  return (
    <section>
      <div className="mb-4 flex flex-col gap-2 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <h2 className="text-2xl font-bold text-white">Favourite Albums</h2>
          <p className="mt-1 text-sm text-mist">Album-level signals from tracks that have usable album metadata.</p>
        </div>
        {loading ? <span className="text-sm text-mist">Loading...</span> : null}
      </div>
      {response?.albums.length ? (
        <div className="grid gap-3 xl:grid-cols-2">
          {response.albums.map((album) => (
            <AlbumCard key={album.key} album={album} selected={selectedAlbum?.key === album.key} onViewSongs={onViewSongs} />
          ))}
        </div>
      ) : (
        <div className="rounded-lg border border-line bg-panel/80 p-5 text-sm text-mist">Album data is unavailable for this period.</div>
      )}
    </section>
  );
}

function AlbumCard({ album, selected, onViewSongs }: { album: TopAlbumItem; selected: boolean; onViewSongs: (album: TopAlbumItem) => void }) {
  return (
    <article className={`rounded-lg border bg-panel/80 p-3 transition hover:border-violet/45 ${selected ? "border-violet/60" : "border-line"}`} data-testid="top-album-card">
      <div className="grid gap-4 sm:grid-cols-[4.5rem_1fr_auto]">
        <Artwork src={album.thumbnail} label={album.album} fallback={`#${album.rank}`} icon={Album} />
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            <span className="rounded-full bg-white/10 px-2.5 py-1 text-xs font-black text-white/70">#{album.rank}</span>
            <span className="rounded-full border border-violet/30 bg-violet/10 px-3 py-1 text-xs font-semibold text-violet-100">{album.label}</span>
          </div>
          <h3 className="mt-2 truncate text-lg font-semibold text-white">{album.album}</h3>
          <p className="mt-1 truncate text-sm text-mist">{album.artist}</p>
          <MetricPills
            items={[
              `${album.plays} plays`,
              `${album.unique_songs} unique songs`,
            ]}
          />
          <p className="mt-3 text-sm leading-6 text-mist/90">{album.album_signal_note}</p>
          {album.most_played_song ? <p className="mt-2 text-xs text-mist/75">Most played: {album.most_played_song}</p> : null}
        </div>
        <div className="flex items-start justify-end">
          <button
            aria-label={`View songs from ${album.album}`}
            className="whitespace-nowrap rounded-md border border-white/10 px-3 py-2 text-sm font-semibold text-white transition hover:border-violet/50 hover:bg-violet/15"
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
  loading,
  onClose,
  emptyMessage,
  summary,
  songs,
}: {
  title: string;
  subtitle: string;
  loading: boolean;
  onClose: () => void;
  emptyMessage: string;
  summary: (string | null)[];
  songs: TopDrilldownSong[];
}) {
  return (
    <section className="rounded-lg border border-line bg-panel/85 p-5 shadow-glow" data-testid="songs-drilldown">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-violet-200">Drilldown</p>
          <h2 className="mt-2 text-2xl font-black text-white">{title}</h2>
          <p className="mt-1 text-sm text-mist">{subtitle}</p>
        </div>
        <button className="inline-flex items-center gap-2 rounded-md border border-white/10 px-3 py-2 text-sm font-semibold text-white hover:border-violet/50 hover:bg-white/10" onClick={onClose}>
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
    <article className="grid gap-3 rounded-lg border border-white/10 bg-white/[0.035] p-3 sm:grid-cols-[3.5rem_1fr]">
      <Artwork src={song.thumbnail} label={song.title ?? "Song"} fallback={`#${song.rank}`} icon={Music2} />
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
}: {
  src: string | null | undefined;
  label: string;
  fallback?: string;
  icon?: typeof Music2;
  rounded?: string;
}) {
  const [failed, setFailed] = useState(false);
  return (
    <div className={`relative grid h-16 w-16 shrink-0 place-items-center overflow-hidden border border-white/10 bg-[linear-gradient(135deg,rgba(127,29,29,0.9),rgba(5,5,5,0.95))] text-white shadow-[0_12px_35px_rgba(0,0,0,0.28)] ${rounded}`}>
      {src && !failed ? <img className="h-full w-full object-cover" src={src} alt={label} onError={() => setFailed(true)} /> : (
        <div className="grid h-full w-full place-items-center">
          {fallback ? <span className="text-sm font-black text-white/80">{fallback}</span> : <Icon size={22} />}
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

function initials(value: string) {
  const parts = value.split(/\s+/).filter(Boolean);
  return (parts[0]?.[0] ?? "?") + (parts[1]?.[0] ?? "");
}
