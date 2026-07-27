import type { MusicSource, PersonaReport } from "../types/api";
import { PersonaStoryExperience } from "./report/PersonaStoryExperience";
import "./ReportPage.css";

interface Props {
  report: PersonaReport | null;
  busy: boolean;
  onGenerate: () => Promise<{ ok: boolean; message: string }>;
  source: MusicSource;
  titleAnimationKey: string;
}

export function ReportPage({ report, busy, onGenerate, source, titleAnimationKey }: Props) {
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
      busy={busy}
      onGenerate={onGenerate}
      titleAnimationKey={titleAnimationKey}
    />
  );
}
