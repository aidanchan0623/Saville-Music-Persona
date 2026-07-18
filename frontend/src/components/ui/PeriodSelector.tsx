export type PeriodValue = "this_month" | "last_7" | "last_30" | "month" | "rolling_year" | "all";

export interface PeriodOption {
  value: PeriodValue;
  label: string;
  shortLabel?: string;
}

interface PeriodSelectorProps {
  value: PeriodValue;
  onChange: (value: PeriodValue) => void;
  month: string | null;
  months: { value: string; label: string }[];
  onMonthChange: (value: string) => void;
  options?: PeriodOption[];
}

export const standardPeriodOptions: PeriodOption[] = [
  { value: "this_month", label: "This Month" },
  { value: "last_7", label: "Last 7" },
  { value: "last_30", label: "Last 30" },
  { value: "month", label: "Select Month", shortLabel: "Month" },
  { value: "rolling_year", label: "Rolling Year", shortLabel: "Year" },
  { value: "all", label: "All History", shortLabel: "All" },
];

export function PeriodSelector({ value, onChange, month, months, onMonthChange, options = standardPeriodOptions }: PeriodSelectorProps) {
  return (
    <div className="flex flex-wrap items-center gap-2 rounded-lg border border-white/10 bg-white/[0.035] p-1.5">
      {options.map((option) => (
        <button
          key={option.value}
          type="button"
          className={`rounded-md px-3 py-2 text-xs font-semibold uppercase tracking-[0.08em] transition focus:outline-none focus-visible:ring-2 focus-visible:ring-red-400 md:text-sm ${
            value === option.value ? "bg-red-600 text-white shadow-[0_0_24px_rgba(220,38,38,0.28)]" : "text-mist hover:bg-white/[0.07] hover:text-white"
          }`}
          aria-pressed={value === option.value}
          onClick={() => onChange(option.value)}
        >
          <span className="hidden sm:inline">{option.label}</span>
          <span className="sm:hidden">{option.shortLabel ?? option.label}</span>
        </button>
      ))}
      {value === "month" ? (
        <select className="min-h-10 rounded-md border border-white/10 bg-[#090606] px-3 py-2 text-sm text-white focus:outline-none focus:ring-2 focus:ring-red-400" value={month ?? months.at(-1)?.value ?? ""} onChange={(event) => onMonthChange(event.target.value)}>
          {months.length ? months.map((item) => <option key={item.value} value={item.value}>{item.label}</option>) : <option value="">No months yet</option>}
        </select>
      ) : null}
    </div>
  );
}
