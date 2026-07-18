export function LoadingSkeleton({ lines = 3 }: { lines?: number }) {
  return (
    <div className="space-y-3" aria-hidden="true">
      {Array.from({ length: lines }, (_, index) => (
        <div key={index} className="h-4 animate-pulse rounded-full bg-white/[0.07]" style={{ width: `${92 - index * 16}%` }} />
      ))}
    </div>
  );
}
