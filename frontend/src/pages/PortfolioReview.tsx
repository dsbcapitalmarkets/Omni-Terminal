import { useEffect, useState } from "react";

interface Holding {
  ticker: string;
  current_price: number;
  pct_change: number;
  rs: number;
  ema_20: number;
  ema_50: number;
  supertrend: string;
  trend_state: string;
  risk_status: string;
  trailing_sl: number;
  pnl_pct: number;
  signal: string;
}

interface PortfolioReviewData {
  timestamp: string;
  status: string;
  holdings: Holding[];
  avg_pnl: number;
  total: number;
  exit_count: number;
  sell_count: number;
  hold_count: number;
}

export default function PortfolioReview() {
  const [data, setData] = useState<PortfolioReviewData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchPortfolioReview = async () => {
      try {
        setLoading(true);
        setError(null);

        const response = await fetch("/api/portfolio-review");

        if (!response.ok) {
          throw new Error(
            `Failed to fetch portfolio review: ${response.status}`
          );
        }

        const json = await response.json();

        if (json?.status === "error") {
          throw new Error(
            json.error || "Backend returned an error"
          );
        }

        setData(json as PortfolioReviewData);
      } catch (err) {
        setError(
          err instanceof Error
            ? err.message
            : "Failed to load portfolio review"
        );
      } finally {
        setLoading(false);
      }
    };

    fetchPortfolioReview();
  }, []);

  const formatNumber = (
    value: number | null | undefined,
    decimals = 2
  ) => {
    if (value === null || value === undefined || Number.isNaN(value)) {
      return "—";
    }

    return value.toLocaleString("en-IN", {
      minimumFractionDigits: decimals,
      maximumFractionDigits: decimals,
    });
  };

  const getSignalClass = (signal: string) => {
    switch (signal?.toUpperCase()) {
      case "EXIT":
        return "text-red-400 bg-red-400/10 border-red-400/20";

      case "SELL":
        return "text-orange-400 bg-orange-400/10 border-orange-400/20";

      case "HOLD":
        return "text-emerald-400 bg-emerald-400/10 border-emerald-400/20";

      default:
        return "text-slate-300 bg-slate-400/10 border-slate-400/20";
    }
  };

  const getRiskClass = (risk: string) => {
    switch (risk?.toUpperCase()) {
      case "BREACHED":
        return "text-red-400";

      case "AT RISK":
        return "text-orange-400";

      case "SAFE":
        return "text-emerald-400";

      default:
        return "text-slate-300";
    }
  };

  const getTrendClass = (trend: string) => {
    switch (trend?.toUpperCase()) {
      case "BULLISH":
        return "text-emerald-400";

      case "BEARISH":
        return "text-red-400";

      case "NEUTRAL":
        return "text-yellow-400";

      default:
        return "text-slate-300";
    }
  };

  const getSupertrendClass = (supertrend: string) => {
    switch (supertrend?.toUpperCase()) {
      case "BUY":
      case "BULLISH":
        return "text-emerald-400";

      case "SELL":
      case "BEARISH":
        return "text-red-400";

      default:
        return "text-slate-300";
    }
  };

  // ------------------------------------------------------------
  // Loading
  // ------------------------------------------------------------

  if (loading) {
    return (
      <div className="min-h-full space-y-6 p-6">
        <div className="animate-pulse">
          <div className="h-8 w-64 rounded bg-slate-800" />

          <div className="mt-2 h-4 w-96 rounded bg-slate-800" />

          <div className="mt-8 grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
            {[1, 2, 3, 4].map((item) => (
              <div
                key={item}
                className="h-28 rounded-xl border border-slate-800 bg-slate-900"
              />
            ))}
          </div>

          <div className="mt-6 h-96 rounded-xl border border-slate-800 bg-slate-900" />
        </div>
      </div>
    );
  }

  // ------------------------------------------------------------
  // Error
  // ------------------------------------------------------------

  if (error) {
    return (
      <div className="min-h-full p-6">
        <div className="rounded-xl border border-red-500/20 bg-red-500/10 p-6">
          <h2 className="text-lg font-semibold text-red-400">
            Unable to load Portfolio Review
          </h2>

          <p className="mt-2 text-sm text-slate-400">
            {error}
          </p>

          <button
            onClick={() => window.location.reload()}
            className="mt-4 rounded-lg border border-slate-700 bg-slate-800 px-4 py-2 text-sm text-slate-300 transition hover:bg-slate-700"
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  // ------------------------------------------------------------
  // No data
  // ------------------------------------------------------------

  if (!data) {
    return (
      <div className="min-h-full p-6">
        <div className="rounded-xl border border-slate-800 bg-slate-900 p-6 text-slate-400">
          No portfolio review data available.
        </div>
      </div>
    );
  }

  // ------------------------------------------------------------
  // Dashboard
  // ------------------------------------------------------------

  return (
    <div className="min-h-full space-y-6 p-6">

      {/* ======================================================
          HEADER
      ====================================================== */}

      <div>
        <div className="flex flex-wrap items-end justify-between gap-4">
          <div>
            <p className="mb-1 text-xs font-medium uppercase tracking-widest text-cyan-400">
              Analytics
            </p>

            <h1 className="text-3xl font-bold tracking-tight text-white">
              Portfolio Review
            </h1>

            <p className="mt-2 text-sm text-slate-500">
              Automated portfolio risk, trend and exit analysis
            </p>
          </div>

          <div className="text-right">
            <div className="text-xs uppercase tracking-wider text-slate-500">
              Last Update
            </div>

            <div className="mt-1 text-sm font-medium text-slate-300">
              {data.timestamp}
            </div>
          </div>
        </div>
      </div>

      {/* ======================================================
          SUMMARY CARDS
      ====================================================== */}

      <section className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">

        {/* Average P&L */}

        <div className="rounded-xl border border-slate-800 bg-[#0c1018] p-5">
          <div className="text-xs font-medium uppercase tracking-wider text-slate-500">
            Average P&L
          </div>

          <div
            className={`mt-3 text-2xl font-bold ${
              data.avg_pnl >= 0
                ? "text-emerald-400"
                : "text-red-400"
            }`}
          >
            {data.avg_pnl >= 0 ? "+" : ""}
            {formatNumber(data.avg_pnl)}%
          </div>

          <div className="mt-1 text-xs text-slate-500">
            Across {data.total} holding
            {data.total === 1 ? "" : "s"}
          </div>
        </div>

        {/* Exit Signals */}

        <div className="rounded-xl border border-slate-800 bg-[#0c1018] p-5">
          <div className="text-xs font-medium uppercase tracking-wider text-slate-500">
            Exit Signals
          </div>

          <div className="mt-3 text-2xl font-bold text-red-400">
            {data.exit_count}
          </div>

          <div className="mt-1 text-xs text-slate-500">
            Positions requiring exit
          </div>
        </div>

        {/* Sell Signals */}

        <div className="rounded-xl border border-slate-800 bg-[#0c1018] p-5">
          <div className="text-xs font-medium uppercase tracking-wider text-slate-500">
            Sell Signals
          </div>

          <div className="mt-3 text-2xl font-bold text-orange-400">
            {data.sell_count}
          </div>

          <div className="mt-1 text-xs text-slate-500">
            Positions with sell signal
          </div>
        </div>

        {/* Hold Positions */}

        <div className="rounded-xl border border-slate-800 bg-[#0c1018] p-5">
          <div className="text-xs font-medium uppercase tracking-wider text-slate-500">
            Hold Positions
          </div>

          <div className="mt-3 text-2xl font-bold text-emerald-400">
            {data.hold_count}
          </div>

          <div className="mt-1 text-xs text-slate-500">
            Positions currently held
          </div>
        </div>

      </section>

      {/* ======================================================
          PORTFOLIO STATUS
      ====================================================== */}

      <section className="grid grid-cols-1 gap-4 lg:grid-cols-3">

        <div className="rounded-xl border border-slate-800 bg-[#0c1018] p-5">
          <div className="text-xs uppercase tracking-wider text-slate-500">
            Total Positions
          </div>

          <div className="mt-2 text-2xl font-bold text-white">
            {data.total}
          </div>
        </div>

        <div className="rounded-xl border border-slate-800 bg-[#0c1018] p-5">
          <div className="text-xs uppercase tracking-wider text-slate-500">
            Action Required
          </div>

          <div className="mt-2 text-2xl font-bold text-orange-400">
            {data.exit_count + data.sell_count}
          </div>

          <div className="mt-1 text-xs text-slate-500">
            Exit + Sell signals
          </div>
        </div>

        <div className="rounded-xl border border-slate-800 bg-[#0c1018] p-5">
          <div className="text-xs uppercase tracking-wider text-slate-500">
            Data Status
          </div>

          <div className="mt-2 text-2xl font-bold text-emerald-400">
            {data.status.toUpperCase()}
          </div>
        </div>

      </section>

      {/* ======================================================
          HOLDINGS TABLE
      ====================================================== */}

      <section className="overflow-hidden rounded-xl border border-slate-800 bg-[#0c1018]">

        <div className="border-b border-slate-800 px-5 py-4">
          <div className="flex flex-wrap items-center justify-between gap-3">

            <div>
              <h2 className="text-lg font-semibold text-white">
                Holdings
              </h2>

              <p className="mt-1 text-xs text-slate-500">
                Current portfolio position analysis
              </p>
            </div>

            <div className="rounded-lg border border-slate-700 bg-slate-800/50 px-3 py-1.5 text-xs text-slate-300">
              {data.total} Position
              {data.total === 1 ? "" : "s"}
            </div>

          </div>
        </div>

        {data.holdings.length === 0 ? (

          <div className="px-5 py-12 text-center text-sm text-slate-500">
            No holdings available.
          </div>

        ) : (

          <div className="overflow-x-auto">

            <table className="w-full min-w-[1200px] text-sm">

              <thead>
                <tr className="border-b border-slate-800 text-left text-xs uppercase tracking-wider text-slate-500">

                  <th className="px-5 py-4">
                    Ticker
                  </th>

                  <th className="px-4 py-4 text-right">
                    Price
                  </th>

                  <th className="px-4 py-4 text-right">
                    Change
                  </th>

                  <th className="px-4 py-4 text-right">
                    RS
                  </th>

                  <th className="px-4 py-4 text-right">
                    EMA 20
                  </th>

                  <th className="px-4 py-4 text-right">
                    EMA 50
                  </th>

                  <th className="px-4 py-4">
                    Supertrend
                  </th>

                  <th className="px-4 py-4">
                    Trend
                  </th>

                  <th className="px-4 py-4">
                    Risk
                  </th>

                  <th className="px-4 py-4 text-right">
                    Trailing SL
                  </th>

                  <th className="px-4 py-4 text-right">
                    P&L
                  </th>

                  <th className="px-5 py-4">
                    Signal
                  </th>

                </tr>
              </thead>

              <tbody>

                {data.holdings.map((holding) => (

                  <tr
                    key={holding.ticker}
                    className="border-b border-slate-800/70 transition-colors hover:bg-slate-800/30"
                  >

                    {/* Ticker */}

                    <td className="px-5 py-4">
                      <span className="font-semibold text-white">
                        {holding.ticker}
                      </span>
                    </td>

                    {/* Price */}

                    <td className="px-4 py-4 text-right font-medium text-slate-200">
                      ₹{formatNumber(holding.current_price)}
                    </td>

                    {/* Daily Change */}

                    <td
                      className={`px-4 py-4 text-right font-medium ${
                        holding.pct_change >= 0
                          ? "text-emerald-400"
                          : "text-red-400"
                      }`}
                    >
                      {holding.pct_change >= 0 ? "+" : ""}
                      {formatNumber(holding.pct_change)}%
                    </td>

                    {/* Relative Strength */}

                    <td
                      className={`px-4 py-4 text-right font-medium ${
                        holding.rs >= 0
                          ? "text-emerald-400"
                          : "text-red-400"
                      }`}
                    >
                      {holding.rs >= 0 ? "+" : ""}
                      {formatNumber(holding.rs)}
                    </td>

                    {/* EMA 20 */}

                    <td className="px-4 py-4 text-right text-slate-300">
                      ₹{formatNumber(holding.ema_20)}
                    </td>

                    {/* EMA 50 */}

                    <td className="px-4 py-4 text-right text-slate-300">
                      ₹{formatNumber(holding.ema_50)}
                    </td>

                    {/* Supertrend */}

                    <td
                      className={`px-4 py-4 font-medium ${getSupertrendClass(
                        holding.supertrend
                      )}`}
                    >
                      {holding.supertrend}
                    </td>

                    {/* Trend */}

                    <td
                      className={`px-4 py-4 font-medium ${getTrendClass(
                        holding.trend_state
                      )}`}
                    >
                      {holding.trend_state}
                    </td>

                    {/* Risk */}

                    <td className="px-4 py-4">
                      <span
                        className={`font-medium ${getRiskClass(
                          holding.risk_status
                        )}`}
                      >
                        {holding.risk_status}
                      </span>
                    </td>

                    {/* Trailing Stop Loss */}

                    <td className="px-4 py-4 text-right text-slate-300">
                      ₹{formatNumber(holding.trailing_sl)}
                    </td>

                    {/* P&L */}

                    <td
                      className={`px-4 py-4 text-right font-semibold ${
                        holding.pnl_pct >= 0
                          ? "text-emerald-400"
                          : "text-red-400"
                      }`}
                    >
                      {holding.pnl_pct >= 0 ? "+" : ""}
                      {formatNumber(holding.pnl_pct)}%
                    </td>

                    {/* Signal */}

                    <td className="px-5 py-4">

                      <span
                        className={`inline-flex rounded-md border px-2.5 py-1 text-xs font-semibold ${getSignalClass(
                          holding.signal
                        )}`}
                      >
                        {holding.signal}
                      </span>

                    </td>

                  </tr>

                ))}

              </tbody>

            </table>

          </div>

        )}

      </section>

      {/* ======================================================
          FOOTER
      ====================================================== */}

      <div className="flex flex-wrap items-center justify-between gap-2 text-xs text-slate-500">

        <span>
          Data status:{" "}
          <span className="font-medium text-emerald-400">
            {data.status.toUpperCase()}
          </span>
        </span>

        <span>
          Portfolio review generated from the latest backend run
        </span>

      </div>

    </div>
  );
}