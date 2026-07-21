import { Music2, UserRound } from "lucide-react";
import { useEffect, useState } from "react";
import "./Artwork.css";

export type ArtworkProps = {
  src?: string | null;
  alt: string;
  kind: "song" | "artist";
  size?: "sm" | "md" | "lg" | "hero";
  priority?: boolean;
  className?: string;
  fallbackLabel?: string;
  shape?: "rounded" | "circle";
};

export function Artwork({ src, alt, kind, size = "md", priority = false, className = "", fallbackLabel, shape }: ArtworkProps) {
  const [failedSrc, setFailedSrc] = useState<string | null>(null);
  const [loadedSrc, setLoadedSrc] = useState<string | null>(null);
  const usableSrc = src && src !== failedSrc ? src : null;
  const loading = Boolean(usableSrc && loadedSrc !== usableSrc);
  const Icon = kind === "artist" ? UserRound : Music2;
  const resolvedShape = shape ?? (kind === "artist" ? "circle" : "rounded");

  useEffect(() => {
    setFailedSrc(null);
    setLoadedSrc(null);
  }, [src]);

  return (
    <div className={`artwork-frame artwork-frame--${kind} artwork-frame--${size} artwork-frame--${resolvedShape}${className ? ` ${className}` : ""}`}>
      {usableSrc ? (
        <>
          {loading ? <div className="artwork-frame__skeleton" aria-hidden="true" /> : null}
          <img
            src={usableSrc}
            alt={alt}
            loading={priority ? "eager" : "lazy"}
            decoding="async"
            data-loaded={loading ? "false" : "true"}
            onLoad={() => setLoadedSrc(usableSrc)}
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
