import { useEffect, useState } from "react";
import {
  CalendarDays,
  TrendingUp,
  BarChart3,
  Building2,
  ExternalLink,
} from "lucide-react";

// ============================================================
// TYPES
// ============================================================

interface EarningsResult {
  symbol: string;
  company: string;
  date: string;
  purpose: string;
  purpose_label: string;
  category: string;
  series: string;
}

interface EarningsCounts {
  quarterly: number;
  annual: number;
  board: number;
}

interface EarningsData {
  timestamp: string;
  status: string;
  today_count: number;
  upcoming_count: number;
  today_counts: EarningsCounts;
  upcoming_counts: EarningsCounts;
  today_results: EarningsResult[];
  upcoming_results: EarningsResult[];
  screener_url: string;
}

// ============================================================
// API
// ============================================================

const API_URL = "http://127.0.0.1:8000/api/earnings";

// ============================================================
// HELPERS
// ============================================================

function getCategoryClass(category: string) {
  switch (category?.toLowerCase()) {
    case "quarterly":
      return "text-cyan-400 bg-cyan-400/10 border-cyan-400/20";

    case "annual":
      return "text-violet-400 bg-violet-400/10 border-violet-400/20";

    case "board":
      return "text-orange-400 bg-orange-400/10 border-orange-400/20";

    default:
      return "text-slate-300 bg-slate-400/10 border-slate-400/20";
  }
}

function getDaysUntil(dateString: string) {
  const resultDate = new Date(dateString);
  const today = new Date("2026-08-30");

  resultDate.setHours(0, 0, 0, 0);
  today.setHours(0, 0, 0, 0);

  const diff =
    resultDate.getTime() - today.getTime();

  return Math.round(diff / (1000 * 60 * 60 * 24));
}

function formatDays(days: number) {
  if (days < 0) {
    return `${Math.abs(days)}d ago`;
  }

  if (days === 0) {
    return "Today";
  }

  if (days === 1) {
    return "Tomorrow";
  }

  return `${days} days`;
}

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
// EARNINGS
// ============================================================

