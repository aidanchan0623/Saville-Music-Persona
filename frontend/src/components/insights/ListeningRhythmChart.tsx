import { useMemo, useState } from "react";
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import type { InsightsResponse, InsightsRhythmPoint } from "../../types/api";
import { formatMinutes } from "../../utils/format";
import { useVisibleMotion } from "./useVisibleMotion";

type RhythmMode = "weekly" | "monthly";

export function ListeningRhythmChart({ data, period }: { data: InsightsResponse["rhythm"]; period: InsightsResponse["period"] }) {
  const [preferredMode, setPreferredMode] = useState<RhythmMode>(() => (period.period === "rolling_year" ? "monthly" : "weekly"));
  const { ref, entered, reducedMotion } = useVisibleMotion();
  const monthlyAvailable = period.period === "rolling_year" || data.monthly.length > 1;
  const mode: RhythmMode = preferredMode === "monthly" && !monthlyAvailable ? "weekly" : preferredMode;
  const points = data[mode];
  const title = mode === "weekly" ? "Weekly listening rhythm" : "Monthly listening rhythm";
  const maxTicks = mode === "weekly" ? 10 : 12;
  const interval = Math.max(0, Math.ceil(points.length / maxTicks) - 1);
  const visibleData = useMemo(() => points.map((point) => ({ ...point, chartMinutes: entered ? point.detectedMinutes : 0 })), [entered, points]);

  return (
    <section ref={ref} className="insights-surface insights-rhythm" aria-labelledby="listening-rhythm-title">
      <div className="insights-section-heading insights-section-heading--split">
        <div>
          <p className="insights-eyebrow">When and how heavily</p>
          <h2 id="listening-rhythm-title">{title}</h2>
          <p>Detected minutes from tracks with usable duration metadata.</p>
        </div>
        <div className="insights-segmented" aria-label="Listening rhythm interval">
          <button type="button" aria-pressed={mode === "weekly"} onClick={() => setPreferredMode("weekly")}>Weekly</button>
          <button
            type="button"
            aria-pressed={mode === "monthly"}
            aria-disabled={!monthlyAvailable}
            disabled={!monthlyAvailable}
            title={!monthlyAvailable ? "Monthly trend needs more than one month in the selected period." : undefined}
            onClick={() => setPreferredMode("monthly")}
          >
            Monthly
          </button>
          <span className={mode === "monthly" ? "insights-segmented__slider insights-segmented__slider--right" : "insights-segmented__slider"} aria-hidden="true" />
        </div>
      </div>

      <div className="insights-rhythm__chart" role="img" aria-label={`${title} for ${period.display_label}`}>
        {points.length ? (
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={visibleData} margin={{ top: 12, right: 8, bottom: 4, left: 0 }}>
              <CartesianGrid stroke="rgba(255,255,255,0.07)" vertical={false} />
              <XAxis dataKey="label" axisLine={false} tickLine={false} tick={{ fill: "#9f9fa8", fontSize: 11 }} interval={interval} minTickGap={8} height={34} />
              <YAxis axisLine={false} tickLine={false} tick={{ fill: "#9f9fa8", fontSize: 11 }} width={42} />
              <Tooltip content={<RhythmTooltip />} cursor={{ fill: "rgba(239,43,45,0.08)" }} />
              <Bar
                key={`${period.period}-${period.month ?? "current"}-${mode}`}
                dataKey="chartMinutes"
                fill="#ef2b2d"
                radius={[5, 5, 0, 0]}
                maxBarSize={48}
                isAnimationActive={entered && !reducedMotion}
                animationDuration={760}
                animationEasing="ease-out"
              />
            </BarChart>
          </ResponsiveContainer>
        ) : (
          <p className="insights-empty-inline">No detected minutes are available for this period.</p>
        )}
      </div>

      <div className="sr-only">
        <p>{title}</p>
        <ul>
          {points.map((point) => (
            <li key={point.startDate}>{point.label}: {point.detectedMinutes} detected minutes, {point.playCount} detected plays, {point.durationCoveragePercent}% duration coverage.</li>
          ))}
        </ul>
      </div>
    </section>
  );
}

function RhythmTooltip({ active, payload }: { active?: boolean; payload?: Array<{ payload: InsightsRhythmPoint }> }) {
  const point = payload?.[0]?.payload;
  if (!active || !point) return null;
  return (
    <div className="insights-tooltip">
      <strong>{point.label}</strong>
      <span>{point.detectedMinutes.toLocaleString()} detected minutes</span>
      <span>{formatMinutes(point.detectedMinutes)}</span>
      <span>{point.playCount.toLocaleString()} detected plays</span>
      <span>{Math.round(point.durationCoveragePercent)}% duration coverage</span>
    </div>
  );
}
