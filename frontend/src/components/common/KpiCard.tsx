import type { LucideIcon } from "lucide-react";

interface KpiCardProps {
  title: string;
  value: string;
  subtitle?: string;
  icon: LucideIcon;
  accentClass?: string;
  onClick?: () => void;
}

export function KpiCard({
  title,
  value,
  subtitle,
  icon: Icon,
  accentClass = "text-[#38BDF8]",
  onClick,
}: KpiCardProps) {
  const interactive = onClick
    ? "cursor-pointer hover:border-[#38BDF8]/60 transition-colors"
    : "";

  return (
    <div
      onClick={onClick}
      className={`rounded-xl border border-[#263244] bg-[#151E2E] p-4 ${interactive}`}
    >
      <div className="flex items-start justify-between gap-2">
        <span className="text-xs font-medium uppercase tracking-wider text-[#94A3B8]">
          {title}
        </span>
        <Icon className={`h-4 w-4 shrink-0 ${accentClass}`} />
      </div>
      <div className="mt-2 text-2xl font-semibold tracking-tight text-[#E2E8F0]">
        {value}
      </div>
      {subtitle && <p className="mt-1 text-xs text-[#94A3B8]">{subtitle}</p>}
    </div>
  );
}

