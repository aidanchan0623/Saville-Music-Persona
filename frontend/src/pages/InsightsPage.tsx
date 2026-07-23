import { AlertCircle, ArrowRight, RefreshCw } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import type { ReactNode } from "react";
import { api } from "../api/client";
import { ArtistAvatar, TrackArtwork } from "../components/Artwork";
import { CompactScoreGauge } from "../components/insights/CompactScoreGauge";
import { ListeningRhythmChart } from "../components/insights/ListeningRhythmChart";
import { MusicProfileRadar } from "../components/insights/MusicProfileRadar";
import type { InsightsResponse, MusicSource } from "../types/api";
import { formatDate, formatMinutes } from "../utils/format";
import "./InsightsPage.css";

type InsightsPeriod = "this_month" | "month" | "rolling_year";

export function InsightsPage({ source, onOpenTop10 }: { source: MusicSource; titleAnimationKey: string; onOpenTop10: () => void }) {
  const [period, setPeriod] = useState<InsightsPeriod>("rolling_year");
  const [selectedMonth, setSelectedMonth] = useState<string | null>(null);
  const [data, setData] = useState<InsightsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [reloadKey, setReloadKey] = useState(0);
  const activeMonth = period === "month" ? selectedMonth : null;

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    setData(null);
    api.insights(period, activeMonth, source)
      .then((next) => {
        if (cancelled) return;
        setData(next);
        if (!selectedMonth && next.period.available_months.length) {
          setSelectedMonth(next.period.available_months[next.period.available_months.length - 1].value);
        }
      })
      .catch((reason) => {
        if (!cancelled) setError(reason instanceof Error ? reason.message : "Insights could not be loaded.");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [period, activeMonth, source, reloadKey]);

  const months = data?.period.available_months ?? [];

  return (
    <div className="insights-page">
      <div className="insights-content">
        <header className="insights-header">
          <div>
            <p className="insights-eyebrow">Listening evidence</p>
            <h1>Insights</h1>
            <p className="insights-header__lede">Your sound profile, listening scores, and rhythm in one view.</p>
          </div>
          <div className="insights-period-control" aria-label="Insights period">
            <div className="insights-period-control__buttons">
              <PeriodButton active={period === "this_month"} onClick={() => setPeriod("this_month")}>This Month</PeriodButton>
              <PeriodButton active={period === "month"} onClick={() => setPeriod("month")}>Select Month</PeriodButton>
              <PeriodButton active={period === "rolling_year"} onClick={() => setPeriod("rolling_year")}>Rolling Year</PeriodButton>
            </div>
            {period === "month" ? (
              <select value={selectedMonth ?? months.at(-1)?.value ?? ""} onChange={(event) => setSelectedMonth(event.target.value)} aria-label="Select insights month">
                {months.map((month) => <option key={month.value} value={month.value}>{month.label}</option>)}
              </select>
            ) : null}
          </div>
        </header>

        {data ? <p className="insights-period-label">{data.period.display_label}</p> : null}
        {loading && !data ? <InsightsLoading /> : null}
        {error && !data ? <InsightsError message={error} onRetry={() => setReloadKey((value) => value + 1)} /> : null}

        {data ? (
          <div className={loading ? "insights-dashboard insights-dashboard--loading" : "insights-dashboard"} aria-busy={loading}>
            {error ? <p className="insights-inline-error" role="alert"><AlertCircle size={16} /> {error}</p> : null}
            <CompactMetrics data={data} />

            <section className="insights-surface insights-profile" aria-labelledby="music-profile-title">
              <div className="insights-section-heading">
                <p className="insights-eyebrow">What you listen to</p>
                <h2 id="music-profile-title">Your Music Profile</h2>
                <p>Actual classified play share using Saville's canonical artist and genre mappings.</p>
              </div>
              <div className="insights-profile__grid">
                <div className="min-w-0">
                  <MusicProfileRadar axes={data.musicProfile.axes} coverage={data.musicProfile.coverage} />
                  {data.musicProfile.coverage < 0.6 ? (
                    <p className="insights-coverage-warning">Genre coverage is limited. {data.musicProfile.unclassifiedPlays.toLocaleString()} plays remain unclassified and are not fabricated.</p>
                  ) : null}
                </div>
                <div className="insights-scores" aria-label={`Listening scores for ${data.period.display_label}`}>
                  <div className="insights-scores__heading">
                    <h3>Listening scores</h3>
                    <span>{data.scores.length} deterministic measures</span>
                  </div>
                  {data.scores.map((score, index) => <CompactScoreGauge key={score.key} score={score} index={index} />)}
                </div>
              </div>
            </section>

            <ListeningRhythmChart data={data.rhythm} period={data.period} />
            <RankingsSection data={data} onOpenTop10={onOpenTop10} />
            <IntensitySection data={data} />
          </div>
        ) : null}
      </div>
    </div>
  );
}

function PeriodButton({ active, onClick, children }: { active: boolean; onClick: () => void; children: string }) {
  return <button type="button" aria-pressed={active} className={active ? "is-active" : ""} onClick={onClick}>{children}</button>;
}

function CompactMetrics({ data }: { data: InsightsResponse }) {
  const metrics = [
    { label: "Selected total", value: data.summary.detectedMinutesFormatted, note: `${data.summary.detectedPlays.toLocaleString()} detected plays` },
    { label: "Active days", value: data.summary.activeDays.toLocaleString(), note: "At least one detected music play" },
    { label: "Average active day", value: formatMinutes(data.summary.averageActiveDayMinutes), note: "Days with usable duration" },
    { label: "Longest day", value: formatMinutes(data.summary.longestDayMinutes), note: data.summary.longestDayDate ? formatDate(data.summary.longestDayDate) : "No detected minutes" },
  ];
  return (
    <section className="insights-metrics" aria-label="Selected period summary">
      {metrics.map((metric) => (
        <div key={metric.label}>
          <p>{metric.label}</p>
          <strong>{metric.value}</strong>
          <span>{metric.note}</span>
        </div>
      ))}
    </section>
  );
}

function RankingsSection({ data, onOpenTop10 }: { data: InsightsResponse; onOpenTop10: () => void }) {
  return (
    <section className="insights-surface insights-rankings" aria-labelledby="rankings-title">
      <div className="insights-section-heading insights-section-heading--split">
        <div>
          <p className="insights-eyebrow">What keeps returning</p>
          <h2 id="rankings-title">Period leaders</h2>
          <p>Same deterministic play-count ranking used by Top 10.</p>
        </div>
        <button type="button" className="insights-text-link" onClick={onOpenTop10}>View full Top 10 <ArrowRight size={15} /></button>
      </div>
      <div className="insights-rankings__grid">
        <RankingList title="Top artists by plays">
          {data.topArtists.map((item) => (
            <RankingRow key={`${item.rank}-${item.artist}`} rank={item.rank} name={item.artist} detail={`${item.detectedPlays.toLocaleString()} plays`} value={item.detectedPlays} max={data.topArtists[0]?.detectedPlays ?? 1}>
              <ArtistAvatar artistImageUrl={item.imageUrl} artistName={item.artist} size="sm" />
            </RankingRow>
          ))}
        </RankingList>
        <RankingList title="Most repeated songs">
          {data.repeatedSongs.map((item) => (
            <RankingRow key={`${item.rank}-${item.title}-${item.artist}`} rank={item.rank} name={item.title} subline={item.artist} detail={`${item.detectedPlays.toLocaleString()} plays`} value={item.detectedPlays} max={data.repeatedSongs[0]?.detectedPlays ?? 1}>
              <TrackArtwork trackImageUrl={item.imageUrl} title={item.title} size="sm" />
            </RankingRow>
          ))}
        </RankingList>
      </div>
    </section>
  );
}

function RankingList({ title, children }: { title: string; children: ReactNode }) {
  return <div className="insights-ranking-list"><h3>{title}</h3><ol>{children}</ol></div>;
}

function RankingRow({ rank, name, subline, detail, value, max, children }: { rank: number; name: string; subline?: string; detail: string; value: number; max: number; children: ReactNode }) {
  return (
    <li className="insights-ranking-row">
      <span className="insights-ranking-row__rank">{rank}</span>
      {children}
      <div className="insights-ranking-row__copy" title={subline ? `${name} - ${subline}` : name}>
        <div><strong>{name}</strong><span>{detail}</span></div>
        {subline ? <p>{subline}</p> : null}
        <span className="insights-ranking-row__bar" aria-hidden="true"><i style={{ width: `${Math.max(4, value / Math.max(max, 1) * 100)}%` }} /></span>
      </div>
    </li>
  );
}

function IntensitySection({ data }: { data: InsightsResponse }) {
  const values = data.dailyIntensity;
  const weeks = useMemo(() => [...new Set(values.map((item) => item.week_start))], [values]);
  const max = Math.max(...values.map((item) => item.value), 1);
  const activeDays = values.filter((item) => item.value > 0);
  const peak = activeDays.reduce<(typeof values)[number] | null>((best, item) => !best || item.value > best.value ? item : best, null);
  return (
    <section className="insights-surface insights-intensity" aria-labelledby="intensity-title">
      <div className="insights-section-heading insights-section-heading--split">
        <div>
          <p className="insights-eyebrow">Recent intensity</p>
          <h2 id="intensity-title">Daily listening intensity</h2>
        </div>
        <p>{activeDays.length} active days{peak ? ` | peak ${formatMinutes(peak.value)} on ${formatDate(peak.date)}` : ""}</p>
      </div>
      <div className="insights-heatmap-scroll" tabIndex={0} aria-label="Scrollable daily intensity heatmap">
        <div className="insights-heatmap" style={{ gridTemplateColumns: `repeat(${Math.max(weeks.length, 1)}, 13px)` }}>
          {values.map((item) => {
            const column = weeks.indexOf(item.week_start) + 1;
            const opacity = item.value === 0 ? 0.06 : 0.18 + item.value / max * 0.82;
            return <span key={item.date} title={`${formatDate(item.date)}: ${item.value} detected minutes`} style={{ gridColumn: column, gridRow: item.weekday_index + 1, backgroundColor: `rgba(239,43,45,${opacity})` }} />;
          })}
        </div>
      </div>
      <p className="sr-only">{activeDays.length} of {values.length} days contain detected listening minutes. {peak ? `The highest day is ${peak.date} with ${peak.value} detected minutes.` : "No days have usable duration totals."}</p>
    </section>
  );
}

function InsightsLoading() {
  return <div className="insights-loading" role="status"><RefreshCw size={18} /> Building deterministic insights...</div>;
}

function InsightsError({ message, onRetry }: { message: string; onRetry: () => void }) {
  return <div className="insights-error" role="alert"><AlertCircle size={20} /><div><strong>Insights could not be loaded</strong><p>{message}</p></div><button type="button" onClick={onRetry}>Try again</button></div>;
}
