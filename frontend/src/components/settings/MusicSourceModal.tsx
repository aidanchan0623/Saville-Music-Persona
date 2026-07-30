import { useEffect, useRef } from "react";
import { ExternalLink, Upload } from "lucide-react";

interface Props {
  open: boolean;
  onClose: () => void;
  onConnectSpotify: () => void;
  onImportTakeout: (file: File) => Promise<boolean>;
  onImportSpotifyHistory: (file: File) => Promise<boolean>;
  busy: boolean;
  message: string | null;
  spotifyConfigured: boolean;
  accountConnectionsEnabled: boolean;
}

const focusable = 'button:not([disabled]), [href], input:not([disabled])';

export function MusicSourceModal({ open, onClose, onConnectSpotify, onImportTakeout, onImportSpotifyHistory, busy, message, spotifyConfigured, accountConnectionsEnabled }: Props) {
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
  const uploadSpotify = async (file: File | undefined) => { if (file && await onImportSpotifyHistory(file)) onClose(); };
  return (
    <div className="fixed inset-0 z-50 grid place-items-center overflow-y-auto bg-black/75 p-4" role="presentation" onMouseDown={(event) => { if (event.target === event.currentTarget) onClose(); }}>
      <div ref={dialogRef} role="dialog" aria-modal="true" aria-labelledby="music-source-title" className="w-full max-w-4xl rounded-xl border border-red-500/25 bg-[#101012] p-5 shadow-2xl md:p-7">
        <div className="flex items-start justify-between gap-4"><div><p className="text-xs font-semibold uppercase tracking-[.18em] text-red-200">Music data</p><h2 id="music-source-title" className="mt-2 text-2xl font-black text-white">Choose music service</h2><p className="mt-2 text-sm leading-6 text-mist">{accountConnectionsEnabled ? "Connect a streaming service or import listening data. Authentication stays local to this device." : "Upload an export without connecting an account. Data is isolated to this anonymous browser session."}</p></div><button className="btn-secondary" onClick={onClose} aria-label="Close music source dialog">Close</button></div>
        <div className="mt-6 grid gap-4 md:grid-cols-2">
          <section className="rounded-lg border border-white/10 bg-black/25 p-5"><h3 className="text-xl font-black text-white">YouTube Music</h3><p className="mt-2 text-sm leading-6 text-mist">Google Takeout provides the longest dated YouTube Music history.</p><button type="button" className="btn-secondary mt-4" onClick={() => openExternal("https://takeout.google.com/settings/takeout")}><ExternalLink size={16}/> Open Google Takeout</button><p className="mt-4 text-sm leading-6 text-mist">Google prepares exports outside Saville: sign in, select YouTube and YouTube Music, request the export, wait, download it, then return here to upload a ZIP, JSON, or HTML file.</p><label className="btn-primary mt-4 inline-flex cursor-pointer"><Upload size={16}/> Upload Takeout File<input ref={inputRef} className="sr-only" disabled={busy} type="file" accept=".json,.zip,.html,.htm,application/json,application/zip,text/html" onChange={(event) => { void upload(event.target.files?.[0]); event.currentTarget.value = ""; }} /></label></section>
          <section className="rounded-lg border border-white/10 bg-black/25 p-5"><h3 className="text-xl font-black text-white">Spotify</h3><p className="mt-2 text-sm leading-6 text-mist">Upload your Spotify extended streaming-history ZIP for dated plays.</p><div className="mt-4 flex flex-wrap gap-3"><label className="btn-primary inline-flex cursor-pointer"><Upload size={16}/> Upload Spotify Export<input className="sr-only" disabled={busy} type="file" accept=".json,.zip,application/json,application/zip" onChange={(event) => { void uploadSpotify(event.target.files?.[0]); event.currentTarget.value = ""; }} /></label>{accountConnectionsEnabled ? <button type="button" className="btn-secondary" disabled={busy || !spotifyConfigured} onClick={onConnectSpotify}>Connect Spotify</button> : null}</div><button type="button" className="btn-secondary mt-3" onClick={() => openExternal("https://www.spotify.com/account/privacy/")}><ExternalLink size={16}/> Open Spotify Data Download</button><p className="mt-4 text-sm leading-6 text-mist">Saville accepts the downloaded ZIP directly, reads only audio history JSON, excludes podcasts and audiobooks, and safely deduplicates overlapping export files.</p></section>
        </div>
        {message ? <p className="mt-5 rounded border border-white/10 bg-black/30 p-3 text-sm text-mist" role="status">{message}</p> : null}
      </div>
    </div>
  );
}
