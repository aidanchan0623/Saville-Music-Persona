import { Disc3, Music2, UserRound } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import "./Artwork.css";

export type ArtworkProps = {
  src?: string | null;
  sources?: Array<string | null | undefined>;
  alt: string;
  kind: "song" | "track" | "artist" | "album";
  size?: "sm" | "md" | "lg" | "hero";
  priority?: boolean;
  className?: string;
  fallbackLabel?: string;
  shape?: "rounded" | "circle";
  fit?: "cover" | "contain";
};

export function Artwork({ src, sources = [], alt, kind, size = "md", priority = false, className = "", fallbackLabel, shape, fit = "cover" }: ArtworkProps) {
  const candidates = artworkCandidates(src, sources);
  const candidatesKey = candidates.join("\n");
  const [candidateIndex, setCandidateIndex] = useState(0);
  const [loadedSrc, setLoadedSrc] = useState<string | null>(null);
  const previousCandidatesRef = useRef(candidatesKey);
  const usableSrc = candidates[candidateIndex] ?? null;
  const loading = Boolean(usableSrc && loadedSrc !== usableSrc);
  const Icon = kind === "artist" ? UserRound : kind === "album" ? Disc3 : Music2;
  const resolvedShape = shape ?? (kind === "artist" ? "circle" : "rounded");

  useEffect(() => {
    if (previousCandidatesRef.current === candidatesKey) return;
    previousCandidatesRef.current = candidatesKey;
    setCandidateIndex(0);
    setLoadedSrc(null);
  }, [candidatesKey]);

  return (
    <div
      className={`artwork-frame artwork-frame--${kind} artwork-frame--${size} artwork-frame--${resolvedShape} artwork-frame--fit-${fit}${className ? ` ${className}` : ""}`}
    >
      {usableSrc ? (
        <>
          {loading ? <div className="artwork-frame__skeleton" aria-hidden="true" /> : null}
          <img
            src={usableSrc}
            alt={alt}
            loading={priority ? "eager" : "lazy"}
            decoding="async"
            data-loaded={loading ? "false" : "true"}
            onLoad={() => {
              setLoadedSrc(usableSrc);
            }}
            onError={() => {
              setCandidateIndex((index) => index + 1);
              setLoadedSrc(null);
            }}
          />
        </>
      ) : (
        <div className="artwork-frame__fallback" aria-label={alt}>
          {fallbackLabel ? <span>{fallbackLabel}</span> : <Icon size={size === "hero" ? 38 : 22} />}
        </div>
      )}
    </div>
  );
}

type StrictArtworkProps = {
  className?: string;
  size?: ArtworkProps["size"];
  priority?: boolean;
  fit?: ArtworkProps["fit"];
};

export function ArtistAvatar({
  artistImageUrl,
  artistName,
  fallbackLabel,
  shape = "circle",
  ...props
}: StrictArtworkProps & {
  artistImageUrl?: string | null;
  artistName: string;
  fallbackLabel?: string;
  shape?: "circle" | "rounded";
}) {
  return (
    <Artwork
      src={artistImageUrl}
      alt={`${artistName} artist profile image`}
      kind="artist"
      fallbackLabel={fallbackLabel ?? initials(artistName)}
      shape={shape}
      {...props}
    />
  );
}

export function TrackArtwork({
  trackImageUrl,
  albumArtUrl,
  title,
  fallbackLabel,
  ...props
}: StrictArtworkProps & {
  trackImageUrl?: string | null;
  albumArtUrl?: string | null;
  title: string;
  fallbackLabel?: string;
}) {
  // A track thumbnail is often a widescreen video still. Prefer the resolved
  // album cover so song cards retain the same square, cover-art treatment as
  // album and artist cards, then fall back to the video thumbnail if needed.
  return <Artwork sources={[albumArtUrl, trackImageUrl]} alt={`${title} track artwork`} kind="track" fallbackLabel={fallbackLabel} shape="rounded" {...props} />;
}

export function AlbumCover({
  albumImageUrl,
  albumTitle,
  fallbackImageUrl,
  fallbackLabel,
  ...props
}: StrictArtworkProps & {
  albumImageUrl?: string | null;
  fallbackImageUrl?: string | null;
  albumTitle: string;
  fallbackLabel?: string;
}) {
  return <Artwork sources={[albumImageUrl, fallbackImageUrl]} alt={`${albumTitle} album cover`} kind="album" fallbackLabel={fallbackLabel ?? initials(albumTitle)} shape="rounded" {...props} />;
}

export type PersonaBackgroundImage = {
  src: string;
  alt?: string;
  position?: string;
};

export function PersonaBackground({
  image,
  priority = false,
  className = "",
}: {
  image?: PersonaBackgroundImage | null;
  priority?: boolean;
  className?: string;
}) {
  const [failed, setFailed] = useState(false);
  useEffect(() => setFailed(false), [image?.src]);

  if (!image?.src || failed) return null;

  return (
    <img
      className={`persona-background${className ? ` ${className}` : ""}`}
      src={image.src}
      alt={image.alt ?? ""}
      loading={priority ? "eager" : "lazy"}
      fetchPriority={priority ? "high" : "auto"}
      decoding="async"
      style={{ objectPosition: image.position ?? "center" }}
      onError={() => setFailed(true)}
    />
  );
}

function initials(value: string) {
  const parts = value.split(/\s+/).filter(Boolean);
  return `${parts[0]?.[0] ?? "?"}${parts[1]?.[0] ?? ""}`.toUpperCase();
}

function artworkCandidates(primary: string | null | undefined, alternatives: Array<string | null | undefined>) {
  return Array.from(new Set([primary, ...alternatives].map((value) => String(value ?? "").trim()).filter(Boolean)));
}