export default function Earnings() {
  const [data, setData] = useState<EarningsData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // ==========================================================
  // FETCH
  // ==========================================================

  useEffect(() => {
    const fetchEarnings = async () => {
      try {
        setLoading(true);
        setError(null);

        const response = await fetch(API_URL);

        if (!response.ok) {
          throw new Error(
            `API request failed with status ${response.status}`
          );
        }

        const json: EarningsData = await response.json();

        if (json?.status === "error") {
          throw new Error(
            "Backend returned an error while loading earnings"
          );
        }

        setData(json);
      } catch (err) {
        console.error("Earnings API error:", err);

        setError(
          err instanceof Error
            ? err.message
            : "Failed to load earnings data"
        );
      } finally {
        setLoading(false);
      }
    };

    fetchEarnings();
  }, []);

  // ==========================================================
  // LOADING
  // ==========================================================

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

  // ==========================================================
  // ERROR
  // ==========================================================

  if (error) {
    return (
      <div className="min-h-full p-6">
        <div className="rounded-xl border border-red-500/20 bg-red-500/10 p-6">
          <h2 className="text-lg font-semibold text-red-400">
            Unable to load Earnings
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

  // ==========================================================
  // NO DATA
  // ==========================================================

  if (!data) {
    return (
      <div className="min-h-full p-6">
        <div className="rounded-xl border border-slate-800 bg-slate-900 p-6 text-slate-400">
          No earnings data available.
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
              Calendar
            </p>

            <h1 className="text-3xl font-bold tracking-tight text-white">
              Earnings
            </h1>

            <p className="mt-2 text-sm text-slate-500">
              Upcoming corporate results and earnings calendar
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
          SUMMARY
      ====================================================== */}

      <section className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">

        <MetricCard
          title="Today"
          value={data.today_count.toString()}
          subtitle="Results scheduled today"
          icon={<CalendarDays size={18} />}
        />

        <MetricCard
          title="Upcoming"
          value={data.upcoming_count.toString()}
          subtitle="Upcoming results"
          icon={<TrendingUp size={18} />}
        />

        <MetricCard
          title="Quarterly"
          value={data.upcoming_counts.quarterly.toString()}
          subtitle="Upcoming quarterly results"
          icon={<BarChart3 size={18} />}
        />

        <MetricCard
          title="Annual / Board"
          value={(
            data.upcoming_counts.annual +
            data.upcoming_counts.board
          ).toString()}
          subtitle={`${data.upcoming_counts.annual} annual · ${data.upcoming_counts.board} board`}
          icon={<Building2 size={18} />}
        />

      </section>

      {/* ======================================================
          UPCOMING RESULTS
      ====================================================== */}

      <section className="overflow-hidden rounded-xl border border-slate-800 bg-[#0c1018]">

        <div className="border-b border-slate-800 px-5 py-4">

          <div className="flex flex-wrap items-center justify-between gap-3">

            <div>
              <h2 className="text-lg font-semibold text-white">
                Upcoming Results
              </h2>

              <p className="mt-1 text-xs text-slate-500">
                Companies with scheduled corporate results
              </p>
            </div>

            <div className="rounded-lg border border-slate-700 bg-slate-800/50 px-3 py-1.5 text-xs text-slate-300">
              {data.upcoming_count} Result
              {data.upcoming_count === 1 ? "" : "s"}
            </div>

          </div>

        </div>

        {data.upcoming_results.length === 0 ? (

          <div className="px-5 py-12 text-center text-sm text-slate-500">
            No upcoming earnings results available.
          </div>

        ) : (

          <div className="overflow-x-auto">

            <table className="w-full min-w-[900px] text-sm">

              <thead>

                <tr className="border-b border-slate-800 text-left text-xs uppercase tracking-wider text-slate-500">

                  <th className="px-5 py-4">
                    Company
                  </th>

                  <th className="px-4 py-4">
                    Symbol
                  </th>

                  <th className="px-4 py-4">
                    Result Date
                  </th>

                  <th className="px-4 py-4">
                    Category
                  </th>

                  <th className="px-4 py-4">
                    Purpose
                  </th>

                  <th className="px-5 py-4">
                    Timing
                  </th>

                </tr>

              </thead>

              <tbody>

                {data.upcoming_results.map(
                  (result, index) => {

                    const days = getDaysUntil(result.date);

                    return (
                      <tr
                        key={`${result.symbol}-${result.date}-${index}`}
                        className="border-b border-slate-800/70 transition-colors hover:bg-slate-800/30"
                      >

                        {/* Company */}

                        <td className="px-5 py-4">

                          <div className="font-semibold text-white">
                            {result.company}
                          </div>

                          <div className="mt-1 text-xs text-slate-600">
                            Series {result.series}
                          </div>

                        </td>

                        {/* Symbol */}

                        <td className="px-4 py-4">

                          <span className="font-medium text-cyan-400">
                            {result.symbol}
                          </span>

                        </td>

                        {/* Date */}

                        <td className="px-4 py-4">

                          <div className="font-medium text-slate-200">
                            {result.date}
                          </div>

                        </td>

                        {/* Category */}

                        <td className="px-4 py-4">

                          <span
                            className={`inline-flex rounded-md border px-2.5 py-1 text-xs font-semibold ${getCategoryClass(
                              result.category
                            )}`}
                          >
                            {result.category}
                          </span>

                        </td>

                        {/* Purpose */}

                        <td className="px-4 py-4 text-slate-300">

                          <div className="flex items-center gap-2">
                            <span>
                              {result.purpose_label}
                            </span>
                          </div>

                        </td>

                        {/* Timing */}

                        <td className="px-5 py-4">

                          <span
                            className={`font-medium ${
                              days === 0
                                ? "text-cyan-400"
                                : days === 1
                                  ? "text-yellow-400"
                                  : days < 0
                                    ? "text-slate-500"
                                    : "text-emerald-400"
                            }`}
                          >
                            {formatDays(days)}
                          </span>

                        </td>

                      </tr>
                    );
                  }
                )}

              </tbody>

            </table>

          </div>

        )}

      </section>

      {/* ======================================================
          TODAY
      ====================================================== */}

      <section className="grid grid-cols-1 gap-4 lg:grid-cols-3">

        <div className="rounded-xl border border-slate-800 bg-[#0c1018] p-5">

          <div className="text-xs uppercase tracking-wider text-slate-500">
            Today's Results
          </div>

          <div className="mt-2 text-2xl font-bold text-white">
            {data.today_count}
          </div>

          <div className="mt-1 text-xs text-slate-500">
            Scheduled corporate events
          </div>

        </div>

        <div className="rounded-xl border border-slate-800 bg-[#0c1018] p-5">

          <div className="text-xs uppercase tracking-wider text-slate-500">
            Quarterly
          </div>

          <div className="mt-2 text-2xl font-bold text-cyan-400">
            {data.today_counts.quarterly}
          </div>

          <div className="mt-1 text-xs text-slate-500">
            Quarterly results today
          </div>

        </div>

        <div className="rounded-xl border border-slate-800 bg-[#0c1018] p-5">

          <div className="text-xs uppercase tracking-wider text-slate-500">
            Annual / Board
          </div>

          <div className="mt-2 text-2xl font-bold text-violet-400">
            {data.today_counts.annual +
              data.today_counts.board}
          </div>

          <div className="mt-1 text-xs text-slate-500">
            Other corporate events today
          </div>

        </div>

      </section>

      {/* ======================================================
          SCREENER LINK
      ====================================================== */}

      <div className="flex flex-wrap items-center justify-between gap-3 text-xs text-slate-500">

        <div>
          Data status:{" "}
          <span className="font-medium text-emerald-400">
            {data.status.toUpperCase()}
          </span>
        </div>

        <a
          href={data.screener_url}
          target="_blank"
          rel="noopener noreferrer"
          className="inline-flex items-center gap-2 rounded-lg border border-slate-700 bg-slate-800/50 px-3 py-2 text-slate-300 transition hover:bg-slate-800 hover:text-white"
        >
          View Screener Results
          <ExternalLink size={14} />
        </a>

      </div>

    </div>
  );
}