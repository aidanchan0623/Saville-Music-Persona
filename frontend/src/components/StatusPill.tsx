import { AlertTriangle, CheckCircle2, Circle } from "lucide-react";

interface Props {
  ok?: boolean;
  label: string;
  muted?: boolean;
}

export function StatusPill({ ok, label, muted }: Props) {
  const Icon = muted ? Circle : ok ? CheckCircle2 : AlertTriangle;
  const className = muted
    ? "border-white/10 bg-white/5 text-mist"
    : ok
      ? "border-emerald-400/25 bg-emerald-400/10 text-emerald-200"
      : "border-amber-300/25 bg-amber-300/10 text-amber-100";
  return (
    <span className={`inline-flex items-center gap-2 rounded-full border px-3 py-1 text-xs font-medium ${className}`}>
      <Icon size={14} />
      {label}
    </span>
  );
}

