import {
  ArrowDown,
  ArrowUp,
  ChevronUp,
  Minus,
  TrendingDown,
  TrendingUp,
} from "lucide-react";

interface Sector {
  rank: number;
  sector: string;
  rs: number;
  mom: number;
  signal: string;
  score: number;
  rank_change: number;
}

interface SectorRotationData {
  timestamp: string;
  run_mode: string;
  title_suffix: string;
  sectors: Sector[];
  leaders: string[];
  laggards: string[];
  status: string;
}

const sectorData: SectorRotationData = {
  timestamp: "29 Aug 2026, 06:17 PM IST",
  run_mode: "DAILY",
  title_suffix: "(1M / 1W)",
  sectors: [
    {
      rank: 1,
      sector: "PHARMA",
      rs: 2.87,
      mom: 2.23,
      signal: "Strong Uptrend 🚀",
      score: 5.1,
      rank_change: 0,
    },
    {
      rank: 2,
      sector: "BANK",
      rs: 1.58,
      mom: 0.61,
      signal: "Moderate Uptrend 📈",
      score: 2.19,
      rank_change: 0,
    },
    {
      rank: 3,
      sector: "IT",
      rs: -2.21,
      mom: -0.9,
      signal: "Neutral ⚖️",
      score: -3.11,
      rank_change: 0,
    },
  ],
  leaders: ["PHARMA", "BANK"],
  laggards: ["BANK", "IT"],
  status: "ok",
};

function getSignalClass(signal: string) {
  if (signal.includes("Strong Uptrend")) {
    return "text-emerald-400";
  }

  if (signal.includes("Moderate Uptrend")) {
    return "text-cyan-400";
  }

  if (signal.includes("Downtrend")) {
    return "text-red-400";
  }

  return "text-slate-400";
}

function RankChange({ value }: { value: number }) {
  if (value > 0) {
    return (
      <span className="flex items-center gap-1 text-emerald-400">
        <ArrowUp size={14} />
        {value}
      </span>
    );
  }

  if (value < 0) {
    return (
      <span className="flex items-center gap-1 text-red-400">
        <ArrowDown size={14} />
        {Math.abs(value)}
      </span>
    );
  }

  return (
    <span className="flex items-center gap-1 text-slate-500">
      <Minus size={14} />
      —
    </span>
  );
}

