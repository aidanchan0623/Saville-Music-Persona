import { useEffect, useState } from "react";

interface ArtworkProps {
  src?: string | null;
  alt: string;
  className?: string;
  rounded?: "square" | "soft" | "circle";
}

export function Artwork({ src, alt, className = "", rounded = "soft" }: ArtworkProps) {
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    setFailed(false);
  }, [src]);

  const roundedClass = rounded === "circle" ? "rounded-full" : rounded === "square" ? "rounded-none" : "rounded-lg";

  return (
    <div className={`relative grid shrink-0 place-items-center overflow-hidden border border-white/10 bg-[#160707] ${roundedClass} ${className}`}>
      {src && !failed ? (
        <img className="h-full w-full object-cover object-center" src={src} alt={alt} loading="lazy" onError={() => setFailed(true)} />
      ) : (
        <span className="px-2 text-center font-display text-lg uppercase tracking-[0.08em] text-red-100/80">{initials(alt)}</span>
      )}
    </div>
  );
}

function initials(value: string) {
  return (
    value
      .split(/\s+/)
      .filter(Boolean)
      .slice(0, 2)
      .map((part) => part[0]?.toUpperCase())
      .join("") || "SM"
  );
}
