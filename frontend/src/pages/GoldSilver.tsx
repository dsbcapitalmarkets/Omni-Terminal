import { useEffect, useState, type ReactNode } from "react";
import {
  Activity,
  ArrowDown,
  ArrowUp,
  BarChart3,
  Coins,
  Gauge,
  TrendingUp,
} from "lucide-react";

// ============================================================
// TYPES
// ============================================================

interface ReturnsData {
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

  gold_returns: ReturnsData;
  silver_returns: ReturnsData;

  signal: string;
  strength: string;
  sentiment: string;
  better_performer: string;
}

// ============================================================
// API
// ============================================================

const API_URL = "http://127.0.0.1:8000/api/gold-silver";

// ============================================================
// METRIC CARD
// ============================================================

function MetricCard({
  title,
  value,
  subtitle,
  icon,
  valueClass = "text-white",
}: {
  title: string;
  value: string;
  subtitle: string;
  icon: ReactNode;
  valueClass?: string;
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

      <div className={`mt-3 text-2xl font-bold tracking-tight ${valueClass}`}>
        {value}
      </div>

      <div className="mt-1 text-xs text-slate-500">
        {subtitle}
      </div>
    </div>
  );
}

// ============================================================
// RETURN VALUE
// ============================================================

function ReturnValue({ value }: { value: number }) {
  const positive = value >= 0;

  return (
    <span
      className={
        positive
          ? "font-medium text-emerald-400"
          : "font-medium text-red-400"
      }
    >
      {positive ? "+" : ""}
      {value.toFixed(2)}%
    </span>
  );
}

// ============================================================
// TREND
// ============================================================

function TrendBadge({ trend }: { trend: string }) {
  const normalized = trend.toUpperCase();

  const isBullish = normalized === "BULLISH";
  const isBearish = normalized === "BEARISH";

  return (
    <span
      className={`inline-flex items-center gap-1 rounded-md border px-2.5 py-1 text-xs font-semibold ${
        isBullish
          ? "border-emerald-400/20 bg-emerald-400/10 text-emerald-400"
          : isBearish
            ? "border-red-400/20 bg-red-400/10 text-red-400"
            : "border-slate-400/20 bg-slate-400/10 text-slate-300"
      }`}
    >
      {isBullish ? (
        <ArrowUp size={13} />
      ) : isBearish ? (
        <ArrowDown size={13} />
      ) : null}

      {trend}
    </span>
  );
}

// ============================================================
// GOLD SILVER
// ============================================================