function SectorRotation() {
  const data = sectorData;

  if (data.status !== "ok") {
    return (
      <div>
        <p className="text-sm text-red-400">
          Unable to load sector rotation data.
        </p>
      </div>
    );
  }

  const strongest = data.sectors[0];
  const weakest = data.sectors[data.sectors.length - 1];

  return (
    <div className="space-y-6">
      {/* Page heading */}
      <div>
        <p className="mb-1 text-xs font-medium uppercase tracking-widest text-cyan-400">
          Analytics
        </p>

        <div className="flex flex-col justify-between gap-3 md:flex-row md:items-end">
          <div>
            <h2 className="text-3xl font-bold tracking-tight">
              Sector Rotation
            </h2>

            <p className="mt-2 text-sm text-slate-500">
              Relative strength and momentum across NSE sectors
            </p>
          </div>

          <div className="text-left text-xs text-slate-500 md:text-right">
            <div>
              {data.run_mode} {data.title_suffix}
            </div>

            <div className="mt-1 text-slate-300">
              {data.timestamp}
            </div>
          </div>
        </div>
      </div>

      {/* Summary cards */}
      <div className="grid gap-4 md:grid-cols-3">
        {/* Leading */}
        <div className="rounded-xl border border-slate-800 bg-[#0c1018] p-5">
          <div className="flex items-center gap-2 text-xs font-medium uppercase tracking-wider text-slate-500">
            <TrendingUp size={15} />
            Leading Sector
          </div>

          <div className="mt-3 text-2xl font-bold text-emerald-400">
            {strongest?.sector ?? "—"}
          </div>

          <div className="mt-1 text-xs text-slate-500">
            RS {strongest?.rs >= 0 ? "+" : ""}
            {strongest?.rs.toFixed(2)}% · MOM{" "}
            {strongest?.mom >= 0 ? "+" : ""}
            {strongest?.mom.toFixed(2)}%
          </div>
        </div>

        {/* Weakest */}
        <div className="rounded-xl border border-slate-800 bg-[#0c1018] p-5">
          <div className="flex items-center gap-2 text-xs font-medium uppercase tracking-wider text-slate-500">
            <TrendingDown size={15} />
            Weakest Sector
          </div>

          <div className="mt-3 text-2xl font-bold text-red-400">
            {weakest?.sector ?? "—"}
          </div>

          <div className="mt-1 text-xs text-slate-500">
            RS {weakest?.rs >= 0 ? "+" : ""}
            {weakest?.rs.toFixed(2)}% · MOM{" "}
            {weakest?.mom >= 0 ? "+" : ""}
            {weakest?.mom.toFixed(2)}%
          </div>
        </div>

        {/* Analysis mode */}
        <div className="rounded-xl border border-slate-800 bg-[#0c1018] p-5">
          <div className="text-xs font-medium uppercase tracking-wider text-slate-500">
            Analysis Mode
          </div>

          <div className="mt-3 text-2xl font-bold">
            {data.run_mode}
          </div>

          <div className="mt-1 text-xs text-slate-500">
            {data.title_suffix}
          </div>
        </div>
      </div>

      {/* Leaders / Laggards */}
      <div className="grid gap-4 md:grid-cols-2">
        <div className="rounded-xl border border-emerald-500/20 bg-[#0c1018] p-5">
          <div className="text-xs font-medium uppercase tracking-wider text-slate-500">
            Leading
          </div>

          <div className="mt-3 flex flex-wrap gap-2">
            {data.leaders.map((sector) => (
              <span
                key={sector}
                className="rounded-lg border border-emerald-500/20 bg-emerald-500/10 px-3 py-1.5 text-sm font-medium text-emerald-400"
              >
                {sector}
              </span>
            ))}
          </div>
        </div>

        <div className="rounded-xl border border-red-500/20 bg-[#0c1018] p-5">
          <div className="text-xs font-medium uppercase tracking-wider text-slate-500">
            Laggards
          </div>

          <div className="mt-3 flex flex-wrap gap-2">
            {data.laggards.map((sector) => (
              <span
                key={sector}
                className="rounded-lg border border-red-500/20 bg-red-500/10 px-3 py-1.5 text-sm font-medium text-red-400"
              >
                {sector}
              </span>
            ))}
          </div>
        </div>
      </div>

      {/* Sector Rankings */}
      <div className="rounded-xl border border-slate-800 bg-[#0c1018]">
        <div className="flex items-center justify-between border-b border-slate-800 px-5 py-4">
          <div>
            <h3 className="font-semibold">
              Sector Rankings
            </h3>

            <p className="mt-1 text-xs text-slate-500">
              Relative strength and momentum ranking
            </p>
          </div>

          <div className="text-xs text-slate-500">
            {data.sectors.length} sectors
          </div>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full min-w-[760px] text-sm">
            <thead>
              <tr className="border-b border-slate-800 text-left text-xs uppercase tracking-wider text-slate-500">
                <th className="px-5 py-3">Rank</th>
                <th className="px-5 py-3">Sector</th>
                <th className="px-5 py-3 text-right">RS</th>
                <th className="px-5 py-3 text-right">MOM</th>
                <th className="px-5 py-3">Signal</th>
                <th className="px-5 py-3 text-right">Score</th>
                <th className="px-5 py-3 text-right">Rank Δ</th>
              </tr>
            </thead>

            <tbody>
              {data.sectors.map((sector) => (
                <tr
                  key={sector.sector}
                  className="border-b border-slate-800/70 transition hover:bg-slate-900/60"
                >
                  <td className="px-5 py-4">
                    <span className="font-semibold text-slate-300">
                      {sector.rank}
                    </span>
                  </td>

                  <td className="px-5 py-4">
                    <span className="font-semibold text-slate-100">
                      {sector.sector}
                    </span>
                  </td>

                  <td
                    className={`px-5 py-4 text-right font-medium ${
                      sector.rs >= 0
                        ? "text-emerald-400"
                        : "text-red-400"
                    }`}
                  >
                    {sector.rs >= 0 ? "+" : ""}
                    {sector.rs.toFixed(2)}%
                  </td>

                  <td
                    className={`px-5 py-4 text-right font-medium ${
                      sector.mom >= 0
                        ? "text-emerald-400"
                        : "text-red-400"
                    }`}
                  >
                    {sector.mom >= 0 ? "+" : ""}
                    {sector.mom.toFixed(2)}%
                  </td>

                  <td className="px-5 py-4">
                    <span
                      className={`font-medium ${getSignalClass(
                        sector.signal,
                      )}`}
                    >
                      {sector.signal}
                    </span>
                  </td>

                  <td className="px-5 py-4 text-right font-semibold text-slate-200">
                    {sector.score.toFixed(2)}
                  </td>

                  <td className="px-5 py-4">
                    <div className="flex justify-end">
                      <RankChange value={sector.rank_change} />
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Current rotation */}
      <div className="rounded-xl border border-slate-800 bg-[#0c1018] p-5">
        <div className="flex items-center gap-2">
          <ChevronUp size={17} className="text-cyan-400" />

          <h3 className="font-semibold">
            Current Rotation
          </h3>
        </div>

        <p className="mt-3 text-sm leading-6 text-slate-400">
          <span className="font-medium text-slate-200">
            {strongest?.sector}
          </span>{" "}
          currently has the strongest combined RS and momentum
          score.{" "}
          <span className="font-medium text-slate-200">
            {weakest?.sector}
          </span>{" "}
          is the weakest sector in the current ranking.
        </p>

        <p className="mt-2 text-xs text-slate-600">
          Rank change compares the current ranking with the
          previous available run.
        </p>
      </div>
    </div>
  );
}

export default SectorRotation;