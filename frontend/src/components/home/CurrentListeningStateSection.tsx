import type { ListeningMinutes, PeriodTopItem, ScoreMetric, TasteDnaComparison, TasteDnaExplorer } from "../../types/api";
import { formatMinutes } from "../../utils/format";

interface Props {
  currentMinutes: ListeningMinutes | null;
  currentTaste: TasteDnaExplorer | null;
  comparison: TasteDnaComparison | null;
  currentTopArtist: PeriodTopItem | null;
  repeatScore: ScoreMetric;
  discoveryScore: ScoreMetric;
}

export function CurrentListeningStateSection({ currentMinutes, currentTaste, comparison, currentTopArtist, repeatScore, discoveryScore }: Props) {
  const dominantCluster = currentTaste?.nodes[0];
  const comfortLeaning = repeatScore.value >= discoveryScore.value;
  const shift = comparison?.claims.growing_cluster ?? comparison?.claims.declining_cluster ?? null;
  const stableCore = comparison?.claims.stable_core_identity?.[0];

  const lead = comfortLeaning
    ? "This month leans more comfort than discovery."
    : "This month is more discovery-led than your long-term baseline.";
  const clusterLine = dominantCluster
    ? `${dominantCluster.name} is the strongest current sound family.`
    : "The current dominant sound family is still forming.";
  const artistLine = currentTopArtist
    ? `${currentTopArtist.artist} is the strongest current artist signal.`
    : "No single current artist signal is strong enough yet.";
  const shiftLine = shift
    ? `${shift.name} is ${shift.delta > 0 ? "stronger" : "lower"} than your rolling-year baseline.`
    : stableCore
      ? `${stableCore} is holding steady as part of the core identity.`
      : "Your recent listening still sits inside your established emotional alternative world.";

  return (
    <section className="overflow-hidden rounded-[1.5rem] border border-white/10 bg-[linear-gradient(135deg,rgba(17,17,29,0.92),rgba(10,10,18,0.96))]">
      <div className="grid gap-0 lg:grid-cols-[0.9fr_1.1fr]">
        <div className="relative min-h-[20rem] border-b border-white/10 p-6 lg:border-b-0 lg:border-r lg:p-8">
          <div className="absolute inset-0 bg-[radial-gradient(circle_at_30%_30%,rgba(217,70,239,0.18),transparent_35%),radial-gradient(circle_at_80%_70%,rgba(99,102,241,0.18),transparent_30%)]" />
          <div className="relative">
            <p className="text-sm font-semibold uppercase tracking-[0.2em] text-violet-200">Your Current Listening State</p>
            <h2 className="mt-3 text-3xl font-black leading-tight text-white md:text-4xl">{lead}</h2>
            <p className="mt-5 text-base leading-8 text-mist">{clusterLine} {artistLine} {shiftLine}</p>
          </div>
          <div className="absolute bottom-6 left-6 right-6">
            <div className="h-2 overflow-hidden rounded-full bg-white/10">
              <div className="h-full rounded-full bg-gradient-to-r from-violet via-magenta to-indigo" style={{ width: `${Math.min(100, Math.max(8, repeatScore.value))}%` }} />
            </div>
            <p className="mt-2 text-xs text-mist">Replay gravity this period, based on your repeat score.</p>
          </div>
        </div>

        <div className="p-6 lg:p-8">
          <div className="grid gap-4 sm:grid-cols-3">
            <StateItem
              label="This month"
              value={currentMinutes ? formatMinutes(currentMinutes.metrics.current_month_total_minutes) : "Unavailable"}
              caption="Detected listening minutes, estimated from track durations."
            />
            <StateItem
              label="Dominant sound"
              value={dominantCluster?.name ?? "Still forming"}
              caption={dominantCluster ? `${dominantCluster.share}% of classified current listening` : "Current month sample is limited."}
            />
            <StateItem
              label="Current anchor"
              value={currentTopArtist?.artist ?? "No clear anchor"}
              caption={currentTopArtist ? `${currentTopArtist.play_count} detected plays this month` : "No artist dominates this period."}
            />
          </div>

          <div className="mt-6 space-y-3">
            {(currentTaste?.nodes ?? []).slice(0, 5).map((node) => (
              <div key={node.id}>
                <div className="flex items-center justify-between gap-3 text-sm">
                  <span className="text-white">{node.name}</span>
                  <span className="text-mist">{node.share}%</span>
                </div>
                <div className="mt-2 h-1.5 overflow-hidden rounded-full bg-white/10">
                  <div className="h-full rounded-full bg-violet" style={{ width: `${Math.min(100, node.share * 3)}%` }} />
                </div>
              </div>
            ))}
          </div>

          {comparison?.summary_sentence ? (
            <p className="mt-6 rounded-xl bg-white/[0.04] p-4 text-sm leading-6 text-mist">{comparison.summary_sentence}</p>
          ) : null}
        </div>
      </div>
    </section>
  );
}

function StateItem({ label, value, caption }: { label: string; value: string; caption: string }) {
  return (
    <div className="rounded-2xl bg-white/[0.045] p-4">
      <p className="text-xs uppercase tracking-[0.16em] text-mist/60">{label}</p>
      <p className="mt-3 text-lg font-black leading-6 text-white">{value}</p>
      <p className="mt-2 text-xs leading-5 text-mist">{caption}</p>
    </div>
  );
}
