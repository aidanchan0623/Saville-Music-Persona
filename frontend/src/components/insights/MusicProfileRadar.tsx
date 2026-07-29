import { useMemo } from "react";
import { PolarAngleAxis, PolarGrid, Radar, RadarChart, ResponsiveContainer, Tooltip } from "recharts";
import type { InsightsProfileAxis } from "../../types/api";
import { useVisibleMotion } from "./useVisibleMotion";

export function MusicProfileRadar({ axes, coverage }: { axes: InsightsProfileAxis[]; coverage: number }) {
  const { ref, entered, motionActive, reducedMotion } = useVisibleMotion();
  const chartData = useMemo(
    () => axes.map((axis) => ({ ...axis, chartValue: entered ? axis.value : 0 })),
    [axes, entered],
  );
  const ranked = useMemo(() => [...axes].sort((a, b) => b.value - a.value), [axes]);
  const summaryId = "music-profile-summary";
  const useRankedFallback = axes.length < 3 || (typeof window !== "undefined" && window.matchMedia("(max-width: 640px)").matches && axes.length > 5);

  if (useRankedFallback) {
    return (
      <div ref={ref} className="insights-radar" data-halo-active="false">
        <div className="space-y-3" role="img" aria-describedby={summaryId} aria-label="Ranked genre shares">
          {ranked.map((axis) => <div key={axis.key}><div className="mb-1 flex justify-between gap-3 text-sm"><span className="text-mist">{axis.label}</span><strong className="text-white">{axis.value.toFixed(1)}%</strong></div><div className="h-2 overflow-hidden rounded bg-white/10"><div className="h-full rounded bg-red-500" style={{ width: `${Math.min(axis.value, 100)}%` }} /></div></div>)}
          {axes.length < 3 ? <p className="text-sm text-mist">Limited genre detail: a ranked view is clearer than a radar with fewer than three real genres.</p> : null}
        </div>
        <ProfileLegend id={summaryId} ranked={ranked} coverage={coverage} />
      </div>
    );
  }

  return (
    <div ref={ref} className="insights-radar" data-halo-active={motionActive ? "true" : "false"}>
      <div className="insights-radar__chart" role="img" aria-describedby={summaryId} aria-label="Music family share radar chart">
        <div className="insights-radar__halo insights-radar__halo--outer" aria-hidden="true" />
        <div className="insights-radar__halo insights-radar__halo--inner" aria-hidden="true" />
        <ResponsiveContainer width="100%" height="100%">
          <RadarChart data={chartData} outerRadius="68%" margin={{ top: 34, right: 58, bottom: 34, left: 58 }}>
            <PolarGrid stroke="rgba(255,255,255,0.12)" radialLines={false} />
            <PolarAngleAxis dataKey="label" tick={radarTick} />
            <Tooltip content={<RadarTooltip />} cursor={false} />
            <Radar
              name="Share of detected plays"
              dataKey="chartValue"
              stroke="#ff4a4d"
              strokeWidth={2.5}
              fill="#ef2b2d"
              fillOpacity={0.3}
              dot={{ r: 3.5, fill: "#ff7b7d", stroke: "#111114", strokeWidth: 2 }}
              isAnimationActive={entered && !reducedMotion}
              animationDuration={850}
              animationEasing="ease-out"
            />
          </RadarChart>
        </ResponsiveContainer>
      </div>

      <ProfileLegend id={summaryId} ranked={ranked} coverage={coverage} />
    </div>
  );
}
function ProfileLegend({ id, ranked, coverage }: { id: string; ranked: InsightsProfileAxis[]; coverage: number }) {
  return <div id={id} className="insights-profile-legend"><p className="insights-coverage"><span>{Math.round(coverage * 100)}% of plays classified</span><span>{Math.round((1 - coverage) * 100)}% of plays unclassified</span></p><ol>{ranked.map((axis) => <li key={axis.key}><span>{axis.label}</span><strong>{axis.value.toFixed(1)}%</strong></li>)}</ol></div>;
}

function radarTick(props: { x?: string | number; y?: string | number; textAnchor?: string; payload?: { value?: string | number } }) {
  if (props.x == null || props.y == null || !props.payload?.value) return <g />;
  return (
    <text x={props.x} y={props.y} dy={4} textAnchor={props.textAnchor as "start" | "middle" | "end" | undefined} fill="#c7c7cf" fontSize={11.5} fontWeight={650}>
      {compactAxisLabel(String(props.payload.value))}
    </text>
  );
}

function compactAxisLabel(value: string) {
  return value
    .replace("Electronic / Atmospheric", "Electronic / Atmos.")
    .replace("Classical / Cinematic", "Classical / Cinema");
}

function RadarTooltip({ active, payload }: { active?: boolean; payload?: Array<{ payload: InsightsProfileAxis }> }) {
  const axis = payload?.[0]?.payload;
  if (!active || !axis) return null;
  return (
    <div className="insights-tooltip">
      <strong>{axis.label}</strong>
      <span>{axis.value.toFixed(1)}% of detected plays</span>
      <span>{axis.detectedPlays.toLocaleString()} classified plays</span>
      <span>{axis.confidence ?? "unknown"} confidence · {axis.metadataSource ?? "reliable genre metadata"}</span>
      {axis.contributingArtists?.length ? <span>Artists: {axis.contributingArtists.join(", ")}</span> : null}
    </div>
  );
}
