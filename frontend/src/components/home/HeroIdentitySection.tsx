import { ArrowRight, RefreshCw, Waves } from "lucide-react";
import { formatDateTime } from "../../utils/format";

interface Props {
  identityTitle: string;
  summary: string;
  currentState: string;
  connectedLabel: string;
  modelLabel: string;
  lastRefreshedAt: string | null;
  busy: boolean;
  onExploreTaste: () => void;
  onViewThisMonth: () => void;
  onRefresh: () => void;
}

export function HeroIdentitySection({
  identityTitle,
  summary,
  currentState,
  connectedLabel,
  modelLabel,
  lastRefreshedAt,
  busy,
  onExploreTaste,
  onViewThisMonth,
  onRefresh,
}: Props) {
  return (
    <section className="relative isolate min-h-[30rem] overflow-hidden rounded-[2rem] border border-white/10 bg-[#090505] px-6 py-8 shadow-glow md:px-10 lg:px-12">
      <div className="absolute inset-0 -z-10 bg-[radial-gradient(circle_at_18%_18%,rgba(239,68,68,0.24),transparent_30%),radial-gradient(circle_at_78%_12%,rgba(153,27,27,0.28),transparent_26%),linear-gradient(140deg,rgba(5,5,5,0.96),rgba(28,12,12,0.96)_52%,rgba(5,5,5,0.98))]" />
      <div className="absolute -right-28 top-10 -z-10 h-96 w-96 rounded-full bg-violet/20 blur-3xl" />
      <div className="absolute bottom-0 left-0 -z-10 h-44 w-full bg-gradient-to-t from-black/40 to-transparent" />

      <div className="flex flex-col gap-8 lg:grid lg:grid-cols-[minmax(0,1.35fr)_minmax(18rem,0.65fr)] lg:items-center">
        <div className="max-w-4xl">
          <div className="flex flex-wrap gap-2 text-xs">
            <span className="rounded-full border border-emerald-300/20 bg-emerald-300/10 px-3 py-1 text-emerald-100">{connectedLabel}</span>
            <span className="rounded-full border border-violet/25 bg-violet/10 px-3 py-1 text-violet-100">{modelLabel}</span>
          </div>
          <p className="mt-7 text-sm font-semibold uppercase tracking-[0.24em] text-violet-100">Private music identity</p>
          <h1 className="mt-3 max-w-5xl text-5xl font-black leading-[0.94] tracking-tight text-white md:text-6xl xl:text-7xl">
            Saville Music Persona
          </h1>
          <p className="mt-5 max-w-4xl text-2xl font-black leading-tight text-violet-100 md:text-3xl xl:text-4xl">
            {identityTitle}
          </p>
          <p className="mt-5 max-w-3xl text-base leading-8 text-mist md:text-lg">{summary}</p>
          <p className="mt-4 max-w-3xl border-l-2 border-violet/60 pl-4 text-sm leading-7 text-violet-100 md:text-base">
            {currentState}
          </p>

          <div className="mt-7 flex flex-wrap gap-3">
            <button className="btn-primary px-5 py-3" onClick={onExploreTaste}>
              Explore My Taste <ArrowRight size={18} />
            </button>
            <button className="btn-secondary px-5 py-3" onClick={onViewThisMonth}>
              View This Month <ArrowRight size={18} />
            </button>
          </div>

          <div className="mt-6 flex flex-wrap items-center gap-3 text-sm text-mist">
            <span>Last refreshed: {formatDateTime(lastRefreshedAt)}</span>
            <button className="inline-flex items-center gap-2 text-violet-100 transition hover:text-white disabled:opacity-50" onClick={onRefresh} disabled={busy}>
              <RefreshCw size={14} className={busy ? "animate-spin" : ""} />
              {busy ? "Refreshing data" : "Refresh data"}
            </button>
          </div>
        </div>

        <div className="relative mx-auto aspect-square w-full max-w-[22rem] xl:max-w-[24rem]">
          <div className="absolute inset-0 rounded-full border border-white/10 bg-white/[0.03] backdrop-blur" />
          <div className="absolute inset-[8%] rounded-full border border-violet/25 bg-violet/10 shadow-glow" />
          <div className="absolute inset-[21%] rounded-full border border-indigo/30 bg-indigo/10" />
          <div className="absolute inset-[34%] grid place-items-center rounded-full border border-white/15 bg-ink/80">
            <Waves className="text-violet-100" size={46} />
          </div>
          <SoundBar className="left-[16%] top-[34%] h-24" />
          <SoundBar className="left-[28%] top-[23%] h-36" delay />
          <SoundBar className="right-[30%] top-[20%] h-44" />
          <SoundBar className="right-[16%] top-[36%] h-28" delay />
          <div className="absolute bottom-12 left-1/2 w-[78%] -translate-x-1/2 rounded-full border border-white/10 bg-black/30 px-4 py-3 text-center text-xs text-mist backdrop-blur">
            Private, local-first music identity analysis
          </div>
        </div>
      </div>
    </section>
  );
}

function SoundBar({ className, delay = false }: { className: string; delay?: boolean }) {
  return (
    <span
      className={`absolute w-2 rounded-full bg-gradient-to-t from-magenta via-violet to-indigo opacity-80 shadow-[0_0_24px_rgba(239,68,68,0.45)] ${className} ${delay ? "animate-[pulse_3s_ease-in-out_infinite]" : "animate-[pulse_4s_ease-in-out_infinite]"}`}
    />
  );
}
