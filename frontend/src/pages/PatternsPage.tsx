import { ChartPanel } from "../components/ChartPanel";
import { EmptyState } from "../components/EmptyState";
import type { Charts } from "../types/api";

export function PatternsPage({ charts }: { charts: Charts | null }) {
  if (!charts) return <EmptyState title="No listening patterns yet" body="Refresh data to build charts from local cached analysis." />;
  return (
    <div className="space-y-5">
      <div>
        <h1 className="text-3xl font-bold text-white">Listening Patterns</h1>
        <p className="mt-2 text-mist">Charts stay tied to real available fields; the timeline appears only when play dates are parseable.</p>
      </div>
      <div className="grid gap-5 xl:grid-cols-2">
        <ChartPanel title="Listening by release decade" data={charts.release_decades} />
        <ChartPanel title="Top genre clusters" data={charts.top_genre_clusters} type="pie" />
        <ChartPanel title="Top artists by detected plays" data={charts.top_artists} />
        <ChartPanel title="Most repeated songs" data={charts.most_repeated_songs} />
        <ChartPanel title="Artist concentration" data={charts.artist_concentration} type="pie" />
        <ChartPanel title="Playlist influence" data={charts.playlist_influence} />
        <div className="xl:col-span-2">
          <ChartPanel title="Data coverage timeline" data={charts.coverage_timeline} type="line" />
        </div>
      </div>
    </div>
  );
}

