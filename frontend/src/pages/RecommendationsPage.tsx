import { ListPlus, WandSparkles } from "lucide-react";
import { Artwork } from "../components/Artwork";
import { EmptyState } from "../components/EmptyState";
import { GlowPanel } from "../components/GlowPanel";
import { PageTitlePanel } from "../components/PageTitlePanel";
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
      <PageTitlePanel
        eyebrow="Recommendation lab"
        title="Evidence-driven next listens"
        titleAnimationKey={titleAnimationKey}
        titleClassName="text-3xl font-black text-white md:text-4xl"
        subtitle="Twenty picks split into safe matches, nearby discoveries, and riskier edges outside the usual profile."
        actions={
          <div className="flex flex-wrap gap-2">
            <button className="btn-primary" disabled={busy || spotifyMode} onClick={onGenerate}>
              <WandSparkles size={17} /> {busy ? "Generating..." : "Generate 20 Recommendations"}
            </button>
            <button className="btn-secondary" disabled={busy || recommendations.length === 0 || spotifyMode} onClick={onCreatePlaylist}>
              <ListPlus size={17} /> Create "Saville Recommendations" Playlist
            </button>
          </div>
        }
        metadata={
          <>
              <RecommendationBadge label={spotifyMode ? "Spotify view" : "YouTube Music view"} muted={spotifyMode} />
              <RecommendationBadge label={`${recommendations.length} saved picks`} />
              <RecommendationBadge label={spotifyMode ? "Generation paused" : "Playlist tools ready"} muted={spotifyMode} />
          </>
        }
      />
      <div className="grid gap-3 md:grid-cols-3">
        {groups.map(({ group, items }) => (
          <GlowPanel key={group} as="div" variant="card" className="p-4">
            <p className="text-xs font-semibold uppercase tracking-[0.16em] text-red-200">{group}</p>
            <p className="mt-2 text-2xl font-black text-white">{items.length}</p>
            <p className="mt-1 text-sm text-mist/80">picks in this lane</p>
          </GlowPanel>
        ))}
      </div>
      {spotifyMode ? (
        <GlowPanel as="p" variant="row" className="bg-amber-200/10 p-4 text-sm leading-6 text-amber-100">
          Recommendations and playlist creation currently use YouTube Music history. Switch back to YouTube Music to generate them.
        </GlowPanel>
      ) : null}
      {!recommendations.length ? (
        <EmptyState title="No recommendations yet" body={spotifyMode ? "Recommendations currently use YouTube Music history. Switch back to YouTube Music to generate them." : "Generate recommendations after refreshing data. The app excludes heavily played tracks and obvious duplicates before ranking candidates."} />
      ) : (
        <div className="space-y-6">
          {groups.filter((group) => group.items.length).map(({ group, description, items }) => (
            <GlowPanel key={group} as="section" variant="major" className="min-w-0 p-4 lg:p-5">
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
            </GlowPanel>
          ))}
        </div>
      )}
    </div>
  );
}

function RecommendationCard({ item }: { item: Recommendation }) {
  return (
    <GlowPanel as="article" variant="card" className="min-w-0 p-4 transition">
      <div className="flex gap-4">
        <Artwork src={item.album_art} alt={item.track_title} kind="song" size="md" fallbackLabel={`#${item.rank}`} />
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
      {item.musical_connection ? <GlowPanel as="p" variant="row" wrapperClassName="mt-3" className="break-words bg-red-950/[0.18] p-3 text-xs leading-5 text-red-100">{item.musical_connection}</GlowPanel> : null}
      <p className="mt-3 break-words text-xs text-mist/70">Source reason: {item.source_reason}</p>
    </GlowPanel>
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
