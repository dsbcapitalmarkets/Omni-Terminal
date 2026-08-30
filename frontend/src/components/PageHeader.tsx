interface PageHeaderProps {
  section: string;
  title: string;
  description: string;
  updated?: string;
}

function PageHeader({
  section,
  title,
  description,
  updated,
}: PageHeaderProps) {
  return (
    <div className="mb-6">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <p className="mb-1 text-xs font-medium uppercase tracking-widest text-cyan-400">
            {section}
          </p>

          <h2 className="text-2xl font-bold tracking-tight sm:text-3xl">
            {title}
          </h2>

          <p className="mt-1 text-sm text-slate-500">
            {description}
          </p>
        </div>

        {updated && (
          <div className="text-right text-xs text-slate-500">
            <div>Last updated</div>

            <div className="mt-1 font-medium text-slate-300">
              {updated}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export default PageHeader;