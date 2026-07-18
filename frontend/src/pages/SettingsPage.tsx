import { ExternalLink, RefreshCw, ShieldCheck } from "lucide-react";
import type { ReactNode } from "react";
import { AnimatedPageTitle } from "../components/AnimatedPageTitle";
import { StatusPill } from "../components/StatusPill";
import type { AuthStatus, Prerequisites, SpotifyStatus } from "../types/api";

interface Props {
  auth: AuthStatus | null;
  prerequisites: Prerequisites | null;
  useDemo: boolean;
  busy: boolean;
  onUseDemoChange: (value: boolean) => void;
  onCheckAuth: () => void;
  onImportTakeout: (file: File) => void;
  spotifyStatus: SpotifyStatus | null;
  onConnectSpotify: () => void;
  onRefreshSpotify: () => void;
  onDisconnectSpotify: () => void;
  titleAnimationKey: string;
}

export function SettingsPage({
  auth,
  prerequisites,
  useDemo,
  busy,
  onUseDemoChange,
  onCheckAuth,
  onImportTakeout,
  spotifyStatus,
  onConnectSpotify,
  onRefreshSpotify,
  onDisconnectSpotify,
  titleAnimationKey,
}: Props) {
  return (
    <div className="space-y-6">
      <header className="overflow-hidden rounded-[1.25rem] border border-red-500/15 bg-[linear-gradient(135deg,rgba(33,8,8,0.96),rgba(5,5,5,0.99)_62%,rgba(16,8,8,0.98))] p-5 shadow-glow lg:p-6">
        <p className="text-xs font-semibold uppercase tracking-[0.2em] text-red-200">Settings</p>
        <AnimatedPageTitle animationKey={titleAnimationKey} text="Local integrations and data controls" className="mt-3 text-3xl font-black text-white md:text-4xl" />
        <p className="mt-3 max-w-3xl text-sm leading-6 text-mist">Connection status, demo mode, private auth guidance, and import tools for the local music profile.</p>
        <div className="mt-5 grid gap-3 md:grid-cols-3">
          <StatusSummary label="YouTube Music" value={auth?.connected ? "Connected" : auth?.cached_data_available ? "Cached data" : "Offline"} ok={Boolean(auth?.connected || auth?.cached_data_available)} />
          <StatusSummary label="Spotify" value={spotifyStatus?.connected ? "Connected" : spotifyStatus?.configured ? "Ready to connect" : "Not configured"} ok={Boolean(spotifyStatus?.connected)} />
          <StatusSummary label="Gemma" value={prerequisites?.model_installed ? "Ready" : "Offline"} ok={Boolean(prerequisites?.model_installed)} />
        </div>
      </header>

      <SettingsCard>
        <div className="flex flex-col justify-between gap-4 md:flex-row md:items-start">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-red-200">Primary source</p>
            <h2 className="mt-2 text-2xl font-black text-white">Connect YouTube Music</h2>
            <p className="mt-2 max-w-3xl text-sm leading-6 text-mist">
              Preferred setup uses ytmusicapi OAuth. Credentials stay in the backend's ignored private config folder.
            </p>
          </div>
          <StatusPill ok={auth?.connected || auth?.cached_data_available} label={auth?.connected ? "Connected" : auth?.cached_data_available ? "Cached data" : "Not connected"} />
        </div>
        <div className="mt-5 grid gap-3 md:grid-cols-2">
          <Info label="Auth storage" value={auth?.auth_file_exists ? "Configured locally" : "Not created yet"} />
          <Info label="OAuth client configured" value={auth?.oauth_client_configured ? "Yes" : "No"} />
          <Info label="Account" value={auth?.account_name || "Unavailable"} />
          <Info label="Cached YouTube profile" value={auth?.cached_data_available ? `Available${auth.last_refreshed_at ? `, refreshed ${auth.last_refreshed_at}` : ""}` : "Unavailable"} />
          <Info label="Status" value={sanitizePrivateDetails(auth?.message || "Not checked yet")} />
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
      </SettingsCard>

      <SettingsCard>
        <div className="flex flex-col justify-between gap-4 md:flex-row md:items-start">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-red-200">Optional source</p>
            <h2 className="mt-2 text-2xl font-black text-white">Connect Spotify</h2>
            <p className="mt-2 max-w-3xl text-sm leading-6 text-mist">
              Spotify is optional. It stays separate from YouTube Music and uses top artists, top tracks, saved songs, playlists, and recent plays.
            </p>
          </div>
          <StatusPill ok={spotifyStatus?.connected} label={spotifyStatus?.connected ? "Connected" : "Optional"} />
        </div>
        <div className="mt-5 grid gap-3 md:grid-cols-2">
          <div className="rounded-md bg-white/[0.04] p-4">
            <p className="text-xs uppercase tracking-[0.16em] text-mist/60">Account</p>
            <div className="mt-3 flex items-center gap-3">
              {spotifyStatus?.profile_image ? (
                <img className="h-11 w-11 rounded-full object-cover" src={spotifyStatus.profile_image} alt={spotifyStatus.display_name ?? "Spotify profile"} />
              ) : (
                <span className="grid h-11 w-11 place-items-center rounded-full bg-white/10 text-sm font-bold text-white">SP</span>
              )}
              <p className="text-sm text-white">{spotifyStatus?.display_name || "Not connected"}</p>
            </div>
          </div>
          <Info label="Spotify configured" value={spotifyStatus?.configured ? "Yes" : "No"} />
          <Info label="Last Spotify sync" value={spotifyStatus?.last_synced_at || "Never"} />
          <Info label="Status" value={sanitizePrivateDetails(spotifyStatus?.message || "Not checked yet")} />
        </div>
        <div className="mt-5 flex flex-wrap gap-3">
          {!spotifyStatus?.connected ? (
            <button className="btn-primary" disabled={busy || !spotifyStatus?.configured} onClick={onConnectSpotify}>
              Connect Spotify
            </button>
          ) : (
            <>
              <button className="btn-secondary" disabled={busy} onClick={onRefreshSpotify}>
                <RefreshCw size={16} /> Refresh Spotify Data
              </button>
              <button className="btn-secondary" disabled={busy} onClick={onDisconnectSpotify}>
                Disconnect Spotify
              </button>
            </>
          )}
        </div>
        <div className="mt-5 rounded-lg border border-white/10 bg-white/[0.04] p-4 text-sm leading-6 text-mist">
          Spotify does not provide Google Takeout-style full historical play counts. Initial Spotify profiles are based on top items, saved music, playlists, and recent sync data; monthly history improves after repeated syncs.
        </div>
      </SettingsCard>

      <SettingsCard>
        <div className="flex items-center justify-between gap-4">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-red-200">Preview mode</p>
            <h2 className="mt-2 text-2xl font-black text-white">Use demo data</h2>
            <p className="mt-2 text-sm text-mist">Explore the whole dashboard with anonymised mock listening history.</p>
          </div>
          <label className="relative inline-flex cursor-pointer items-center">
            <input className="peer sr-only" type="checkbox" checked={useDemo} onChange={(event) => onUseDemoChange(event.target.checked)} />
            <span className="h-7 w-12 rounded-full bg-white/10 transition peer-checked:bg-red-600" />
            <span className="absolute left-1 h-5 w-5 rounded-full bg-white transition peer-checked:translate-x-5" />
          </label>
        </div>
      </SettingsCard>

      <SettingsCard>
        <p className="text-xs font-semibold uppercase tracking-[0.18em] text-red-200">Analysis rules</p>
        <h2 className="mt-2 text-2xl font-black text-white">Analytics timezone and duration enrichment</h2>
        <p className="mt-2 max-w-3xl text-sm leading-6 text-mist">
          Calendar months, daily charts and streaks use the backend local timezone. Change <code>SMP_LOCAL_TIMEZONE</code> in the backend environment to adjust it.
        </p>
        <div className="mt-5 grid gap-3 md:grid-cols-2">
          <Info label="Analytics timezone" value={prerequisites?.local_timezone || "Asia/Kuala_Lumpur"} />
          <Info label="Duration enrichment limit" value={`${prerequisites?.duration_enrichment_limit ?? 150} missing tracks per refresh/import`} />
        </div>
      </SettingsCard>

      <SettingsCard>
        <p className="text-xs font-semibold uppercase tracking-[0.18em] text-red-200">Long history import</p>
        <h2 className="mt-2 text-2xl font-black text-white">Import Google Takeout history</h2>
        <p className="mt-2 max-w-3xl text-sm leading-6 text-mist">
          YouTube Music only exposed a short recent web history feed. Upload a Google Takeout YouTube watch-history JSON, HTML, or ZIP file to rebuild analysis with the longest account history Google provides.
        </p>
        <label className="mt-5 inline-flex cursor-pointer items-center gap-2 rounded-md border border-white/10 bg-white/[0.06] px-4 py-2.5 text-sm font-semibold text-white transition hover:border-red-500/40 hover:bg-white/[0.09]">
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
      </SettingsCard>

      <SettingsCard>
        <p className="text-xs font-semibold uppercase tracking-[0.18em] text-red-200">Local runtime</p>
        <h2 className="mt-2 flex items-center gap-2 text-2xl font-black text-white">
          <ShieldCheck size={20} /> Local prerequisites
        </h2>
        <div className="mt-4 grid gap-3">
          {prerequisites?.items.map((item) => (
            <div key={item.name} className="flex flex-col justify-between gap-2 rounded-md bg-white/[0.04] p-4 sm:flex-row sm:items-center">
              <StatusPill ok={item.available} label={item.name} />
              <p className="text-sm text-mist">{sanitizePrivateDetails(item.detail)}</p>
            </div>
          ))}
          <div className="rounded-md bg-white/[0.04] p-4 text-sm text-mist">
            Ollama model: <span className="text-white">{prerequisites?.ollama_model || "gemma3:4b"}</span>. Model installed:{" "}
            <span className="text-white">{prerequisites?.model_installed ? "Yes" : "No"}</span>.
          </div>
        </div>
      </SettingsCard>
    </div>
  );
}

function SettingsCard({ children }: { children: ReactNode }) {
  return (
    <section className="rounded-[1.25rem] border border-line bg-panel/78 p-5 shadow-[0_18px_70px_rgba(0,0,0,0.18)]">
      {children}
    </section>
  );
}

function StatusSummary({ label, value, ok }: { label: string; value: string; ok: boolean }) {
  return (
    <div className="rounded-xl border border-white/10 bg-black/25 p-4">
      <p className="text-xs font-semibold uppercase tracking-[0.16em] text-mist/60">{label}</p>
      <p className={`mt-2 text-sm font-semibold ${ok ? "text-red-100" : "text-mist"}`}>{value}</p>
    </div>
  );
}

function Info({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg border border-white/10 bg-black/20 p-4">
      <p className="text-xs uppercase tracking-[0.16em] text-mist/60">{label}</p>
      <p className="mt-2 break-words text-sm text-white">{value}</p>
    </div>
  );
}

function sanitizePrivateDetails(value: string) {
  return value
    .replace(/[A-Za-z]:\\[^\s]+/g, "[local private path]")
    .replace(/backend[\\/]+private[\\/]+\.env/g, "local private settings")
    .replace(/backend[\\/]+private[\\/]?/g, "local private storage");
}
