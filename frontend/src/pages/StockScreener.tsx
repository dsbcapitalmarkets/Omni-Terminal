import { useEffect, useState } from "react";
import {
  Search,
  BarChart3,
  Database,
  Filter,
  TrendingUp,
} from "lucide-react";

// ============================================================
// TYPES
// ============================================================

interface ScreenerStock {
  symbol: string;
  exchange: string;
  score: number;
}

interface StockScreenerData {
  timestamp: string;
  status: string;
  total_universe: number;
  nse_universe: number;
  bse_universe: number;
  passed_count: number;
  stocks: ScreenerStock[];
}

// ============================================================
// API
// ============================================================

const API_URL = "/api/stock-screener";

// ============================================================
// METRIC CARD
// ============================================================

function MetricCard({
  title,
  value,
  subtitle,
  icon,
}: {
  title: string;
  value: string;
  subtitle: string;
  icon: React.ReactNode;
}) {
  return (
    <div className="rounded-xl border border-slate-800 bg-[#0c1018] p-5">
      <div className="flex items-start justify-between">
        <div className="text-xs font-medium uppercase tracking-wider text-slate-500">
          {title}
        </div>

        <div className="text-slate-600">
          {icon}
        </div>
      </div>

      <div className="mt-3 text-2xl font-bold tracking-tight text-white">
        {value}
      </div>

      <div className="mt-1 text-xs text-slate-500">
        {subtitle}
      </div>
    </div>
  );
}

// ============================================================
// STOCK SCREENER
// ============================================================

