interface PanelProps {
  title: string;
  description?: string;
  children: React.ReactNode;
  className?: string;
}

function Panel({
  title,
  description,
  children,
  className = "",
}: PanelProps) {
  return (
    <section
      className={`rounded-xl border border-slate-800 bg-[#0c1018] p-5 ${className}`}
    >
      <div className="mb-5">
        <h3 className="font-semibold text-slate-100">
          {title}
        </h3>

        {description && (
          <p className="mt-1 text-xs text-slate-500">
            {description}
          </p>
        )}
      </div>

      {children}
    </section>
  );
}

export default Panel;