import { ListPlus, WandSparkles } from "lucide-react";
import { AnimatedPageTitle } from "../components/AnimatedPageTitle";
import { EmptyState } from "../components/EmptyState";
import type { MusicSource, Recommendation } from "../types/api";

interface Props {
  recommendations: Recommendation[];
  busy: boolean;
  onGenerate: () => void;
  onCreatePlaylist: () => void;
  source: MusicSource;
  titleAnimationKey: string;
}

export function RecommendationsPage({ recommendations, busy, onGenerate, onCreatePlaylist, source, titleAnimationKey }: Props) {
  const groups = RECOMMENDATION_GROUPS.map((group) => ({
    ...group,
    items: recommendations.filter((item) => recommendationGroup(item) === group.group),
  }));
  const spotifyMode = source === "spotify";
  return (
    <div className="space-y-6">
      <header className="overflow-hidden rounded-[1.25rem] border border-red-500/15 bg-[linear-gradient(135deg,rgba(33,8,8,0.96),rgba(5,5,5,0.99)_62%,rgba(16,8,8,0.98))] p-5 shadow-glow lg:p-6">
        <div className="flex flex-col justify-between gap-5 lg:flex-row lg:items-end">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.2em] text-red-200">Recommendation lab</p>
            <AnimatedPageTitle animationKey={titleAnimationKey} text="Evidence-driven next listens" className="mt-3 text-3xl font-black text-white md:text-4xl" />
            <p className="mt-3 max-w-3xl text-sm leading-6 text-mist">
              Twenty picks split into safe matches, nearby discoveries, and riskier edges outside the usual profile.
            </p>
            <div className="mt-4 flex flex-wrap gap-2">
              <RecommendationBadge label={spotifyMode ? "Spotify view" : "YouTube Music view"} muted={spotifyMode} />
              <RecommendationBadge label={`${recommendations.length} saved picks`} />
              <RecommendationBadge label={spotifyMode ? "Generation paused" : "Playlist tools ready"} muted={spotifyMode} />
            </div>
          </div>
          <div className="flex flex-wrap gap-2">
            <button className="btn-primary" disabled={busy || spotifyMode} onClick={onGenerate}>
              <WandSparkles size={17} /> {busy ? "Generating..." : "Generate 20 Recommendations"}
            </button>
            <button className="btn-secondary" disabled={busy || recommendations.length === 0 || spotifyMode} onClick={onCreatePlaylist}>
              <ListPlus size={17} /> Create "Saville Recommendations" Playlist
            </button>
          </div>
        </div>
      </header>
      <div className="grid gap-3 md:grid-cols-3">
        {groups.map(({ group, items }) => (
          <div key={group} className="rounded-xl border border-line bg-panel/70 p-4">
            <p className="text-xs font-semibold uppercase tracking-[0.16em] text-red-200">{group}</p>
            <p className="mt-2 text-2xl font-black text-white">{items.length}</p>
            <p className="mt-1 text-sm text-mist/80">picks in this lane</p>
          </div>
        ))}
      </div>
      {spotifyMode ? (
        <p className="rounded-xl border border-amber-200/15 bg-amber-200/10 p-4 text-sm leading-6 text-amber-100">
          Recommendations and playlist creation currently use YouTube Music history. Switch back to YouTube Music to generate them.
        </p>
      ) : null}
      {!recommendations.length ? (
        <EmptyState title="No recommendations yet" body={spotifyMode ? "Recommendations currently use YouTube Music history. Switch back to YouTube Music to generate them." : "Generate recommendations after refreshing data. The app excludes heavily played tracks and obvious duplicates before ranking candidates."} />
      ) : (
        <div className="space-y-6">
          {groups.filter((group) => group.items.length).map(({ group, description, items }) => (
            <section key={group} className="min-w-0 rounded-[1.25rem] border border-line bg-panel/72 p-4 lg:p-5">
              <div className="flex flex-col gap-2 sm:flex-row sm:items-end sm:justify-between">
                <div>
                  <p className="text-xs font-semibold uppercase tracking-[0.18em] text-red-200">{group}</p>
                  <h2 className="mt-2 text-2xl font-black text-white">{description}</h2>
                </div>
                <span className="rounded-full border border-white/10 bg-black/25 px-3 py-1.5 text-xs font-semibold text-mist">{items.length} picks</span>
              </div>
              <div className="mt-4 grid min-w-0 gap-4 lg:grid-cols-2">
                {items.map((item) => (
                  <RecommendationCard key={`${item.rank}-${item.track_title}-${item.artist}`} item={item} />
                ))}
              </div>
            </section>
          ))}
        </div>
      )}
    </div>
  );
}

function RecommendationCard({ item }: { item: Recommendation }) {
  return (
    <article className="min-w-0 rounded-xl border border-white/10 bg-black/20 p-4 transition hover:border-red-500/30 hover:bg-white/[0.045]">
      <div className="flex gap-4">
        <div className="grid h-20 w-20 shrink-0 place-items-center overflow-hidden rounded-lg border border-white/10 bg-red-950/45 text-lg font-black text-white/70">
          {item.album_art ? <img className="h-full w-full object-cover" src={item.album_art} alt="" /> : `#${item.rank}`}
        </div>
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            <span className="text-lg font-black text-white/25">#{item.rank}</span>
            <span className="rounded-full border border-red-400/25 bg-red-500/10 px-2 py-0.5 text-xs font-semibold text-red-100">{item.recommendation_type}</span>
            <span className="rounded-full border border-white/10 bg-white/[0.04] px-2 py-0.5 text-xs text-mist">{item.score}% fit</span>
          </div>
          <h3 className="mt-2 line-clamp-2 break-words text-lg font-black leading-6 text-white">{item.track_title}</h3>
          <p className="mt-1 truncate text-sm font-semibold text-red-100">{item.artist}</p>
          <p className="mt-1 truncate text-sm text-mist">{item.album || "Album unavailable"} {item.release_year ? `- ${item.release_year}` : ""}</p>
        </div>
      </div>
      <p className="mt-4 break-words text-sm leading-6 text-mist">{item.why_this_fits}</p>
      {item.musical_connection ? <p className="mt-3 break-words rounded-lg border border-red-500/15 bg-red-950/18 p-3 text-xs leading-5 text-red-100">{item.musical_connection}</p> : null}
      <p className="mt-3 break-words text-xs text-mist/70">Source reason: {item.source_reason}</p>
    </article>
  );
}

function RecommendationBadge({ label, muted = false }: { label: string; muted?: boolean }) {
  return (
    <span className={`rounded-full border px-3 py-1.5 text-xs font-semibold ${muted ? "border-white/10 bg-white/[0.04] text-mist/70" : "border-red-400/25 bg-red-500/10 text-red-100"}`}>
      {label}
    </span>
  );
}

function recommendationGroup(item: Recommendation) {
  const group = item.recommendation_group || item.recommendation_type;
  if (group === "Safe") return "Safe bets";
  if (group === "Adjacent") return "One step sideways";
  if (group === "Discovery") return "Worth the risk";
  return group;
}

const RECOMMENDATION_GROUPS = [
  { group: "Safe bets", description: "Closest to the core profile" },
  { group: "One step sideways", description: "Adjacent sounds with familiar DNA" },
  { group: "Worth the risk", description: "Sharper edges and discovery swings" },
];
