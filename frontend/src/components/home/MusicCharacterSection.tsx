import { Sparkles } from "lucide-react";
import { useEffect, useState } from "react";
import { api } from "../../api/client";
import type { MusicCharacterResponse, MusicCharacterRewrite, MusicSource, Prerequisites } from "../../types/api";

type CharacterPeriod = "this_month" | "month" | "rolling_year";

interface Props {
  prerequisites: Prerequisites | null;
  source: MusicSource;
}

export function MusicCharacterSection({ prerequisites, source }: Props) {
  const [period, setPeriod] = useState<CharacterPeriod>("rolling_year");
  const [selectedMonth, setSelectedMonth] = useState<string | null>(null);
  const [character, setCharacter] = useState<MusicCharacterResponse | null>(null);
  const [rewrite, setRewrite] = useState<MusicCharacterRewrite | null>(null);
  const [loading, setLoading] = useState(false);
  const [rewriting, setRewriting] = useState(false);
  const [rewriteError, setRewriteError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setRewrite(null);
    setRewriteError(null);
    api.musicCharacter(period, period === "month" ? selectedMonth : null, source)
      .then((next) => {
        if (cancelled) return;
        setCharacter(next);
        if (!selectedMonth && next.period.available_months.length) {
          setSelectedMonth(next.period.available_months[next.period.available_months.length - 1].value);
        }
      })
      .catch(() => {
        if (!cancelled) setCharacter(null);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [period, selectedMonth, source]);

  if (!character) {
    return (
      <section className="rounded-[1.5rem] border border-line bg-panel/82 p-6">
        <p className="text-sm font-semibold uppercase tracking-[0.2em] text-violet-200">Your Music Character</p>
        <p className="mt-3 text-mist">{loading ? "Reading your music character..." : "Music Character will appear after a refresh with listening data."}</p>
      </section>
    );
  }

  const months = character.period.available_months;
  const primary = character.primary;
  const canRewrite = Boolean(prerequisites?.ollama_reachable && prerequisites.model_installed);
  const headline = rewrite?.headline || primary.name;
  const roast = rewrite?.friendly_roast || rewrite?.one_liner || primary.roast;
  const profile = rewrite?.profile_paragraph || primary.profile;

  const personalise = async () => {
    if (!canRewrite) return;
    setRewriting(true);
    setRewriteError(null);
    try {
      setRewrite(await api.rewriteMusicCharacter(period, period === "month" ? selectedMonth : null, "playful", source));
    } catch (error) {
      setRewriteError(error instanceof Error ? error.message : "Personalised rewrite unavailable.");
    } finally {
      setRewriting(false);
    }
  };

  return (
    <section className="overflow-hidden rounded-[1.5rem] border border-line bg-[linear-gradient(135deg,rgba(20,16,16,0.94),rgba(5,5,5,0.98))] shadow-glow">
      <div className="grid gap-0 xl:grid-cols-[1.05fr_0.95fr]">
        <div className="relative border-b border-white/10 p-6 lg:p-8 xl:border-b-0 xl:border-r">
          <div className="absolute inset-0 bg-[radial-gradient(circle_at_18%_18%,rgba(239,68,68,0.18),transparent_35%)]" />
          <div className="relative">
            <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
              <div>
                <p className="text-sm font-semibold uppercase tracking-[0.2em] text-violet-200">Your Music Character</p>
                <h2 className="mt-3 text-3xl font-black leading-tight text-white md:text-5xl">{headline}</h2>
                <p className="mt-2 text-sm text-mist">{displayPeriodLabel(character.period.label, period)}</p>
              </div>
              <div className="flex flex-wrap gap-2 rounded-lg border border-white/10 bg-white/[0.035] p-2">
                <PeriodButton active={period === "this_month"} label="This Month" onClick={() => setPeriod("this_month")} />
                <PeriodButton active={period === "month"} label="Select Month" onClick={() => setPeriod("month")} />
                <PeriodButton active={period === "rolling_year"} label="Rolling Year" onClick={() => setPeriod("rolling_year")} />
                {period === "month" ? (
                  <select className="rounded-md border border-white/10 bg-ink px-3 py-2 text-sm text-white" value={selectedMonth ?? months.at(-1)?.value ?? ""} onChange={(event) => setSelectedMonth(event.target.value)}>
                    {months.map((month) => <option key={month.value} value={month.value}>{month.label}</option>)}
                  </select>
                ) : null}
              </div>
            </div>

            {character.sample_warning ? <p className="mt-5 rounded-md border border-amber-200/10 bg-amber-200/10 p-3 text-sm text-amber-100">{character.sample_warning}</p> : null}

            <p className="mt-6 rounded-xl border border-violet/25 bg-violet/10 p-4 text-xl font-black leading-snug text-violet-100">{roast}</p>
            <p className="mt-5 max-w-3xl text-base leading-8 text-mist">{profile}</p>

            <div className="mt-6 flex flex-wrap gap-2">
              {character.evidence_chips.slice(0, 7).map((chip) => (
                <span key={chip} className="rounded-full border border-white/10 bg-white/[0.055] px-3 py-1.5 text-sm text-mist">{chip}</span>
              ))}
            </div>

            <div className="mt-6">
              <button className="btn-primary" onClick={personalise} disabled={!canRewrite || rewriting}>
                <Sparkles size={17} /> {canRewrite ? rewriting ? "Rewriting..." : "Make it more personal" : "Personalised rewrite unavailable - Ollama is offline"}
              </button>
              {rewriteError ? <p className="mt-3 text-sm text-amber-100">{rewriteError}</p> : null}
            </div>
          </div>
        </div>

        <div className="p-6 lg:p-8">
          <div className="grid gap-4 sm:grid-cols-2">
            <CharacterMini title="Secondary character" value={character.secondary?.name ?? "No strong secondary yet"} body={character.secondary?.profile ?? "The primary character carries most of the signal for this period."} />
            <CharacterMini title="Behaviour modifier" value={character.modifier?.name ?? "No clear modifier"} body={character.modifier?.roast ?? "No behaviour pattern is strong enough to label separately yet."} />
          </div>

          <div className="mt-6 rounded-xl border border-white/10 bg-white/[0.04] p-5">
            <h3 className="text-lg font-black text-white">Why it fits</h3>
            <ul className="mt-4 space-y-3 text-sm leading-6 text-mist">
              {(rewrite?.why_it_fits?.length ? rewrite.why_it_fits : primary.evidence).slice(0, 4).map((item) => (
                <li key={item} className="flex gap-2">
                  <span className="mt-2 h-1.5 w-1.5 shrink-0 rounded-full bg-violet" />
                  <span>{item}</span>
                </li>
              ))}
            </ul>
          </div>
        </div>
      </div>
    </section>
  );
}

function PeriodButton({ active, label, onClick }: { active: boolean; label: string; onClick: () => void }) {
  return <button className={`rounded-md px-3 py-2 text-sm font-semibold transition ${active ? "bg-violet text-white" : "text-mist hover:bg-white/10 hover:text-white"}`} onClick={onClick}>{label}</button>;
}

function CharacterMini({ title, value, body }: { title: string; value: string; body: string }) {
  return (
    <div className="rounded-xl border border-white/10 bg-white/[0.04] p-4">
      <p className="text-xs font-semibold uppercase tracking-[0.16em] text-mist/60">{title}</p>
      <p className="mt-3 text-lg font-black leading-6 text-white">{value}</p>
      <p className="mt-3 text-sm leading-6 text-mist">{body}</p>
    </div>
  );
}

function displayPeriodLabel(label: string | undefined, period: CharacterPeriod) {
  if (period === "rolling_year") return "Your Music Character - Rolling Year";
  return `Your Music Character - ${label ?? "Selected Period"}`;
}