export default function GoldSilver() {
  const [data, setData] = useState<GoldSilverData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

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

        const contentType =
          response.headers.get("content-type") ?? "";

        if (!contentType.includes("application/json")) {
          const text = await response.text();

          throw new Error(
            `Expected JSON from API, but received ${
              contentType || "unknown content type"
            }. Response starts with: ${text.slice(0, 100)}`
          );
        }

        const json: GoldSilverData = await response.json();

        if (json?.status === "error") {
          throw new Error("Backend returned an error");
        }

        setData(json);
      } catch (err) {
        console.error("Gold-Silver API error:", err);

        setError(
          err instanceof Error
            ? err.message
            : "Failed to load gold-silver data"
        );
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, []);

  // ==========================================================
  // LOADING
  // ==========================================================

  if (loading) {
    return (
      <div className="min-h-full space-y-6 p-6">
        <div className="animate-pulse">
          <div className="h-8 w-72 rounded bg-slate-800" />

          <div className="mt-2 h-4 w-96 rounded bg-slate-800" />

          <div className="mt-8 grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
            {[1, 2, 3, 4].map((item) => (
              <div
                key={item}
                className="h-28 rounded-xl border border-slate-800 bg-slate-900"
              />
            ))}
          </div>

          <div className="mt-6 h-64 rounded-xl border border-slate-800 bg-slate-900" />
        </div>
      </div>
    );
  }

  // ==========================================================
  // ERROR
  // ==========================================================

  if (error) {
    return (
      <div className="min-h-full p-6">
        <div className="rounded-xl border border-red-500/20 bg-red-500/10 p-6">
          <h2 className="text-lg font-semibold text-red-400">
            Unable to load Gold-Silver Ratio
          </h2>

          <p className="mt-2 text-sm text-slate-400">
            {error}
          </p>

          <div className="mt-2 text-xs text-slate-600">
            API: {API_URL}
          </div>

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

  // ==========================================================
  // NO DATA
  // ==========================================================

  if (!data) {
    return (
      <div className="min-h-full p-6">
        <div className="rounded-xl border border-slate-800 bg-slate-900 p-6 text-slate-400">
          No gold-silver data available.
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
              Commodities
            </p>

            <h1 className="text-3xl font-bold tracking-tight text-white">
              Gold-Silver Ratio
            </h1>

            <p className="mt-2 text-sm text-slate-500">
              Relative valuation, momentum and risk analysis of gold and silver
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
          SIGNAL
      ====================================================== */}

      <section className="rounded-xl border border-slate-800 bg-[#0c1018] p-5">

        <div className="flex flex-wrap items-center justify-between gap-5">

          <div>
            <div className="text-xs uppercase tracking-wider text-slate-500">
              Current Signal
            </div>

            <div className="mt-2 text-2xl font-bold text-white">
              {data.signal}
            </div>

            <div className="mt-2 text-sm text-slate-500">
              Relative strength:{" "}
              <span className="font-medium text-slate-300">
                {data.strength}
              </span>
            </div>
          </div>

          <div className="rounded-lg border border-slate-700 bg-slate-900 px-5 py-4 text-right">

            <div className="text-xs uppercase tracking-wider text-slate-500">
              Better Performer
            </div>

            <div className="mt-1 text-xl font-bold text-emerald-400">
              {data.better_performer}
            </div>

          </div>

        </div>

      </section>


      {/* ======================================================
          PRIMARY METRICS
      ====================================================== */}

      <section className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">

        <MetricCard
          title="Gold Price"
          value={data.gold_price.toFixed(2)}
          subtitle="Latest gold price"
          icon={<Coins size={18} />}
        />

        <MetricCard
          title="Silver Price"
          value={data.silver_price.toFixed(2)}
          subtitle="Latest silver price"
          icon={<Coins size={18} />}
        />

        <MetricCard
          title="Gold-Silver Ratio"
          value={data.gsr.toFixed(4)}
          subtitle={`Mean: ${data.gsr_mean.toFixed(4)}`}
          icon={<BarChart3 size={18} />}
        />

        <MetricCard
          title="Ratio Deviation"
          value={`${data.gsr_dev_pct >= 0 ? "+" : ""}${data.gsr_dev_pct.toFixed(2)}%`}
          subtitle="Deviation from historical mean"
          icon={<Activity size={18} />}
          valueClass={
            data.gsr_dev_pct >= 0
              ? "text-orange-400"
              : "text-emerald-400"
          }
        />

      </section>


      {/* ======================================================
          RATIO STATISTICS
      ====================================================== */}

      <section className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">

        <MetricCard
          title="Ratio Mean"
          value={data.gsr_mean.toFixed(4)}
          subtitle="Historical average"
          icon={<Gauge size={18} />}
        />

        <MetricCard
          title="Ratio Std Dev"
          value={data.gsr_std.toFixed(4)}
          subtitle="Historical volatility"
          icon={<Activity size={18} />}
        />

        <MetricCard
          title="Ratio High"
          value={data.gsr_max.toFixed(4)}
          subtitle="Observed maximum"
          icon={<ArrowUp size={18} />}
        />

        <MetricCard
          title="Ratio Low"
          value={data.gsr_min.toFixed(4)}
          subtitle="Observed minimum"
          icon={<ArrowDown size={18} />}
        />

      </section>


      {/* ======================================================
          GOLD VS SILVER
      ====================================================== */}

      <section className="grid grid-cols-1 gap-4 xl:grid-cols-2">

        {/* GOLD */}

        <div className="rounded-xl border border-slate-800 bg-[#0c1018] p-5">

          <div className="flex items-center justify-between">

            <div>
              <h2 className="text-lg font-semibold text-white">
                Gold
              </h2>

              <p className="mt-1 text-xs text-slate-500">
                Price performance and volatility
              </p>
            </div>

            <TrendBadge trend={data.gold_trend} />

          </div>

          <div className="mt-6 grid grid-cols-2 gap-4">

            <div>
              <div className="text-xs uppercase tracking-wider text-slate-500">
                Price
              </div>

              <div className="mt-1 text-xl font-bold text-white">
                {data.gold_price.toFixed(2)}
              </div>
            </div>

            <div>
              <div className="text-xs uppercase tracking-wider text-slate-500">
                Volatility
              </div>

              <div className="mt-1 text-xl font-bold text-slate-200">
                {data.gold_vol.toFixed(2)}
              </div>
            </div>

          </div>

          <div className="mt-6 border-t border-slate-800 pt-5">

            <div className="mb-4 text-xs uppercase tracking-wider text-slate-500">
              Returns
            </div>

            <div className="grid grid-cols-4 gap-3">

              <div>
                <div className="text-xs text-slate-600">
                  1D
                </div>
                <div className="mt-1">
                  <ReturnValue value={data.gold_returns["1D"]} />
                </div>
              </div>

              <div>
                <div className="text-xs text-slate-600">
                  1W
                </div>
                <div className="mt-1">
                  <ReturnValue value={data.gold_returns["1W"]} />
                </div>
              </div>

              <div>
                <div className="text-xs text-slate-600">
                  1M
                </div>
                <div className="mt-1">
                  <ReturnValue value={data.gold_returns["1M"]} />
                </div>
              </div>

              <div>
                <div className="text-xs text-slate-600">
                  1Y
                </div>
                <div className="mt-1">
                  <ReturnValue value={data.gold_returns["1Y"]} />
                </div>
              </div>

            </div>

          </div>

        </div>


        {/* SILVER */}

        <div className="rounded-xl border border-slate-800 bg-[#0c1018] p-5">

          <div className="flex items-center justify-between">

            <div>
              <h2 className="text-lg font-semibold text-white">
                Silver
              </h2>

              <p className="mt-1 text-xs text-slate-500">
                Price performance and volatility
              </p>
            </div>

            <TrendBadge trend={data.silver_trend} />

          </div>

          <div className="mt-6 grid grid-cols-2 gap-4">

            <div>
              <div className="text-xs uppercase tracking-wider text-slate-500">
                Price
              </div>

              <div className="mt-1 text-xl font-bold text-white">
                {data.silver_price.toFixed(2)}
              </div>
            </div>

            <div>
              <div className="text-xs uppercase tracking-wider text-slate-500">
                Volatility
              </div>

              <div className="mt-1 text-xl font-bold text-slate-200">
                {data.silver_vol.toFixed(2)}
              </div>
            </div>

          </div>

          <div className="mt-6 border-t border-slate-800 pt-5">

            <div className="mb-4 text-xs uppercase tracking-wider text-slate-500">
              Returns
            </div>

            <div className="grid grid-cols-4 gap-3">

              <div>
                <div className="text-xs text-slate-600">
                  1D
                </div>
                <div className="mt-1">
                  <ReturnValue value={data.silver_returns["1D"]} />
                </div>
              </div>

              <div>
                <div className="text-xs text-slate-600">
                  1W
                </div>
                <div className="mt-1">
                  <ReturnValue value={data.silver_returns["1W"]} />
                </div>
              </div>

              <div>
                <div className="text-xs text-slate-600">
                  1M
                </div>
                <div className="mt-1">
                  <ReturnValue value={data.silver_returns["1M"]} />
                </div>
              </div>

              <div>
                <div className="text-xs text-slate-600">
                  1Y
                </div>
                <div className="mt-1">
                  <ReturnValue value={data.silver_returns["1Y"]} />
                </div>
              </div>

            </div>

          </div>

        </div>

      </section>


      {/* ======================================================
          COMPARISON
      ====================================================== */}

      <section className="rounded-xl border border-slate-800 bg-[#0c1018]">

        <div className="border-b border-slate-800 px-5 py-4">

          <h2 className="text-lg font-semibold text-white">
            Gold vs Silver Performance
          </h2>

          <p className="mt-1 text-xs text-slate-500">
            Comparative returns across multiple timeframes
          </p>

        </div>

        <div className="overflow-x-auto">

          <table className="w-full min-w-[700px] text-sm">

            <thead>
              <tr className="border-b border-slate-800 text-left text-xs uppercase tracking-wider text-slate-500">

                <th className="px-5 py-4">
                  Asset
                </th>

                <th className="px-4 py-4 text-right">
                  1D
                </th>

                <th className="px-4 py-4 text-right">
                  1W
                </th>

                <th className="px-4 py-4 text-right">
                  1M
                </th>

                <th className="px-4 py-4 text-right">
                  1Y
                </th>

                <th className="px-4 py-4 text-right">
                  Volatility
                </th>

                <th className="px-5 py-4">
                  Trend
                </th>

              </tr>
            </thead>

            <tbody>

              <tr className="border-b border-slate-800/70">

                <td className="px-5 py-4 font-semibold text-white">
                  Gold
                </td>

                <td className="px-4 py-4 text-right">
                  <ReturnValue value={data.gold_returns["1D"]} />
                </td>

                <td className="px-4 py-4 text-right">
                  <ReturnValue value={data.gold_returns["1W"]} />
                </td>

                <td className="px-4 py-4 text-right">
                  <ReturnValue value={data.gold_returns["1M"]} />
                </td>

                <td className="px-4 py-4 text-right">
                  <ReturnValue value={data.gold_returns["1Y"]} />
                </td>

                <td className="px-4 py-4 text-right text-slate-300">
                  {data.gold_vol.toFixed(2)}
                </td>

                <td className="px-5 py-4">
                  <TrendBadge trend={data.gold_trend} />
                </td>

              </tr>

              <tr>

                <td className="px-5 py-4 font-semibold text-white">
                  Silver
                </td>

                <td className="px-4 py-4 text-right">
                  <ReturnValue value={data.silver_returns["1D"]} />
                </td>

                <td className="px-4 py-4 text-right">
                  <ReturnValue value={data.silver_returns["1W"]} />
                </td>

                <td className="px-4 py-4 text-right">
                  <ReturnValue value={data.silver_returns["1M"]} />
                </td>

                <td className="px-4 py-4 text-right">
                  <ReturnValue value={data.silver_returns["1Y"]} />
                </td>

                <td className="px-4 py-4 text-right text-slate-300">
                  {data.silver_vol.toFixed(2)}
                </td>

                <td className="px-5 py-4">
                  <TrendBadge trend={data.silver_trend} />
                </td>

              </tr>

            </tbody>

          </table>

        </div>

      </section>


      {/* ======================================================
          MARKET SENTIMENT
      ====================================================== */}

      <section className="rounded-xl border border-slate-800 bg-[#0c1018] p-5">

        <div className="flex flex-wrap items-center justify-between gap-4">

          <div>

            <div className="text-xs uppercase tracking-wider text-slate-500">
              Market Sentiment
            </div>

            <div className="mt-2 text-xl font-bold text-white">
              {data.sentiment}
            </div>

          </div>

          <div className="flex items-center gap-2 rounded-lg border border-slate-700 bg-slate-900 px-4 py-2">

            <TrendingUp
              size={16}
              className="text-cyan-400"
            />

            <span className="text-sm text-slate-300">
              Preferred Asset:
            </span>

            <span className="text-sm font-semibold text-emerald-400">
              {data.better_performer}
            </span>

          </div>

        </div>

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
          Gold-Silver analysis generated from the latest backend run
        </span>

      </div>

    </div>
  );
}