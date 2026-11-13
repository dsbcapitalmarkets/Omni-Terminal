
import { useEffect, useMemo, useState } from "react";
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

type Exchange = "NSE" | "BSE" | "BOTH";

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

        <div className="text-slate-600">{icon}</div>
      </div>

      <div className="mt-3 text-2xl font-bold tracking-tight text-white">
        {value}
      </div>

      <div className="mt-1 text-xs text-slate-500">{subtitle}</div>
    </div>
  );
}

// ============================================================
// EXCHANGE SELECTOR
// ============================================================

function ExchangeSelector({
  exchange,
  onChange,
}: {
  exchange: Exchange;
  onChange: (value: Exchange) => void;
}) {
  const options: Exchange[] = ["NSE", "BSE", "BOTH"];

  return (
    <div className="inline-flex rounded-lg border border-slate-800 bg-[#0c1018] p-1">
      {options.map((option) => {
        const active = exchange === option;

        return (
          <button
            key={option}
            onClick={() => onChange(option)}
            className={`rounded-md px-5 py-2 text-xs font-semibold transition-all ${
              active
                ? "bg-cyan-500 text-slate-950 shadow-sm"
                : "text-slate-400 hover:bg-slate-800 hover:text-white"
            }`}
          >
            {option === "BOTH" ? "Both" : option}
          </button>
        );
      })}
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
  const [exchange, setExchange] = useState<Exchange>("BOTH");

  // ==========================================================
  // FETCH DATA
  // ==========================================================

  useEffect(() => {
    const fetchData = async () => {
      try {
        setLoading(true);
        setError(null);

        const response = await fetch(`${API_URL}?exchange=BOTH`);

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

        setError(
          err instanceof Error
            ? err.message
            : "Failed to load stock screener data"
        );
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
  // EXCHANGE FILTER
  // ==========================================================

  const exchangeStocks = useMemo(() => {
    if (!data) return [];

    if (exchange === "BOTH") {
      return data.stocks;
    }

    return data.stocks.filter(
      (stock) => stock.exchange.toUpperCase() === exchange
    );
  }, [data, exchange]);

  // ==========================================================
  // SEARCH FILTER
  // ==========================================================

  const filteredStocks = useMemo(() => {
    const query = search.trim().toLowerCase();

    if (!query) {
      return exchangeStocks;
    }

    return exchangeStocks.filter(
      (stock) =>
        stock.symbol.toLowerCase().includes(query) ||
        stock.exchange.toLowerCase().includes(query)
    );
  }, [exchangeStocks, search]);

  // ==========================================================
  // DYNAMIC METRICS
  // ==========================================================

  const selectedUniverse = useMemo(() => {
    if (!data) return 0;

    switch (exchange) {
      case "NSE":
        return data.nse_universe;

      case "BSE":
        return data.bse_universe;

      default:
        return data.total_universe;
    }
  }, [data, exchange]);

  const selectedPassed = exchangeStocks.length;

  const passRate =
    selectedUniverse > 0
      ? (selectedPassed / selectedUniverse) * 100
      : 0;

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
          EXCHANGE SELECTOR
      ====================================================== */}

      <section className="flex flex-wrap items-center justify-between gap-4 rounded-xl border border-slate-800 bg-[#0c1018] p-4">

        <div>
          <div className="text-sm font-semibold text-white">
            Exchange
          </div>

          <p className="mt-1 text-xs text-slate-500">
            Select the stock market universe to screen
          </p>
        </div>

        <ExchangeSelector
          exchange={exchange}
          onChange={setExchange}
        />

      </section>

      {/* ======================================================
          SUMMARY METRICS
      ====================================================== */}

      <section className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">

        <MetricCard
          title="Selected Universe"
          value={formatNumber(selectedUniverse)}
          subtitle={`${exchange === "BOTH" ? "NSE + BSE" : exchange} securities`}
          icon={<Database size={18} />}
        />

        <MetricCard
          title="NSE Universe"
          value={formatNumber(data.nse_universe)}
          subtitle="Total NSE securities"
          icon={<BarChart3 size={18} />}
        />

        <MetricCard
          title="BSE Universe"
          value={formatNumber(data.bse_universe)}
          subtitle="Total BSE securities"
          icon={<Database size={18} />}
        />

        <MetricCard
          title="Passed"
          value={formatNumber(selectedPassed)}
          subtitle={`${exchange === "BOTH" ? "Combined" : exchange} qualifying stocks`}
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
              {formatNumber(selectedPassed)} stocks passed
            </div>

            <p className="mt-1 text-xs text-slate-500">
              From a total universe of{" "}
              {formatNumber(selectedUniverse)} securities
            </p>
          </div>

          <div className="text-right">
            <div className="text-xs text-slate-500">
              Pass Rate
            </div>

            <div className="mt-1 text-2xl font-bold text-cyan-400">
              {passRate.toFixed(2)}%
            </div>
          </div>

        </div>

        <div className="mt-5 h-2 overflow-hidden rounded-full bg-slate-800">
          <div
            className="h-full rounded-full bg-cyan-400 transition-all duration-300"
            style={{
              width: `${Math.min(passRate, 100)}%`,
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
                {exchange === "BOTH"
                  ? "NSE + BSE stocks"
                  : `${exchange} stocks`}{" "}
                ranked by screener score
              </p>
            </div>

            <div className="flex items-center gap-3">

              <div className="flex items-center gap-2 rounded-lg border border-slate-700 bg-slate-900 px-3 py-2">

                <Search size={15} className="text-slate-500" />

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
              {search
                ? "No stocks match your search."
                : `No qualifying stocks found for ${exchange}.`}
            </div>
          </div>

        ) : (

          <div className="overflow-x-auto">

            <table className="w-full min-w-[600px] text-sm">

              <thead>
                <tr className="border-b border-slate-800 text-left text-xs uppercase tracking-wider text-slate-500">

                  <th className="px-5 py-4">Rank</th>

                  <th className="px-5 py-4">Symbol</th>

                  <th className="px-5 py-4">Exchange</th>

                  <th className="px-5 py-4 text-right">Score</th>

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
          Showing {filteredStocks.length} of {selectedPassed} passed stocks
        </span>

      </div>

    </div>
  );
}
