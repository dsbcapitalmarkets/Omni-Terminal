import { useEffect, useState } from "react";
import {
  Activity,
  BarChart3,
  CalendarDays,
  CircleAlert,
  ShieldCheck,
  TrendingUp,
} from "lucide-react";

// ============================================================
// TYPES
// ============================================================

interface MarketBreadthData {
  timestamp: string;
  status: string;
  regime: string;
  advances: number;
  declines: number;
  unchanged: number;
  new_highs: number;
  new_lows: number;
  ad_ratio: number;
  nh_nl_spread: number;
  num_above_50: number;
  pct_above_50: number;
  num_above_200: number;
  pct_above_200: number;
}

interface PortfolioHolding {
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

interface PortfolioData {
  timestamp: string;
  status: string;
  holdings: PortfolioHolding[];
  avg_pnl: number;
  total: number;
  exit_count: number;
  sell_count: number;
  hold_count: number;
}

interface ScreenerStock {
  symbol: string;
  exchange: string;
  score: number;
}

interface ScreenerData {
  timestamp: string;
  status: string;
  total_universe: number;
  nse_universe: number;
  bse_universe: number;
  passed_count: number;
  stocks: ScreenerStock[];
}

interface GoldSilverReturns {
  "1D": number;
  "1W": number;
  "1M": number;
  "1Y": number;
}

interface GoldSilverData {
  timestamp: string;
  status: string;
  gold_price: number;
  silver_price: number;
  gsr: number;
  gsr_mean: number;
  gsr_std: number;
  gsr_dev_pct: number;
  gsr_max: number;
  gsr_min: number;
  gold_trend: string;
  silver_trend: string;
  gold_vol: number;
  silver_vol: number;
  gold_returns: GoldSilverReturns;
  silver_returns: GoldSilverReturns;
  signal: string;
  strength: string;
  sentiment: string;
  better_performer: string;
}

interface EarningsItem {
  symbol: string;
  company: string;
  date: string;
  purpose: string;
  purpose_label: string;
  category: string;
  series: string;
}

interface EarningsData {
  timestamp: string;
  status: string;
  today_count: number;
  upcoming_count: number;
  today_counts: {
    quarterly: number;
    annual: number;
    board: number;
  };
  upcoming_counts: {
    quarterly: number;
    annual: number;
    board: number;
  };
  today_results: EarningsItem[];
  upcoming_results: EarningsItem[];
  screener_url: string;
}

// ============================================================
// HELPERS
// ============================================================

const formatNumber = (
  value: number | null | undefined,
  decimals = 2
) => {
  if (
    value === null ||
    value === undefined ||
    Number.isNaN(value)
  ) {
    return "—";
  }

  return value.toLocaleString("en-IN", {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  });
};

const formatPercent = (value: number) => {
  return `${value >= 0 ? "+" : ""}${formatNumber(value)}%`;
};

const getRegimeClass = (regime: string) => {
  const value = regime?.toUpperCase() ?? "";

  if (
    value.includes("BULL") ||
    value.includes("POSITIVE")
  ) {
    return "text-emerald-400";
  }

  if (
    value.includes("BEAR") ||
    value.includes("NEGATIVE")
  ) {
    return "text-red-400";
  }

  return "text-yellow-400";
};

// ============================================================
// COMPONENT
// ============================================================

export default function Home() {
  const [breadth, setBreadth] =
    useState<MarketBreadthData | null>(null);

  const [portfolio, setPortfolio] =
    useState<PortfolioData | null>(null);

  const [screener, setScreener] =
    useState<ScreenerData | null>(null);

  const [goldSilver, setGoldSilver] =
    useState<GoldSilverData | null>(null);

  const [earnings, setEarnings] =
    useState<EarningsData | null>(null);

  const [loading, setLoading] = useState(true);
  const [errorCount, setErrorCount] = useState(0);

  // ==========================================================
  // FETCH ALL DASHBOARD DATA
  // ==========================================================

  useEffect(() => {
    const fetchDashboard = async () => {
      setLoading(true);

      const endpoints = [
        {
          url: "/api/market-breadth",
          setter: setBreadth,
        },
        {
          url: "/api/portfolio-review",
          setter: setPortfolio,
        },
        {
          url: "/api/stock-screener",
          setter: setScreener,
        },
        {
          url: "/api/gold-silver",
          setter: setGoldSilver,
        },
        {
          url: "/api/earnings",
          setter: setEarnings,
        },
      ];

      let failures = 0;

      await Promise.all(
        endpoints.map(async ({ url, setter }) => {
          try {
            const response = await fetch(url);

            if (!response.ok) {
              throw new Error(
                `${url}: ${response.status}`
              );
            }

            const json = await response.json();

            if (json?.status === "error") {
              throw new Error(
                json.error || `${url}: backend error`
              );
            }

            setter(json);
          } catch (error) {
            failures += 1;

            console.error(
              `Dashboard API error: ${url}`,
              error
            );
          }
        })
      );

      setErrorCount(failures);
      setLoading(false);
    };

    fetchDashboard();
  }, []);

  // ==========================================================
  // LOADING
  // ==========================================================

  if (loading) {
    return (
      <div className="min-h-full space-y-6 p-6">
        <div className="animate-pulse">

          <div className="h-4 w-24 rounded bg-slate-800" />

          <div className="mt-3 h-9 w-72 rounded bg-slate-800" />

          <div className="mt-2 h-4 w-96 rounded bg-slate-800" />

          <div className="mt-8 grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
            {[1, 2, 3, 4].map((item) => (
              <div
                key={item}
                className="h-32 rounded-xl border border-slate-800 bg-slate-900"
              />
            ))}
          </div>

          <div className="mt-6 grid grid-cols-1 gap-4 lg:grid-cols-2">
            {[1, 2].map((item) => (
              <div
                key={item}
                className="h-72 rounded-xl border border-slate-800 bg-slate-900"
              />
            ))}
          </div>

        </div>
      </div>
    );
  }

  // ==========================================================
  // DASHBOARD
  // ==========================================================

  return (
    <div className="min-h-full space-y-6 p-6">

      {/* ======================================================
          HEADER
      ====================================================== */}

      <div className="flex flex-wrap items-end justify-between gap-4">

        <div>
          <p className="mb-1 text-xs font-medium uppercase tracking-widest text-cyan-400">
            Command Center
          </p>

          <h1 className="text-3xl font-bold tracking-tight text-white">
            Omni Terminal
          </h1>

          <p className="mt-2 text-sm text-slate-500">
            Market intelligence, portfolio risk and actionable signals
          </p>
        </div>

        <div className="text-right">

          <div className="text-xs uppercase tracking-wider text-slate-500">
            Latest Data
          </div>

          <div className="mt-1 text-sm font-medium text-slate-300">
            {breadth?.timestamp ??
              portfolio?.timestamp ??
              goldSilver?.timestamp ??
              "—"}
          </div>

        </div>

      </div>

      {/* ======================================================
          PARTIAL API WARNING
      ====================================================== */}

      {errorCount > 0 && (
        <div className="flex items-center gap-3 rounded-xl border border-orange-500/20 bg-orange-500/10 px-4 py-3">

          <CircleAlert
            size={18}
            className="text-orange-400"
          />

          <div className="text-sm text-orange-300">
            {errorCount} dashboard data source
            {errorCount === 1 ? "" : "s"} could not be loaded.
          </div>

        </div>
      )}

      {/* ======================================================
          TOP SUMMARY
      ====================================================== */}

      <section className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">

        {/* Market Regime */}

        <div className="rounded-xl border border-slate-800 bg-[#0c1018] p-5">

          <div className="flex items-start justify-between">

            <div className="text-xs font-medium uppercase tracking-wider text-slate-500">
              Market Regime
            </div>

            <Activity
              size={18}
              className="text-slate-600"
            />

          </div>

          <div
            className={`mt-3 text-2xl font-bold ${getRegimeClass(
              breadth?.regime ?? ""
            )}`}
          >
            {breadth?.regime ?? "—"}
          </div>

          <div className="mt-2 text-xs text-slate-500">
            A/D Ratio{" "}
            <span className="text-slate-300">
              {breadth
                ? formatNumber(breadth.ad_ratio)
                : "—"}
            </span>
          </div>

        </div>

        {/* Portfolio */}

        <div className="rounded-xl border border-slate-800 bg-[#0c1018] p-5">

          <div className="flex items-start justify-between">

            <div className="text-xs font-medium uppercase tracking-wider text-slate-500">
              Portfolio
            </div>

            <ShieldCheck
              size={18}
              className="text-slate-600"
            />

          </div>

          <div
            className={`mt-3 text-2xl font-bold ${
              (portfolio?.avg_pnl ?? 0) >= 0
                ? "text-emerald-400"
                : "text-red-400"
            }`}
          >
            {portfolio
              ? formatPercent(portfolio.avg_pnl)
              : "—"}
          </div>

          <div className="mt-2 text-xs text-slate-500">
            {portfolio?.hold_count ?? 0} Hold ·{" "}
            {portfolio?.sell_count ?? 0} Sell ·{" "}
            {portfolio?.exit_count ?? 0} Exit
          </div>

        </div>

        {/* Gold / Silver */}

        <div className="rounded-xl border border-slate-800 bg-[#0c1018] p-5">

          <div className="flex items-start justify-between">

            <div className="text-xs font-medium uppercase tracking-wider text-slate-500">
              Gold / Silver
            </div>

            <TrendingUp
              size={18}
              className="text-slate-600"
            />

          </div>

          <div className="mt-3 text-2xl font-bold text-cyan-400">
            {goldSilver?.better_performer ?? "—"}
          </div>

          <div className="mt-2 text-xs text-slate-500">
            GSR{" "}
            <span className="text-slate-300">
              {goldSilver
                ? formatNumber(goldSilver.gsr, 4)
                : "—"}
            </span>
          </div>

        </div>

        {/* Screener */}

        <div className="rounded-xl border border-slate-800 bg-[#0c1018] p-5">

          <div className="flex items-start justify-between">

            <div className="text-xs font-medium uppercase tracking-wider text-slate-500">
              Screener
            </div>

            <BarChart3
              size={18}
              className="text-slate-600"
            />

          </div>

          <div className="mt-3 text-2xl font-bold text-white">
            {screener?.passed_count ?? "—"}
          </div>

          <div className="mt-2 text-xs text-slate-500">
            Stocks passed from{" "}
            {screener?.total_universe
              ? formatNumber(screener.total_universe, 0)
              : "—"}{" "}
            universe
          </div>

        </div>

      </section>

      {/* ======================================================
          MARKET + PORTFOLIO
      ====================================================== */}

      <section className="grid grid-cols-1 gap-4 lg:grid-cols-2">

        {/* Market Breadth */}

        <div className="rounded-xl border border-slate-800 bg-[#0c1018] p-5">

          <div className="flex items-start justify-between">

            <div>
              <h2 className="text-lg font-semibold text-white">
                Market Breadth
              </h2>

              <p className="mt-1 text-xs text-slate-500">
                Current market participation
              </p>
            </div>

            <Activity
              size={20}
              className="text-slate-600"
            />

          </div>

          <div className="mt-6 grid grid-cols-2 gap-4">

            <div>
              <div className="text-xs uppercase tracking-wider text-slate-600">
                Advances
              </div>

              <div className="mt-1 text-xl font-bold text-emerald-400">
                {breadth?.advances ?? "—"}
              </div>
            </div>

            <div>
              <div className="text-xs uppercase tracking-wider text-slate-600">
                Declines
              </div>

              <div className="mt-1 text-xl font-bold text-red-400">
                {breadth?.declines ?? "—"}
              </div>
            </div>

            <div>
              <div className="text-xs uppercase tracking-wider text-slate-600">
                Above 50 DMA
              </div>

              <div className="mt-1 text-xl font-bold text-cyan-400">
                {breadth
                  ? formatNumber(breadth.pct_above_50) + "%"
                  : "—"}
              </div>
            </div>

            <div>
              <div className="text-xs uppercase tracking-wider text-slate-600">
                Above 200 DMA
              </div>

              <div className="mt-1 text-xl font-bold text-violet-400">
                {breadth
                  ? formatNumber(breadth.pct_above_200) + "%"
                  : "—"}
              </div>
            </div>

          </div>

          <div className="mt-6 border-t border-slate-800 pt-4">

            <div className="flex items-center justify-between text-xs">

              <span className="text-slate-500">
                New Highs
              </span>

              <span className="text-emerald-400">
                {breadth?.new_highs ?? "—"}
              </span>

            </div>

            <div className="mt-2 flex items-center justify-between text-xs">

              <span className="text-slate-500">
                New Lows
              </span>

              <span className="text-red-400">
                {breadth?.new_lows ?? "—"}
              </span>

            </div>

            <div className="mt-2 flex items-center justify-between text-xs">

              <span className="text-slate-500">
                NH-NL Spread
              </span>

              <span
                className={
                  (breadth?.nh_nl_spread ?? 0) >= 0
                    ? "text-emerald-400"
                    : "text-red-400"
                }
              >
                {breadth?.nh_nl_spread ?? "—"}
              </span>

            </div>

          </div>

        </div>

        {/* Portfolio */}

        <div className="rounded-xl border border-slate-800 bg-[#0c1018] p-5">

          <div className="flex items-start justify-between">

            <div>
              <h2 className="text-lg font-semibold text-white">
                Portfolio Health
              </h2>

              <p className="mt-1 text-xs text-slate-500">
                Current positions requiring attention
              </p>
            </div>

            <ShieldCheck
              size={20}
              className="text-slate-600"
            />

          </div>

          <div className="mt-6 grid grid-cols-3 gap-3">

            <div className="rounded-lg border border-emerald-500/10 bg-emerald-500/5 p-4">

              <div className="text-xs text-slate-500">
                Hold
              </div>

              <div className="mt-1 text-xl font-bold text-emerald-400">
                {portfolio?.hold_count ?? "—"}
              </div>

            </div>

            <div className="rounded-lg border border-orange-500/10 bg-orange-500/5 p-4">

              <div className="text-xs text-slate-500">
                Sell
              </div>

              <div className="mt-1 text-xl font-bold text-orange-400">
                {portfolio?.sell_count ?? "—"}
              </div>

            </div>

            <div className="rounded-lg border border-red-500/10 bg-red-500/5 p-4">

              <div className="text-xs text-slate-500">
                Exit
              </div>

              <div className="mt-1 text-xl font-bold text-red-400">
                {portfolio?.exit_count ?? "—"}
              </div>

            </div>

          </div>

          <div className="mt-6 border-t border-slate-800 pt-4">

            <div className="flex items-center justify-between">

              <span className="text-xs text-slate-500">
                Average P&L
              </span>

              <span
                className={`text-sm font-semibold ${
                  (portfolio?.avg_pnl ?? 0) >= 0
                    ? "text-emerald-400"
                    : "text-red-400"
                }`}
              >
                {portfolio
                  ? formatPercent(portfolio.avg_pnl)
                  : "—"}
              </span>

            </div>

            <div className="mt-3 flex items-center justify-between">

              <span className="text-xs text-slate-500">
                Action Required
              </span>

              <span className="text-sm font-semibold text-orange-400">
                {(portfolio?.exit_count ?? 0) +
                  (portfolio?.sell_count ?? 0)}
              </span>

            </div>

          </div>

        </div>

      </section>

      {/* ======================================================
          GOLD / SILVER + EARNINGS
      ====================================================== */}

      <section className="grid grid-cols-1 gap-4 lg:grid-cols-2">

        {/* Gold Silver */}

        <div className="rounded-xl border border-slate-800 bg-[#0c1018] p-5">

          <div className="flex items-start justify-between">

            <div>
              <h2 className="text-lg font-semibold text-white">
                Gold / Silver
              </h2>

              <p className="mt-1 text-xs text-slate-500">
                Relative performance and allocation signal
              </p>
            </div>

            <TrendingUp
              size={20}
              className="text-slate-600"
            />

          </div>

          <div className="mt-5 rounded-lg border border-cyan-500/10 bg-cyan-500/5 p-4">

            <div className="text-xs uppercase tracking-wider text-slate-500">
              Signal
            </div>

            <div className="mt-2 text-base font-semibold text-cyan-400">
              {goldSilver?.signal ?? "—"}
            </div>

            <div className="mt-2 text-xs text-slate-500">
              Strength:{" "}
              <span className="text-slate-300">
                {goldSilver?.strength ?? "—"}
              </span>
            </div>

          </div>

          <div className="mt-5 grid grid-cols-2 gap-4">

            <div>

              <div className="text-xs text-slate-500">
                Gold 1M
              </div>

              <div
                className={`mt-1 text-lg font-semibold ${
                  (goldSilver?.gold_returns["1M"] ?? 0) >= 0
                    ? "text-emerald-400"
                    : "text-red-400"
                }`}
              >
                {goldSilver
                  ? formatPercent(
                      goldSilver.gold_returns["1M"]
                    )
                  : "—"}
              </div>

            </div>

            <div>

              <div className="text-xs text-slate-500">
                Silver 1M
              </div>

              <div
                className={`mt-1 text-lg font-semibold ${
                  (goldSilver?.silver_returns["1M"] ?? 0) >= 0
                    ? "text-emerald-400"
                    : "text-red-400"
                }`}
              >
                {goldSilver
                  ? formatPercent(
                      goldSilver.silver_returns["1M"]
                    )
                  : "—"}
              </div>

            </div>

            <div>

              <div className="text-xs text-slate-500">
                Gold 1Y
              </div>

              <div className="mt-1 text-lg font-semibold text-emerald-400">
                {goldSilver
                  ? formatPercent(
                      goldSilver.gold_returns["1Y"]
                    )
                  : "—"}
              </div>

            </div>

            <div>

              <div className="text-xs text-slate-500">
                Silver 1Y
              </div>

              <div className="mt-1 text-lg font-semibold text-emerald-400">
                {goldSilver
                  ? formatPercent(
                      goldSilver.silver_returns["1Y"]
                    )
                  : "—"}
              </div>

            </div>

          </div>

          <div className="mt-5 flex items-center justify-between border-t border-slate-800 pt-4">

            <span className="text-xs text-slate-500">
              Current GSR
            </span>

            <span className="text-sm font-semibold text-white">
              {goldSilver
                ? formatNumber(goldSilver.gsr, 4)
                : "—"}
            </span>

          </div>

        </div>

        {/* Earnings */}

        <div className="rounded-xl border border-slate-800 bg-[#0c1018] p-5">

          <div className="flex items-start justify-between">

            <div>
              <h2 className="text-lg font-semibold text-white">
                Upcoming Earnings
              </h2>

              <p className="mt-1 text-xs text-slate-500">
                Next scheduled financial results
              </p>
            </div>

            <CalendarDays
              size={20}
              className="text-slate-600"
            />

          </div>

          <div className="mt-5 space-y-3">

            {earnings?.upcoming_results
              ?.slice(0, 4)
              .map((item) => (

                <div
                  key={`${item.symbol}-${item.date}`}
                  className="flex items-center justify-between rounded-lg border border-slate-800/80 bg-slate-900/30 p-3"
                >

                  <div className="min-w-0">

                    <div className="truncate text-sm font-medium text-white">
                      {item.company}
                    </div>

                    <div className="mt-1 text-xs text-slate-500">
                      {item.symbol}
                    </div>

                  </div>

                  <div className="ml-4 flex-shrink-0 text-right">

                    <div className="text-sm font-medium text-cyan-400">
                      {item.date}
                    </div>

                    <div className="mt-1 text-xs text-slate-600">
                      {item.category}
                    </div>

                  </div>

                </div>

              ))}

            {!earnings?.upcoming_results?.length && (
              <div className="py-8 text-center text-sm text-slate-500">
                No upcoming earnings available.
              </div>
            )}

          </div>

          <div className="mt-4 border-t border-slate-800 pt-4">

            <div className="flex items-center justify-between text-xs">

              <span className="text-slate-500">
                Upcoming events
              </span>

              <span className="font-medium text-slate-300">
                {earnings?.upcoming_count ?? "—"}
              </span>

            </div>

          </div>

        </div>

      </section>

      {/* ======================================================
          STOCK SCREENER
      ====================================================== */}

      <section className="overflow-hidden rounded-xl border border-slate-800 bg-[#0c1018]">

        <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-800 px-5 py-4">

          <div>

            <h2 className="text-lg font-semibold text-white">
              Top Screener Candidates
            </h2>

            <p className="mt-1 text-xs text-slate-500">
              Highest-scoring stocks from the latest screening run
            </p>

          </div>

          <div className="rounded-lg border border-slate-700 bg-slate-800/50 px-3 py-1.5 text-xs text-slate-300">
            {screener?.passed_count ?? 0} Passed
          </div>

        </div>

        {!screener?.stocks?.length ? (

          <div className="px-5 py-10 text-center text-sm text-slate-500">
            No screener candidates available.
          </div>

        ) : (

          <div className="overflow-x-auto">

            <table className="w-full min-w-[500px] text-sm">

              <thead>

                <tr className="border-b border-slate-800 text-left text-xs uppercase tracking-wider text-slate-500">

                  <th className="px-5 py-3">
                    Rank
                  </th>

                  <th className="px-4 py-3">
                    Symbol
                  </th>

                  <th className="px-4 py-3">
                    Exchange
                  </th>

                  <th className="px-5 py-3 text-right">
                    Score
                  </th>

                </tr>

              </thead>

              <tbody>

                {screener.stocks
                  .slice(0, 10)
                  .map((stock, index) => (

                    <tr
                      key={`${stock.symbol}-${stock.exchange}`}
                      className="border-b border-slate-800/60 transition-colors hover:bg-slate-900/50"
                    >

                      <td className="px-5 py-3 text-slate-600">
                        {index + 1}
                      </td>

                      <td className="px-4 py-3 font-semibold text-white">
                        {stock.symbol}
                      </td>

                      <td className="px-4 py-3 text-slate-400">
                        {stock.exchange}
                      </td>

                      <td className="px-5 py-3 text-right font-semibold text-cyan-400">
                        {formatNumber(stock.score, 3)}
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

      <div className="flex flex-wrap items-center justify-between gap-2 border-t border-slate-800 pt-4 text-xs text-slate-600">

        <span>
          Omni Terminal · Market Intelligence
        </span>

        <span>
          {errorCount === 0
            ? "All data sources connected"
            : `${errorCount} data source${
                errorCount === 1 ? "" : "s"
              } unavailable`}
        </span>

      </div>

    </div>
  );
}