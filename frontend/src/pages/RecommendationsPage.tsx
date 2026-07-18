import { ListPlus, WandSparkles } from "lucide-react";
import { EmptyState } from "../components/EmptyState";
import { Artwork } from "../components/ui/Artwork";
import { PageHeader } from "../components/ui/PageHeader";
import type { MusicSource, Recommendation } from "../types/api";

interface Props {
  recommendations: Recommendation[];
  busy: boolean;
  onGenerate: () => void;
  onCreatePlaylist: () => void;
  source: MusicSource;
}

export function RecommendationsPage({ recommendations, busy, onGenerate, onCreatePlaylist, source }: Props) {
  const groups = ["Safe bets", "One step sideways", "Worth the risk"].map((group) => ({
    group,
    items: recommendations.filter((item) => recommendationGroup(item) === group),
  }));
  const spotifyMode = source === "spotify";

  return (
    <div className="space-y-8">
      <section className="editorial-panel p-5 md:p-8">
        <PageHeader
          eyebrow="Recommendations"
          title="Curated Picks"
          description="Twenty evidence-driven picks: safe matches, adjacent discoveries, and a few edges outside the usual profile."
          action={
            <>
              <button className="btn-primary" disabled={busy || spotifyMode} onClick={onGenerate}>
                <WandSparkles size={17} /> {busy ? "Generating..." : "Generate 20"}
              </button>
              <button className="btn-secondary" disabled={busy || recommendations.length === 0 || spotifyMode} onClick={onCreatePlaylist}>
                <ListPlus size={17} /> Create playlist
              </button>
            </>
          }
          meta={
            <>
              <span className="subtle-pill border-red-400/20 bg-red-500/10 text-red-100">{recommendations.length} picks</span>
              {spotifyMode ? <span className="subtle-pill border-amber-200/20 bg-amber-200/10 text-amber-100">Switch to YouTube Music to generate playlists</span> : null}
            </>
          }
        />
      </section>

      {!recommendations.length ? (
        <EmptyState title="No recommendations yet" body={spotifyMode ? "Recommendations currently use YouTube Music history. Switch back to YouTube Music to generate them." : "Generate recommendations after refreshing data. The app excludes heavily played tracks and obvious duplicates before ranking candidates."} />
      ) : (
        <div className="space-y-7">
          {groups.filter((group) => group.items.length).map(({ group, items }) => (
            <RecommendationLane key={group} title={group} items={items} />
          ))}
        </div>
      )}
    </div>
  );
}

function RecommendationLane({ title, items }: { title: string; items: Recommendation[] }) {
  return (
    <section className="editorial-panel p-5 md:p-7">
      <div className="mb-5 flex flex-col gap-2 md:flex-row md:items-end md:justify-between">
        <div>
          <p className="section-label">{title}</p>
          <h2 className="mt-2 text-3xl font-black text-white">{title}</h2>
        </div>
        <p className="max-w-lg text-sm leading-6 text-mist">{laneCaption(title)}</p>
      </div>
      <div className="grid gap-4 lg:grid-cols-2">
        {items.map((item) => <RecommendationCard key={`${item.rank}-${item.track_title}-${item.artist}`} item={item} />)}
      </div>
    </section>
  );
}

function RecommendationCard({ item }: { item: Recommendation }) {
  return (
    <article className="rounded-lg border border-white/10 bg-black/20 p-4 transition hover:border-red-400/40">
      <div className="grid gap-4 sm:grid-cols-[5rem_1fr]">
        <Artwork className="h-20 w-20" src={item.album_art} alt={item.track_title} />
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            <span className="font-display text-2xl leading-none text-red-200">#{item.rank}</span>
            <span className="rounded-full border border-red-400/25 bg-red-500/10 px-2 py-0.5 text-xs text-red-100">{item.recommendation_type}</span>
            <span className="rounded-full border border-white/10 px-2 py-0.5 text-xs text-mist">{item.score}% fit</span>
          </div>
          <h3 className="mt-2 truncate text-lg font-black text-white">{item.track_title}</h3>
          <p className="truncate text-sm text-red-100/80">{item.artist}</p>
          <p className="mt-1 truncate text-sm text-mist">{item.album || "Album unavailable"} {item.release_year ? `, ${item.release_year}` : ""}</p>
        </div>
      </div>
      <p className="mt-4 text-sm leading-6 text-mist">{item.why_this_fits}</p>
      {item.musical_connection ? <p className="mt-3 rounded-md border border-white/10 bg-white/[0.04] p-3 text-xs leading-5 text-red-100/90">{item.musical_connection}</p> : null}
      <p className="mt-3 text-xs text-mist/70">Source reason: {item.source_reason}</p>
    </article>
  );
}

function laneCaption(title: string) {
  if (title === "Safe bets") return "High-fit picks close to your current identity.";
  if (title === "One step sideways") return "Adjacent sounds that should feel fresh without breaking the thread.";
  return "Riskier discoveries that expand the profile without ignoring the evidence.";
}

function recommendationGroup(item: Recommendation) {
  const group = item.recommendation_group || item.recommendation_type;
  if (group === "Safe") return "Safe bets";
  if (group === "Adjacent") return "One step sideways";
  if (group === "Discovery") return "Worth the risk";
  return group;
}
