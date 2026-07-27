import { Disc3, Music2, UserRound } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import "./Artwork.css";

export type ArtworkProps = {
  src?: string | null;
  alt: string;
  kind: "song" | "track" | "artist" | "album";
  size?: "sm" | "md" | "lg" | "hero";
  priority?: boolean;
  className?: string;
  fallbackLabel?: string;
  shape?: "rounded" | "circle";
  fit?: "cover" | "contain";
};

export function Artwork({ src, alt, kind, size = "md", priority = false, className = "", fallbackLabel, shape, fit = "cover" }: ArtworkProps) {
  const [failedSrc, setFailedSrc] = useState<string | null>(null);
  const [loadedSrc, setLoadedSrc] = useState<string | null>(null);
  const [naturalRatio, setNaturalRatio] = useState<number | null>(() => initialArtworkRatio(src, kind));
  const previousSrcRef = useRef(src);
  const usableSrc = src && src !== failedSrc ? src : null;
  const loading = Boolean(usableSrc && loadedSrc !== usableSrc);
  const Icon = kind === "artist" ? UserRound : kind === "album" ? Disc3 : Music2;
  const resolvedShape = shape ?? (kind === "artist" ? "circle" : "rounded");

  useEffect(() => {
    if (previousSrcRef.current === src) return;
    previousSrcRef.current = src;
    setFailedSrc(null);
    setLoadedSrc(null);
    setNaturalRatio(initialArtworkRatio(src, kind));
  }, [src, kind]);

  return (
    <div
      className={`artwork-frame artwork-frame--${kind} artwork-frame--${size} artwork-frame--${resolvedShape} artwork-frame--fit-${fit}${className ? ` ${className}` : ""}`}
      style={naturalRatio ? { aspectRatio: naturalRatio } : undefined}
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
            onLoad={(event) => {
              setLoadedSrc(usableSrc);
              if (kind === "track" && event.currentTarget.naturalWidth && event.currentTarget.naturalHeight) {
                setNaturalRatio(event.currentTarget.naturalWidth / event.currentTarget.naturalHeight);
              }
            }}
            onError={() => {
              setFailedSrc(usableSrc);
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
  return <Artwork src={albumArtUrl ?? trackImageUrl ?? null} alt={`${title} track artwork`} kind="track" fallbackLabel={fallbackLabel} shape="rounded" {...props} />;
}

export function AlbumCover({
  albumImageUrl,
  albumTitle,
  fallbackLabel,
  ...props
}: StrictArtworkProps & {
  albumImageUrl?: string | null;
  albumTitle: string;
  fallbackLabel?: string;
}) {
  return <Artwork src={albumImageUrl ?? null} alt={`${albumTitle} album cover`} kind="album" fallbackLabel={fallbackLabel ?? initials(albumTitle)} shape="rounded" {...props} />;
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

function initialArtworkRatio(_src: string | null | undefined, _kind: ArtworkProps["kind"]) {
  return null;
}
