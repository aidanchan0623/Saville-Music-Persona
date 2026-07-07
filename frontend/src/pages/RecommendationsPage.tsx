import { ListPlus, WandSparkles } from "lucide-react";
import { EmptyState } from "../components/EmptyState";
import type { Recommendation } from "../types/api";

interface Props {
  recommendations: Recommendation[];
  busy: boolean;
  onGenerate: () => void;
  onCreatePlaylist: () => void;
}

export function RecommendationsPage({ recommendations, busy, onGenerate, onCreatePlaylist }: Props) {
  const groups = ["Safe bets", "One step sideways", "Worth the risk"].map((group) => ({
    group,
    items: recommendations.filter((item) => recommendationGroup(item) === group),
  }));
  return (
    <div className="space-y-6">
      <div className="flex flex-col justify-between gap-4 lg:flex-row lg:items-end">
        <div>
          <h1 className="text-3xl font-bold text-white">Recommendations</h1>
          <p className="mt-2 max-w-3xl text-mist">Twenty evidence-driven picks: safe matches, adjacent discoveries, and a few edges outside the usual profile.</p>
        </div>
        <div className="flex flex-wrap gap-2">
          <button className="btn-primary" disabled={busy} onClick={onGenerate}>
            <WandSparkles size={17} /> {busy ? "Generating..." : "Generate 20 Recommendations"}
          </button>
          <button className="btn-secondary" disabled={busy || recommendations.length === 0} onClick={onCreatePlaylist}>
            <ListPlus size={17} /> Create "Saville Recommendations" Playlist
          </button>
        </div>
      </div>
      {!recommendations.length ? (
        <EmptyState title="No recommendations yet" body="Generate recommendations after refreshing data. The app excludes heavily played tracks and obvious duplicates before ranking candidates." />
      ) : (
        <div className="space-y-6">
          {groups.filter((group) => group.items.length).map(({ group, items }) => (
            <section key={group}>
              <h2 className="text-xl font-semibold text-white">{group}</h2>
              <div className="mt-3 grid gap-4 lg:grid-cols-2">
                {items.map((item) => (
            <article key={`${item.rank}-${item.track_title}-${item.artist}`} className="rounded-lg border border-line bg-panel/82 p-4 transition hover:border-magenta/40">
              <div className="flex gap-4">
                <div className="h-20 w-20 shrink-0 overflow-hidden rounded-md bg-white/10">
                  {item.album_art ? <img className="h-full w-full object-cover" src={item.album_art} alt="" /> : null}
                </div>
                <div className="min-w-0">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="text-lg font-black text-white/25">#{item.rank}</span>
                    <span className="rounded-full border border-violet/25 bg-violet/10 px-2 py-0.5 text-xs text-violet-100">{item.recommendation_type}</span>
                    <span className="rounded-full border border-white/10 px-2 py-0.5 text-xs text-mist">{item.score}% fit</span>
                  </div>
                  <h3 className="mt-2 truncate text-lg font-semibold text-white">{item.track_title}</h3>
                  <p className="truncate text-sm text-violet-100">{item.artist}</p>
                  <p className="mt-1 truncate text-sm text-mist">{item.album || "Album unavailable"} {item.release_year ? `- ${item.release_year}` : ""}</p>
                </div>
              </div>
              <p className="mt-4 text-sm leading-6 text-mist">{item.why_this_fits}</p>
              {item.musical_connection ? <p className="mt-2 text-xs text-violet-100">{item.musical_connection}</p> : null}
              <p className="mt-3 text-xs text-mist/70">Source reason: {item.source_reason}</p>
            </article>
                ))}
              </div>
            </section>
          ))}
        </div>
      )}
    </div>
  );
}

function recommendationGroup(item: Recommendation) {
  const group = item.recommendation_group || item.recommendation_type;
  if (group === "Safe") return "Safe bets";
  if (group === "Adjacent") return "One step sideways";
  if (group === "Discovery") return "Worth the risk";
  return group;
}
