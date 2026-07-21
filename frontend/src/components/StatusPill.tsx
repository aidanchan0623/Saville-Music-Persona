import { AlertTriangle, CheckCircle2, Circle } from "lucide-react";

interface Props {
  ok?: boolean;
  label: string;
  muted?: boolean;
}

export function StatusPill({ ok, label, muted }: Props) {
  const Icon = muted ? Circle : ok ? CheckCircle2 : AlertTriangle;
  const className = muted
    ? "text-mist"
    : ok
      ? "text-emerald-200"
      : "text-amber-100";
  return (
    <span className={`inline-flex items-center gap-2 text-xs font-medium ${className}`}>
      <Icon size={14} />
      {label}
    </span>
  );
}
