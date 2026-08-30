import { useEffect, useState, type ReactNode } from "react";
import {
  BarChart3,
  TrendingDown,
  TrendingUp,
  Activity,
} from "lucide-react";
import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
} from "recharts";


// ============================================================
// TYPES
// ============================================================

interface BreadthHistory {
  date: string;
  num_above_50: number;
  pct_above_50: number;
  num_above_200: number;
  pct_above_200: number;
  advances: number;
  declines: number;
  ad_ratio: number;
  nh_nl_spread: number;
  regime: string;
}

interface BreadthData {
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
  history: BreadthHistory[];
}


// ============================================================
// API
// ============================================================

const API_URL = "/api/market-breadth";


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
  icon: ReactNode;
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

      <div className="mt-3 text-2xl font-bold tracking-tight">
        {value}
      </div>

      <div className="mt-1 text-xs text-slate-500">
        {subtitle}
      </div>
    </div>
  );
}


// ============================================================
// MARKET BREADTH
// ============================================================

function MarketBreadth() {
  const [data, setData] = useState<BreadthData | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);


  // ==========================================================
  // FETCH DATA FROM FASTAPI
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

        const json: BreadthData = await response.json();

        if (json.status !== "ok") {
          throw new Error(
            "API returned an error while loading market breadth data"
          );
        }

        setData(json);
      } catch (err) {
        console.error("Market Breadth API error:", err);

        if (err instanceof Error) {
          setError(err.message);
        } else {
          setError("Failed to load market breadth data");
        }
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
      <div className="flex min-h-[400px] items-center justify-center">
        <div className="text-sm text-slate-500">
          Loading Market Breadth...
        </div>
      </div>
    );
  }


  // ==========================================================
  // ERROR
  // ==========================================================

  if (error || !data) {
    return (
      <div>
        <div className="mb-6">
          <p className="mb-1 text-xs font-medium uppercase tracking-widest text-cyan-400">
            Analytics
          </p>

          <h2 className="text-3xl font-bold tracking-tight">
            Market Breadth
          </h2>

          <p className="mt-2 text-sm text-red-400">
            Failed to load data from FastAPI.
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
    <div>

      {/* ======================================================
          PAGE HEADING
      ====================================================== */}

      <div className="mb-6">
        <p className="mb-1 text-xs font-medium uppercase tracking-widest text-cyan-400">
          Analytics
        </p>

        <div className="flex flex-wrap items-end justify-between gap-3">
          <div>
            <h2 className="text-3xl font-bold tracking-tight">
              Market Breadth
            </h2>

            <p className="mt-2 text-sm text-slate-500">
              Market participation, advances, declines and breadth indicators
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
          REGIME
      ====================================================== */}

      <div className="mb-6 rounded-xl border border-slate-800 bg-[#0c1018] p-5">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div>
            <div className="text-xs uppercase tracking-wider text-slate-500">
              Current Market Regime
            </div>

            <div className="mt-2 text-2xl font-bold">
              {data.regime}
            </div>
          </div>

          <div className="rounded-lg bg-slate-900 px-4 py-3 text-right">
            <div className="text-xs text-slate-500">
              A/D Ratio
            </div>

            <div className="mt-1 text-xl font-bold">
              {data.ad_ratio.toFixed(2)}
            </div>
          </div>
        </div>
      </div>


      {/* ======================================================
          PRIMARY METRICS
      ====================================================== */}

      <section className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">

        <MetricCard
          title="Advances"
          value={data.advances.toString()}
          subtitle={`${data.advances} stocks advanced`}
          icon={<TrendingUp size={18} />}
        />

        <MetricCard
          title="Declines"
          value={data.declines.toString()}
          subtitle={`${data.declines} stocks declined`}
          icon={<TrendingDown size={18} />}
        />

        <MetricCard
          title="Above 50 DMA"
          value={`${data.pct_above_50.toFixed(2)}%`}
          subtitle={`${data.num_above_50} stocks`}
          icon={<BarChart3 size={18} />}
        />

        <MetricCard
          title="Above 200 DMA"
          value={`${data.pct_above_200.toFixed(2)}%`}
          subtitle={`${data.num_above_200} stocks`}
          icon={<Activity size={18} />}
        />

      </section>


      {/* ======================================================
          SECONDARY METRICS
      ====================================================== */}

      <section className="mt-6 grid gap-4 sm:grid-cols-2 xl:grid-cols-4">

        <MetricCard
          title="Unchanged"
          value={data.unchanged.toString()}
          subtitle="Stocks unchanged"
          icon={<Activity size={18} />}
        />

        <MetricCard
          title="New Highs"
          value={data.new_highs.toString()}
          subtitle="52-week highs"
          icon={<TrendingUp size={18} />}
        />

        <MetricCard
          title="New Lows"
          value={data.new_lows.toString()}
          subtitle="52-week lows"
          icon={<TrendingDown size={18} />}
        />

        <MetricCard
          title="NH-NL Spread"
          value={data.nh_nl_spread.toString()}
          subtitle="New highs minus new lows"
          icon={<BarChart3 size={18} />}
        />

      </section>


      {/* ======================================================
          CHARTS
      ====================================================== */}

      <section className="mt-6 grid gap-4 xl:grid-cols-2">


        {/* ====================================================
            50 DMA
        ==================================================== */}

        <div className="rounded-xl border border-slate-800 bg-[#0c1018] p-5">

          <div className="mb-5">
            <h3 className="font-semibold">
              Stocks Above 50 DMA
            </h3>

            <p className="mt-1 text-xs text-slate-500">
              Percentage of stocks trading above their 50-day moving average
            </p>
          </div>

          <div className="h-[300px]">

            <ResponsiveContainer width="100%" height="100%">

              <LineChart data={data.history}>

                <CartesianGrid
                  strokeDasharray="3 3"
                  stroke="#1e293b"
                />

                <XAxis
                  dataKey="date"
                  tick={{ fill: "#64748b", fontSize: 10 }}
                  tickLine={false}
                  axisLine={false}
                />

                <YAxis
                  domain={[40, 60]}
                  tick={{ fill: "#64748b", fontSize: 10 }}
                  tickLine={false}
                  axisLine={false}
                  tickFormatter={(value: number) => `${value}%`}
                />

                <Tooltip
                  contentStyle={{
                    backgroundColor: "#0c1018",
                    border: "1px solid #1e293b",
                    borderRadius: "8px",
                    color: "#f8fafc",
                  }}
                  formatter={(value) => [
                    `${Number(value).toFixed(2)}%`,
                    "Above 50 DMA",
                  ]}
                />

                <Line
                  type="monotone"
                  dataKey="pct_above_50"
                  stroke="#22d3ee"
                  strokeWidth={2}
                  dot={false}
                />

              </LineChart>

            </ResponsiveContainer>

          </div>
        </div>


        {/* ====================================================
            200 DMA
        ==================================================== */}

        <div className="rounded-xl border border-slate-800 bg-[#0c1018] p-5">

          <div className="mb-5">
            <h3 className="font-semibold">
              Stocks Above 200 DMA
            </h3>

            <p className="mt-1 text-xs text-slate-500">
              Percentage of stocks trading above their 200-day moving average
            </p>
          </div>

          <div className="h-[300px]">

            <ResponsiveContainer width="100%" height="100%">

              <LineChart data={data.history}>

                <CartesianGrid
                  strokeDasharray="3 3"
                  stroke="#1e293b"
                />

                <XAxis
                  dataKey="date"
                  tick={{ fill: "#64748b", fontSize: 10 }}
                  tickLine={false}
                  axisLine={false}
                />

                <YAxis
                  domain={[50, 70]}
                  tick={{ fill: "#64748b", fontSize: 10 }}
                  tickLine={false}
                  axisLine={false}
                  tickFormatter={(value: number) => `${value}%`}
                />

                <Tooltip
                  contentStyle={{
                    backgroundColor: "#0c1018",
                    border: "1px solid #1e293b",
                    borderRadius: "8px",
                    color: "#f8fafc",
                  }}
                  formatter={(value) => [
                    `${Number(value).toFixed(2)}%`,
                    "Above 200 DMA",
                  ]}
                />

                <Line
                  type="monotone"
                  dataKey="pct_above_200"
                  stroke="#a78bfa"
                  strokeWidth={2}
                  dot={false}
                />

              </LineChart>

            </ResponsiveContainer>

          </div>
        </div>

      </section>


      {/* ======================================================
          A/D HISTORY
      ====================================================== */}

      <section className="mt-6 rounded-xl border border-slate-800 bg-[#0c1018] p-5">

        <div className="mb-5">

          <h3 className="font-semibold">
            Advance / Decline History
          </h3>

          <p className="mt-1 text-xs text-slate-500">
            Daily market participation over the recent sessions
          </p>

        </div>


        <div className="overflow-x-auto">

          <table className="w-full min-w-[700px] text-sm">

            <thead>

              <tr className="border-b border-slate-800 text-left text-xs uppercase tracking-wider text-slate-500">

                <th className="px-4 py-3">
                  Date
                </th>

                <th className="px-4 py-3 text-right">
                  Advances
                </th>

                <th className="px-4 py-3 text-right">
                  Declines
                </th>

                <th className="px-4 py-3 text-right">
                  A/D Ratio
                </th>

                <th className="px-4 py-3 text-right">
                  NH-NL
                </th>

                <th className="px-4 py-3 text-right">
                  Above 50
                </th>

                <th className="px-4 py-3 text-right">
                  Above 200
                </th>

              </tr>

            </thead>


            <tbody>

              {data.history.map((row) => (

                <tr
                  key={row.date}
                  className="border-b border-slate-800/60 hover:bg-slate-900/50"
                >

                  <td className="px-4 py-3 text-slate-300">
                    {row.date}
                  </td>

                  <td className="px-4 py-3 text-right text-emerald-400">
                    {row.advances}
                  </td>

                  <td className="px-4 py-3 text-right text-red-400">
                    {row.declines}
                  </td>

                  <td
                    className={`px-4 py-3 text-right font-medium ${
                      row.ad_ratio >= 1
                        ? "text-emerald-400"
                        : "text-red-400"
                    }`}
                  >
                    {row.ad_ratio.toFixed(2)}
                  </td>

                  <td
                    className={`px-4 py-3 text-right font-medium ${
                      row.nh_nl_spread > 0
                        ? "text-emerald-400"
                        : row.nh_nl_spread < 0
                          ? "text-red-400"
                          : "text-slate-400"
                    }`}
                  >
                    {row.nh_nl_spread}
                  </td>

                  <td className="px-4 py-3 text-right text-slate-300">
                    {row.pct_above_50.toFixed(2)}%
                  </td>

                  <td className="px-4 py-3 text-right text-slate-300">
                    {row.pct_above_200.toFixed(2)}%
                  </td>

                </tr>

              ))}

            </tbody>

          </table>

        </div>

      </section>

    </div>
  );
}


export default MarketBreadth;