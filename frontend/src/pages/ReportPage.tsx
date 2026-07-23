import type { MusicSource, PersonaReport, Prerequisites } from "../types/api";
import { PersonaStoryExperience } from "./report/PersonaStoryExperience";
import "./ReportPage.css";

interface Props {
  report: PersonaReport | null;
  prerequisites: Prerequisites | null;
  busy: boolean;
  onGenerate: (mode: "serious" | "playful" | "roast") => void;
  source: MusicSource;
  titleAnimationKey: string;
}

export function ReportPage({ report, prerequisites, busy, onGenerate, source, titleAnimationKey }: Props) {
  if (!report) {
    return (
      <section className="persona-report-empty" aria-live="polite">
        <p className="persona-report-empty__eyebrow">Persona Report</p>
        <h1 key={titleAnimationKey}>{busy ? "Writing your listening story" : "No persona story yet"}</h1>
        <p>
          {busy
            ? "The deterministic profile is ready; the language layer is finishing locally."
            : source === "spotify"
              ? "Connect and refresh Spotify, then return here for your report."
              : "Refresh YouTube Music data or import Takeout history, then return here for your report."}
        </p>
      </section>
    );
  }

  return (
    <PersonaStoryExperience
      report={report}
      modelReady={Boolean(prerequisites?.ollama_reachable && prerequisites.model_installed)}
      busy={busy}
      onGenerate={onGenerate}
      titleAnimationKey={titleAnimationKey}
    />
  );
}
