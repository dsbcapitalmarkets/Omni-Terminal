interface MetricCardProps {
  title: string;
  value: string | number;
  subtitle?: string;
  valueClassName?: string;
}

function MetricCard({
  title,
  value,
  subtitle,
  valueClassName = "text-slate-100",
}: MetricCardProps) {
  return (
    <div className="rounded-xl border border-slate-800 bg-[#0c1018] p-5">
      <div className="text-xs font-medium uppercase tracking-wider text-slate-500">
        {title}
      </div>

      <div
        className={`mt-3 text-2xl font-bold tracking-tight ${valueClassName}`}
      >
        {value}
      </div>

      {subtitle && (
        <div className="mt-1 text-xs text-slate-500">
          {subtitle}
        </div>
      )}
    </div>
  );
}

export default MetricCard;