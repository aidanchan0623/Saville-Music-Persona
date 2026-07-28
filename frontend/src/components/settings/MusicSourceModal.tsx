import { useEffect, useRef } from "react";
import { ExternalLink, Upload } from "lucide-react";

interface Props {
  open: boolean;
  onClose: () => void;
  onConnectSpotify: () => void;
  onImportTakeout: (file: File) => Promise<boolean>;
  busy: boolean;
  message: string | null;
  spotifyConfigured: boolean;
}

const focusable = 'button:not([disabled]), [href], input:not([disabled])';

export function MusicSourceModal({ open, onClose, onConnectSpotify, onImportTakeout, busy, message, spotifyConfigured }: Props) {
  const dialogRef = useRef<HTMLDivElement>(null);
  const triggerRef = useRef<HTMLElement | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (!open) return;
    triggerRef.current = document.activeElement instanceof HTMLElement ? document.activeElement : null;
    const first = dialogRef.current?.querySelector<HTMLElement>(focusable);
    first?.focus();
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") onClose();
      if (event.key !== "Tab") return;
      const items = [...(dialogRef.current?.querySelectorAll<HTMLElement>(focusable) ?? [])];
      if (!items.length) return;
      const current = document.activeElement;
      const index = items.indexOf(current as HTMLElement);
      if (event.shiftKey && (index <= 0)) { event.preventDefault(); items.at(-1)?.focus(); }
      else if (!event.shiftKey && index === items.length - 1) { event.preventDefault(); items[0]?.focus(); }
    };
    document.addEventListener("keydown", onKeyDown);
    return () => { document.removeEventListener("keydown", onKeyDown); triggerRef.current?.focus(); };
  }, [open, onClose]);

  if (!open) return null;
  const openExternal = (url: string) => window.open(url, "_blank", "noopener,noreferrer");
  const upload = async (file: File | undefined) => { if (file && await onImportTakeout(file)) onClose(); };
  return (
    <div className="fixed inset-0 z-50 grid place-items-center overflow-y-auto bg-black/75 p-4" role="presentation" onMouseDown={(event) => { if (event.target === event.currentTarget) onClose(); }}>
      <div ref={dialogRef} role="dialog" aria-modal="true" aria-labelledby="music-source-title" className="w-full max-w-4xl rounded-xl border border-red-500/25 bg-[#101012] p-5 shadow-2xl md:p-7">
        <div className="flex items-start justify-between gap-4"><div><p className="text-xs font-semibold uppercase tracking-[.18em] text-red-200">Music data</p><h2 id="music-source-title" className="mt-2 text-2xl font-black text-white">Choose music service</h2><p className="mt-2 text-sm leading-6 text-mist">Connect a streaming service or import listening data. Authentication stays local to this device.</p></div><button className="btn-secondary" onClick={onClose} aria-label="Close music source dialog">Close</button></div>
        <div className="mt-6 grid gap-4 md:grid-cols-2">
          <section className="rounded-lg border border-white/10 bg-black/25 p-5"><h3 className="text-xl font-black text-white">YouTube Music</h3><p className="mt-2 text-sm leading-6 text-mist">A local connection can provide recent or partial listening data. For a longer dated history, Google Takeout is recommended.</p><button type="button" className="btn-secondary mt-4" onClick={() => openExternal("https://takeout.google.com/settings/takeout")}><ExternalLink size={16}/> Open Google Takeout</button><p className="mt-4 text-sm leading-6 text-mist">Google prepares exports outside Saville: sign in, select YouTube and YouTube Music, request the export, wait, download it, then return here to upload a ZIP, JSON, or HTML file.</p><label className="btn-primary mt-4 inline-flex cursor-pointer"><Upload size={16}/> Upload Takeout File<input ref={inputRef} className="sr-only" disabled={busy} type="file" accept=".json,.zip,.html,.htm,application/json,application/zip,text/html" onChange={(event) => { void upload(event.target.files?.[0]); event.currentTarget.value = ""; }} /></label></section>
          <section className="rounded-lg border border-white/10 bg-black/25 p-5"><h3 className="text-xl font-black text-white">Spotify</h3><p className="mt-2 text-sm leading-6 text-mist">Connect to use top tracks and artists, saved songs, playlists, recent plays, and locally accumulated sync data. OAuth does not provide complete lifetime play history.</p><button type="button" className="btn-primary mt-4" disabled={busy || !spotifyConfigured} onClick={onConnectSpotify}>Connect Spotify</button><button type="button" className="btn-secondary mt-3" onClick={() => openExternal("https://www.spotify.com/account/privacy/")}><ExternalLink size={16}/> Open Spotify Data Download</button><p className="mt-4 text-sm leading-6 text-mist">Spotify historical file import is not supported yet. Request the export in Spotify, then keep the files private; adding a safe importer requires a dedicated parser and source-aware deduplication.</p></section>
        </div>
        {message ? <p className="mt-5 rounded border border-white/10 bg-black/30 p-3 text-sm text-mist" role="status">{message}</p> : null}
      </div>
    </div>
  );
}
