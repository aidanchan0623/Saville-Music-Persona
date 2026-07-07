import { Sparkles } from "lucide-react";
import { EmptyState } from "../components/EmptyState";
import type { PersonaReport, Prerequisites } from "../types/api";

interface Props {
  report: PersonaReport | null;
  prerequisites: Prerequisites | null;
  busy: boolean;
  onGenerate: (mode: "serious" | "playful" | "roast") => void;
}

export function ReportPage({ report, prerequisites, busy, onGenerate }: Props) {
  const disabled = busy || !prerequisites?.model_installed;
  const taste = report?.evidence?.taste_interpretation as { summary?: string; core_genre_families?: { name: string; share: number }[]; sonic_traits?: string[] } | undefined;
  return (
    <div className="space-y-6">
      <div className="flex flex-col justify-between gap-4 lg:flex-row lg:items-end">
        <div>
          <h1 className="text-3xl font-bold text-white">AI Persona Report</h1>
          <p className="mt-2 max-w-3xl text-mist">Gemma writes the prose from the factual profile JSON. Counts, rankings, and scores remain deterministic.</p>
        </div>
        <div className="flex flex-wrap gap-2">
          <button className="btn-secondary" disabled={disabled} onClick={() => onGenerate("serious")}>Serious Profile</button>
          <button className="btn-secondary" disabled={disabled} onClick={() => onGenerate("playful")}>Playful Profile</button>
          <button className="btn-secondary" disabled={disabled} onClick={() => onGenerate("roast")}>Roast Me Gently</button>
        </div>
      </div>
      {!prerequisites?.model_installed ? (
        <div className="rounded-lg border border-amber-300/20 bg-amber-300/10 p-4 text-sm text-amber-100">
          Ollama or gemma3:4b is unavailable. Deterministic dashboard pages still work; report writing is disabled until the model is installed and running.
        </div>
      ) : null}
      {!report ? (
        <EmptyState
          title="No persona report yet"
          body="Generate a report after refreshing your music data. The model receives only compact evidence, not raw private history exports."
          action={
            <button className="btn-primary" disabled={disabled} onClick={() => onGenerate("serious")}>
              <Sparkles size={17} /> {busy ? "Generating..." : "Generate Serious Profile"}
            </button>
          }
        />
      ) : (
        <article className="rounded-lg border border-line bg-panel/82 p-6 shadow-glow">
          <p className="text-sm uppercase tracking-[0.18em] text-violet-200">{report.mode} - {report.model}</p>
          <h2 className="mt-3 text-4xl font-black text-white">{report.headline}</h2>
          <div className="mt-6 grid gap-5 lg:grid-cols-[0.75fr_1.25fr]">
            <aside className="space-y-3">
              {report.personality_tags.map((tag) => (
                <div key={tag.tag} className="rounded-lg border border-white/10 bg-white/[0.04] p-4">
                  <h3 className="font-semibold text-white">{tag.tag}</h3>
                  <p className="mt-2 text-sm leading-6 text-mist">{tag.reason}</p>
                </div>
              ))}
            </aside>
            <div className="space-y-5 text-base leading-8 text-mist">
              {taste?.summary ? (
                <section className="rounded-lg border border-violet/20 bg-violet/10 p-4">
                  <h3 className="text-xl font-semibold text-white">What Your Taste Sounds Like</h3>
                  <p className="mt-2">{taste.summary}</p>
                  <div className="mt-3 flex flex-wrap gap-2">
                    {taste.core_genre_families?.slice(0, 3).map((item) => (
                      <span key={item.name} className="rounded-full border border-white/10 px-3 py-1 text-xs text-violet-100">
                        {item.name} {item.share}%
                      </span>
                    ))}
                    {taste.sonic_traits?.slice(0, 5).map((trait) => (
                      <span key={trait} className="rounded-full border border-white/10 px-3 py-1 text-xs text-mist">
                        {trait}
                      </span>
                    ))}
                  </div>
                </section>
              ) : null}
              <p className="text-lg text-white">{report.summary}</p>
              <Section title="Your current era" body={report.current_era} />
              <Section title="Your core identity" body={report.core_identity} />
              <Section title="Your listening habits" body={report.listening_habits} />
              <Section title="Your comfort artists" body={report.comfort_artists} />
              {report.report_sections.map((section) => <p key={section}>{section}</p>)}
            </div>
          </div>
          <details className="mt-6 rounded-lg border border-white/10 bg-black/20 p-4">
            <summary className="cursor-pointer font-medium text-white">Report evidence</summary>
            <pre className="mt-4 max-h-96 overflow-auto text-xs leading-5 text-mist">{JSON.stringify(report.evidence, null, 2)}</pre>
          </details>
        </article>
      )}
    </div>
  );
}

function Section({ title, body }: { title: string; body: string }) {
  if (!body) return null;
  return (
    <section>
      <h3 className="text-xl font-semibold text-white">{title}</h3>
      <p className="mt-2">{body}</p>
    </section>
  );
}
