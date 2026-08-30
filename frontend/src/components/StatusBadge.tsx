interface StatusBadgeProps {
  children: React.ReactNode;
  type?: "positive" | "negative" | "warning" | "neutral";
}

function StatusBadge({
  children,
  type = "neutral",
}: StatusBadgeProps) {
  const styles = {
    positive:
      "border-emerald-500/20 bg-emerald-500/10 text-emerald-400",

    negative:
      "border-red-500/20 bg-red-500/10 text-red-400",

    warning:
      "border-amber-500/20 bg-amber-500/10 text-amber-400",

    neutral:
      "border-slate-700 bg-slate-800/50 text-slate-400",
  };

  return (
    <span
      className={`inline-flex items-center rounded-md border px-2.5 py-1 text-xs font-medium ${styles[type]}`}
    >
      {children}
    </span>
  );
}

export default StatusBadge;