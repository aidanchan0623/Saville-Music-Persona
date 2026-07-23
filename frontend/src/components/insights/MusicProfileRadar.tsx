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

      <div id={summaryId} className="insights-profile-legend">
        <p className="insights-coverage">
          <span>{Math.round(coverage * 100)}% classified</span>
          <span>{Math.round((1 - coverage) * 100)}% unclassified</span>
        </p>
        <ol>
          {ranked.map((axis) => (
            <li key={axis.key}>
              <span>{axis.label}</span>
              <strong>{axis.value.toFixed(1)}%</strong>
            </li>
          ))}
        </ol>
      </div>
    </div>
  );
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
      <span>{formatWeightedPlays(axis.detectedPlays)} classified play weight</span>
    </div>
  );
}

function formatWeightedPlays(value: number) {
  return Number.isInteger(value) ? value.toLocaleString() : value.toFixed(1);
}
