import { RefreshCw } from "lucide-react";
import { useEffect, useState } from "react";
import { api } from "../api/client";
import { PageTitlePanel } from "../components/PageTitlePanel";
import type {
  AuthStatus,
  MusicSource,
  OverviewPeriodKey,
  OverviewResponse,
  Prerequisites,
} from "../types/api";
import { resolvePersonaVisualTheme } from "../utils/personaVisualTheme";

interface Props {
  overview: OverviewResponse | null;
  auth: AuthStatus | null;
  prerequisites: Prerequisites | null;
  busy: boolean;
  useDemo: boolean;
  onRefresh: () => void;
  onOpenSettings: () => void;
  onOpenReport: () => void;
  source: MusicSource;
  titleAnimationKey: string;
}

const PERIOD_OPTIONS: { key: OverviewPeriodKey; label: string }[] = [
  { key: "this_month", label: "This Month" },
  { key: "month", label: "Select Month" },
  { key: "last_30", label: "Last 30 Days" },
  { key: "rolling_year", label: "Rolling Year" },
  { key: "all", label: "All History" },
];

export function OverviewPage({
  overview,
  busy,
  useDemo,
  onRefresh,
  onOpenSettings,
  onOpenReport,
  source,
  titleAnimationKey,
}: Props) {
  const [period, setPeriod] = useState<OverviewPeriodKey>("this_month");
  const [selectedMonth, setSelectedMonth] = useState<string | null>(null);
  const [activeResponse, setActiveResponse] = useState<OverviewResponse | null>(overview);
  const [periodLoading, setPeriodLoading] = useState(false);
  const [periodError, setPeriodError] = useState<string | null>(null);

  useEffect(() => {
    setPeriod("this_month");
    setSelectedMonth(null);
    setActiveResponse(overview);
  }, [overview?.languageFingerprint, source]);

  useEffect(() => {
    if (!overview) return;
    if (period === "this_month" && !selectedMonth) {
      setActiveResponse(overview);
      setPeriodError(null);
      return;
    }
    let cancelled = false;
    setPeriodLoading(true);
    setPeriodError(null);
    api.overview(period, period === "month" ? selectedMonth : null, source)
      .then((value) => {
        if (!cancelled) setActiveResponse(value);
      })
      .catch((error) => {
        if (!cancelled) setPeriodError(error instanceof Error ? error.message : "This timeframe could not be loaded.");
      })
      .finally(() => {
        if (!cancelled) setPeriodLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [period, selectedMonth, source, overview?.languageFingerprint]);

  if (!activeResponse) {
    return (
      <div className="space-y-6">
        <PageTitlePanel
          eyebrow="Private local music identity"
          title="No listening analysis loaded yet"
          titleAnimationKey={titleAnimationKey}
          subtitle={source === "spotify" ? "Connect Spotify to generate a music profile from your Spotify top artists, top tracks, saved songs, playlists and recent plays." : "Connect YouTube Music for private local analysis, or switch on demo data to explore the dashboard without account access."}
          actions={
            <div className="flex flex-wrap justify-center gap-3">
              <button className="btn-primary" onClick={onRefresh} disabled={busy}>
                <RefreshCw size={17} /> {busy ? "Refreshing..." : useDemo ? "Load Demo Data" : "Refresh My Music Data"}
              </button>
              <button className="btn-secondary" onClick={onOpenSettings}>Open Settings</button>
            </div>
          }
        />
      </div>
    );
  }

  const data = activeResponse.overview;
  const identity = activeResponse.identity;
  const visualTheme = resolvePersonaVisualTheme(data, null);
  const updatedLabel = data.last_refreshed_at ? formatShortDate(data.last_refreshed_at) : "not refreshed yet";
  const months = activeResponse.selectedPeriod.availableMonths;

  return (
    <div className="space-y-7">
      <section className="overview-period-control" aria-label="Overview timeframe">
        <div className="overview-period-control__buttons">
          {PERIOD_OPTIONS.map((option) => (
            <button
              key={option.key}
              className={period === option.key ? "overview-period-button overview-period-button--active" : "overview-period-button"}
              type="button"
              aria-pressed={period === option.key}
              onClick={() => {
                setPeriod(option.key);
                if (option.key === "month" && !selectedMonth) setSelectedMonth(months[months.length - 1]?.value ?? null);
              }}
            >
              {option.label}
            </button>
          ))}
        </div>
        {period === "month" ? (
          <select
            className="overview-period-select"
            value={selectedMonth ?? ""}
            onChange={(event) => setSelectedMonth(event.target.value || null)}
            aria-label="Select overview month"
          >
            {months.map((item) => <option key={item.value} value={item.value}>{item.label}</option>)}
          </select>
        ) : null}
        <p className="overview-period-control__label">{activeResponse.selectedPeriod.label}</p>
      </section>

      {periodLoading ? <p className="overview-period-status" role="status">Loading {periodLabel(period).toLowerCase()}...</p> : null}
      {periodError ? <p className="overview-period-status overview-period-status--error" role="alert">{periodError}</p> : null}

      <PageTitlePanel
        eyebrow="Private music identity"
        title={identity.characterTitle}
        titleAnimationKey={`${titleAnimationKey}-${activeResponse.languageFingerprint}`}
        titleClassName="max-w-4xl text-3xl font-black leading-tight text-white md:text-4xl"
        subtitle={`${identity.tagline} ${identity.explanation}`}
        subtitleClassName="mt-4 max-w-3xl text-base leading-7 text-mist"
        lineMode="animated"
        className="overview-hero-panel"
        backgroundImage={visualTheme.primaryImage.src}
        backgroundPosition={visualTheme.primaryImage.position ?? visualTheme.position}
        overlayStrength={visualTheme.overlayStrength}
        actions={
          <div className="overview-hero-sound">
            <p className="overview-hero-sound__label">Most active sound</p>
            <p className="overview-hero-sound__value">{identity.mostActiveSound.label}</p>
            <p className="overview-hero-sound__context">{identity.mostActiveSound.description}</p>
            <button className="btn-primary mt-5" type="button" onClick={onOpenReport}>Open Persona Report</button>
          </div>
        }
        metadata={
          <span>{activeResponse.sourceLabel} &middot; {activeResponse.selectedPeriod.label} &middot; {data.coverage.days_represented.toLocaleString()} active days &middot; Updated {updatedLabel}</span>
        }
      />

      <section className="overview-coverage-strip" aria-label="Analysis coverage">
        <div><span>Detected plays</span><strong>{data.total_detected_plays.toLocaleString()}</strong></div>
        <div><span>Active days</span><strong>{data.coverage.days_represented.toLocaleString()}</strong></div>
        <div><span>History range</span><strong>{data.coverage.earliest_detected_play || "Not available"}</strong></div>
        <div><span>Status</span><strong>{data.coverage.history_coverage_status}</strong></div>
      </section>
    </div>
  );
}

function periodLabel(period: OverviewPeriodKey) {
  return PERIOD_OPTIONS.find((option) => option.key === period)?.label ?? "period";
}

function formatShortDate(value: string) {
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return value;
  return parsed.toLocaleDateString(undefined, { month: "short", day: "numeric", year: "numeric" });
}
