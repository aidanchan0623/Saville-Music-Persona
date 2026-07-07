export function formatDate(value: string | null | undefined): string {
  if (!value) return "Unavailable";
  return new Intl.DateTimeFormat(undefined, { year: "numeric", month: "short", day: "numeric" }).format(new Date(value));
}

export function formatDateTime(value: string | null | undefined): string {
  if (!value) return "Never";
  return new Intl.DateTimeFormat(undefined, {
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  }).format(new Date(value));
}

export function asPercent(value: number): string {
  return `${Math.round(value)}%`;
}

export function formatMinutes(value: number | null | undefined): string {
  const total = Math.max(0, Math.round(value ?? 0));
  const hours = Math.floor(total / 60);
  const minutes = total % 60;
  if (hours <= 0) return `${minutes} minutes`;
  return `${hours.toLocaleString()} hr ${String(minutes).padStart(2, "0")} min`;
}