export default function StockScreener() {
  const [data, setData] = useState<StockScreenerData | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState<string>("");

  // ==========================================================
  // FETCH DATA
  // ==========================================================

  useEffect(() => {
    const fetchData = async () => {
      try {
        setLoading(true);
        setError(null);

        const response = await fetch(API_URL);

        if (!response.ok) {
          throw new Error(
            `API request failed with status ${response.status}`
          );
        }

        const json: StockScreenerData = await response.json();

        if (json.status !== "ok") {
          throw new Error(
            "API returned an error while loading stock screener data"
          );
        }

        setData(json);
      } catch (err) {
        console.error("Stock Screener API error:", err);

        if (err instanceof Error) {
          setError(err.message);
        } else {
          setError("Failed to load stock screener data");
        }
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, []);

  // ==========================================================
  // FORMATTERS
  // ==========================================================

  const formatNumber = (value: number, decimals = 0) => {
    return value.toLocaleString("en-IN", {
      minimumFractionDigits: decimals,
      maximumFractionDigits: decimals,
    });
  };

  const formatScore = (value: number) => {
    return value.toFixed(3);
  };

  // ==========================================================
  // FILTER
  // ==========================================================

  const filteredStocks =
    data?.stocks.filter((stock) => {
      const query = search.trim().toLowerCase();

      if (!query) {
        return true;
      }

      return (
        stock.symbol.toLowerCase().includes(query) ||
        stock.exchange.toLowerCase().includes(query)
      );
    }) ?? [];

  // ==========================================================
  // LOADING
  // ==========================================================

  if (loading) {
    return (
      <div className="min-h-full p-6">
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

  // ==========================================================
  // ERROR
  // ==========================================================

  if (error || !data) {
    return (
      <div className="min-h-full p-6">
        <div className="mb-6">
          <p className="mb-1 text-xs font-medium uppercase tracking-widest text-cyan-400">
            Analytics
          </p>

          <h1 className="text-3xl font-bold tracking-tight text-white">
            Stock Screener
          </h1>

          <p className="mt-2 text-sm text-red-400">
            Failed to load stock screener data.
          </p>
        </div>

        <div className="rounded-xl border border-red-900/50 bg-[#0c1018] p-5">
          <div className="text-sm text-red-400">
            {error ?? "No data received from API."}
          </div>

          <div className="mt-2 text-xs text-slate-600">
            API: {API_URL}
          </div>
        </div>
      </div>
    );
  }

  // ==========================================================
  // PAGE
  // ==========================================================

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
              Stock Screener
            </h1>

            <p className="mt-2 text-sm text-slate-500">
              Systematic screening of the available NSE and BSE universe
            </p>
          </div>

          <div className="text-right text-xs text-slate-500">
            <div>Last update</div>

            <div className="mt-1 font-medium text-slate-300">
              {data.timestamp}
            </div>
          </div>
        </div>
      </div>

      {/* ======================================================
          SUMMARY METRICS
      ====================================================== */}

      <section className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">

        <MetricCard
          title="Total Universe"
          value={formatNumber(data.total_universe)}
          subtitle="All screened securities"
          icon={<Database size={18} />}
        />

        <MetricCard
          title="NSE Universe"
          value={formatNumber(data.nse_universe)}
          subtitle="NSE securities"
          icon={<BarChart3 size={18} />}
        />

        <MetricCard
          title="BSE Universe"
          value={formatNumber(data.bse_universe)}
          subtitle="BSE securities"
          icon={<Database size={18} />}
        />

        <MetricCard
          title="Passed"
          value={formatNumber(data.passed_count)}
          subtitle="Stocks passing the screener"
          icon={<TrendingUp size={18} />}
        />

      </section>

      {/* ======================================================
          PASS RATE
      ====================================================== */}

      <section className="rounded-xl border border-slate-800 bg-[#0c1018] p-5">

        <div className="flex flex-wrap items-center justify-between gap-4">

          <div>
            <div className="text-xs font-medium uppercase tracking-wider text-slate-500">
              Screener Result
            </div>

            <div className="mt-2 text-xl font-semibold text-white">
              {formatNumber(data.passed_count)} stocks passed
            </div>

            <p className="mt-1 text-xs text-slate-500">
              From a total universe of{" "}
              {formatNumber(data.total_universe)} securities
            </p>
          </div>

          <div className="text-right">
            <div className="text-xs text-slate-500">
              Pass Rate
            </div>

            <div className="mt-1 text-2xl font-bold text-cyan-400">
              {data.total_universe > 0
                ? ((data.passed_count / data.total_universe) * 100).toFixed(2)
                : "0.00"}
              %
            </div>
          </div>

        </div>

        {/* Progress bar */}

        <div className="mt-5 h-2 overflow-hidden rounded-full bg-slate-800">
          <div
            className="h-full rounded-full bg-cyan-400 transition-all"
            style={{
              width: `${
                data.total_universe > 0
                  ? Math.min(
                      (data.passed_count / data.total_universe) * 100,
                      100
                    )
                  : 0
              }%`,
            }}
          />
        </div>

      </section>

      {/* ======================================================
          RESULTS TABLE
      ====================================================== */}

      <section className="overflow-hidden rounded-xl border border-slate-800 bg-[#0c1018]">

        {/* Table Header */}

        <div className="border-b border-slate-800 px-5 py-4">

          <div className="flex flex-wrap items-center justify-between gap-4">

            <div>
              <h2 className="text-lg font-semibold text-white">
                Screening Results
              </h2>

              <p className="mt-1 text-xs text-slate-500">
                Stocks ranked by screener score
              </p>
            </div>

            <div className="flex items-center gap-3">

              <div className="flex items-center gap-2 rounded-lg border border-slate-700 bg-slate-900 px-3 py-2">

                <Search
                  size={15}
                  className="text-slate-500"
                />

                <input
                  type="text"
                  value={search}
                  onChange={(event) => setSearch(event.target.value)}
                  placeholder="Search symbol..."
                  className="w-40 bg-transparent text-sm text-slate-200 outline-none placeholder:text-slate-600"
                />

              </div>

              <div className="hidden items-center gap-2 rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 text-xs text-slate-400 sm:flex">

                <Filter size={14} />

                {filteredStocks.length} result
                {filteredStocks.length === 1 ? "" : "s"}

              </div>

            </div>

          </div>

        </div>

        {/* Table */}

        {filteredStocks.length === 0 ? (

          <div className="px-5 py-12 text-center">

            <div className="text-sm text-slate-500">
              No stocks match your search.
            </div>

          </div>

        ) : (

          <div className="overflow-x-auto">

            <table className="w-full min-w-[600px] text-sm">

              <thead>

                <tr className="border-b border-slate-800 text-left text-xs uppercase tracking-wider text-slate-500">

                  <th className="px-5 py-4">
                    Rank
                  </th>

                  <th className="px-5 py-4">
                    Symbol
                  </th>

                  <th className="px-5 py-4">
                    Exchange
                  </th>

                  <th className="px-5 py-4 text-right">
                    Score
                  </th>

                </tr>

              </thead>

              <tbody>

                {filteredStocks.map((stock, index) => (

                  <tr
                    key={`${stock.exchange}-${stock.symbol}`}
                    className="border-b border-slate-800/70 transition-colors hover:bg-slate-800/30"
                  >

                    <td className="px-5 py-4 text-slate-500">
                      #{index + 1}
                    </td>

                    <td className="px-5 py-4">

                      <span className="font-semibold text-white">
                        {stock.symbol}
                      </span>

                    </td>

                    <td className="px-5 py-4">

                      <span
                        className={`inline-flex rounded-md border px-2.5 py-1 text-xs font-medium ${
                          stock.exchange.toUpperCase() === "NSE"
                            ? "border-blue-400/20 bg-blue-400/10 text-blue-400"
                            : "border-purple-400/20 bg-purple-400/10 text-purple-400"
                        }`}
                      >
                        {stock.exchange}
                      </span>

                    </td>

                    <td
                      className={`px-5 py-4 text-right font-semibold ${
                        stock.score > 0
                          ? "text-emerald-400"
                          : stock.score < 0
                            ? "text-red-400"
                            : "text-slate-300"
                      }`}
                    >
                      {formatScore(stock.score)}
                    </td>

                  </tr>

                ))}

              </tbody>

            </table>

          </div>

        )}

      </section>

      {/* ======================================================
          STATUS
      ====================================================== */}

      <div className="flex flex-wrap items-center justify-between gap-2 text-xs text-slate-500">

        <span>
          Data status:{" "}
          <span className="font-medium text-emerald-400">
            {data.status.toUpperCase()}
          </span>
        </span>

        <span>
          Showing {filteredStocks.length} of {data.passed_count} passed stocks
        </span>

      </div>

    </div>
  );
}