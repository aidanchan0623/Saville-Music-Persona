import { ExternalLink, ShieldCheck } from "lucide-react";
import { StatusPill } from "../components/StatusPill";
import type { AuthStatus, Prerequisites } from "../types/api";

interface Props {
  auth: AuthStatus | null;
  prerequisites: Prerequisites | null;
  useDemo: boolean;
  busy: boolean;
  onUseDemoChange: (value: boolean) => void;
  onCheckAuth: () => void;
  onImportTakeout: (file: File) => void;
}

export function SettingsPage({ auth, prerequisites, useDemo, busy, onUseDemoChange, onCheckAuth, onImportTakeout }: Props) {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-white">Settings</h1>
        <p className="mt-2 text-mist">Local connection status, demo mode, and private authentication guidance.</p>
      </div>

      <section className="rounded-lg border border-line bg-panel/82 p-5">
        <div className="flex flex-col justify-between gap-4 md:flex-row md:items-start">
          <div>
            <h2 className="text-xl font-semibold text-white">Connect YouTube Music</h2>
            <p className="mt-2 max-w-3xl text-sm leading-6 text-mist">
              Preferred setup uses ytmusicapi OAuth. Credentials stay in <code>backend/private/</code>, which is ignored by Git.
            </p>
          </div>
          <StatusPill ok={auth?.connected} label={auth?.connected ? "Connected" : "Not connected"} />
        </div>
        <div className="mt-5 grid gap-3 md:grid-cols-2">
          <Info label="Auth file" value={auth?.auth_file_path || "Unknown"} />
          <Info label="OAuth client configured" value={auth?.oauth_client_configured ? "Yes" : "No"} />
          <Info label="Account" value={auth?.account_name || "Unavailable"} />
          <Info label="Status" value={auth?.message || "Not checked yet"} />
        </div>
        <div className="mt-5 flex flex-wrap gap-3">
          <button className="btn-secondary" onClick={onCheckAuth}>Recheck Connection</button>
          <a className="btn-secondary" href="/docs/AUTH_SETUP.md" onClick={(event) => event.preventDefault()}>
            <ExternalLink size={17} /> See docs/AUTH_SETUP.md in the repo
          </a>
        </div>
        <div className="mt-5 rounded-lg border border-amber-300/20 bg-amber-300/10 p-4 text-sm leading-6 text-amber-100">
          Browser-header authentication is deliberately not automated. If you use it as an advanced fallback, treat the header file like account-access data and keep it out of Git.
        </div>
      </section>

      <section className="rounded-lg border border-line bg-panel/82 p-5">
        <div className="flex items-center justify-between gap-4">
          <div>
            <h2 className="text-xl font-semibold text-white">Use demo data</h2>
            <p className="mt-2 text-sm text-mist">Explore the whole dashboard with anonymised mock listening history.</p>
          </div>
          <label className="relative inline-flex cursor-pointer items-center">
            <input className="peer sr-only" type="checkbox" checked={useDemo} onChange={(event) => onUseDemoChange(event.target.checked)} />
            <span className="h-7 w-12 rounded-full bg-white/10 transition peer-checked:bg-violet" />
            <span className="absolute left-1 h-5 w-5 rounded-full bg-white transition peer-checked:translate-x-5" />
          </label>
        </div>
      </section>

      <section className="rounded-lg border border-line bg-panel/82 p-5">
        <h2 className="text-xl font-semibold text-white">Import Google Takeout history</h2>
        <p className="mt-2 max-w-3xl text-sm leading-6 text-mist">
          YouTube Music only exposed a short recent web history feed. Upload a Google Takeout YouTube watch-history JSON, HTML, or ZIP file to rebuild analysis with the longest account history Google provides.
        </p>
        <label className="mt-5 inline-flex cursor-pointer items-center gap-2 rounded-md border border-white/10 bg-white/[0.06] px-4 py-2.5 text-sm font-semibold text-white transition hover:border-violet/40 hover:bg-white/[0.09]">
          Choose Takeout file
          <input
            className="sr-only"
            disabled={busy}
            type="file"
            accept=".json,.zip,.html,.htm,application/json,application/zip,text/html"
            onChange={(event) => {
              const file = event.target.files?.[0];
              if (file) onImportTakeout(file);
              event.currentTarget.value = "";
            }}
          />
        </label>
      </section>

      <section className="rounded-lg border border-line bg-panel/82 p-5">
        <h2 className="flex items-center gap-2 text-xl font-semibold text-white">
          <ShieldCheck size={20} /> Local prerequisites
        </h2>
        <div className="mt-4 grid gap-3">
          {prerequisites?.items.map((item) => (
            <div key={item.name} className="flex flex-col justify-between gap-2 rounded-md bg-white/[0.04] p-4 sm:flex-row sm:items-center">
              <StatusPill ok={item.available} label={item.name} />
              <p className="text-sm text-mist">{item.detail}</p>
            </div>
          ))}
          <div className="rounded-md bg-white/[0.04] p-4 text-sm text-mist">
            Ollama model: <span className="text-white">{prerequisites?.ollama_model || "gemma3:4b"}</span>. Model installed:{" "}
            <span className="text-white">{prerequisites?.model_installed ? "Yes" : "No"}</span>.
          </div>
        </div>
      </section>
    </div>
  );
}

function Info({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-md bg-white/[0.04] p-4">
      <p className="text-xs uppercase tracking-[0.16em] text-mist/60">{label}</p>
      <p className="mt-2 break-words text-sm text-white">{value}</p>
    </div>
  );
}
