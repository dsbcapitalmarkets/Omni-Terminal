import { useEffect, useState } from "react";

interface SmartMoneyHistory {
  date: string;
  fii_buy: number;
  fii_sell: number;
  fii_net: number;
  dii_buy: number;
  dii_sell: number;
  dii_net: number;
}

interface SmartMoneyData {
  timestamp: string;
  status: string;
  latest: {
    date: string;
    fii_buy: number;
    fii_sell: number;
    fii_net: number;
    dii_buy: number;
    dii_sell: number;
    dii_net: number;
    signal: string;
  };
  history: SmartMoneyHistory[];
}

const API_BASE_URL = "http://127.0.0.1:8000";

function formatNumber(value: number): string {
  return value.toLocaleString("en-IN", {
    maximumFractionDigits: 2,
  });
}

function getNetClass(value: number): string {
  if (value > 0) return "text-emerald-400";
  if (value < 0) return "text-red-400";
  return "text-slate-400";
}

export default function SmartMoney() {
  const [data, setData] = useState<SmartMoneyData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let mounted = true;

    async function loadData() {
      try {
        setLoading(true);
        setError(null);

        const response = await fetch(
          `${API_BASE_URL}/api/smart-money`
        );

        if (!response.ok) {
          throw new Error(
            `API request failed with status ${response.status}`
          );
        }

        const result: SmartMoneyData = await response.json();

        if (mounted) {
          setData(result);
        }
      } catch (err) {
        if (mounted) {
          setError(
            err instanceof Error
              ? err.message
              : "Failed to load Smart Money data."
          );
        }
      } finally {
        if (mounted) {
          setLoading(false);
        }
      }
    }

    loadData();

    return () => {
      mounted = false;
    };
  }, []);

  if (loading) {
    return (
      <div className="min-h-full p-6">
        <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-8 text-center">
          <div className="text-sm text-slate-400">
            Loading Smart Money data...
          </div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-full p-6">
        <div className="rounded-xl border border-red-500/30 bg-red-500/10 p-6">
          <h1 className="text-lg font-semibold text-red-400">
            Smart Money
          </h1>

          <p className="mt-2 text-sm text-slate-400">
            Failed to load data from FastAPI.
          </p>

          <p className="mt-3 break-all text-xs text-red-300">
            {error}
          </p>
        </div>
      </div>
    );
  }

  if (!data || !data.latest) {
    return (
      <div className="min-h-full p-6">
        <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-8 text-center">
          <div className="text-sm text-slate-400">
            No Smart Money data available.
          </div>
        </div>
      </div>
    );
  }

  const latest = data.latest;

  return (
    <div className="min-h-full space-y-6 p-6">
      <div>
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h1 className="text-2xl font-bold tracking-tight text-white">
              Smart Money
            </h1>

            <p className="mt-1 text-sm text-slate-400">
              FII & DII institutional activity
            </p>
          </div>

          <div className="text-right">
            <div className="text-xs uppercase tracking-wide text-slate-500">
              Data Updated
            </div>

            <div className="mt-1 text-sm text-slate-300">
              {data.timestamp}
            </div>
          </div>
        </div>
      </div>

      <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-5">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div>
            <div className="text-xs font-medium uppercase tracking-wider text-slate-500">
              Latest Signal
            </div>

            <div className="mt-2 text-lg font-semibold text-white">
              {latest.signal}
            </div>

            <div className="mt-1 text-sm text-slate-400">
              Trading date: {latest.date}
            </div>
          </div>

          <div className="rounded-lg border border-slate-700 bg-slate-950/50 px-4 py-3 text-center">
            <div className="text-xs uppercase tracking-wide text-slate-500">
              Status
            </div>

            <div className="mt-1 text-sm font-semibold text-emerald-400">
              {data.status.toUpperCase()}
            </div>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
        <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-5">
          <div>
            <div className="text-xs font-medium uppercase tracking-wider text-slate-500">
              FII
            </div>

            <div className="mt-1 text-lg font-semibold text-white">
              Foreign Institutional Investors
            </div>
          </div>

          <div className="mt-6">
            <div className="text-xs uppercase tracking-wide text-slate-500">
              Net Flow
            </div>

            <div
              className={`mt-1 text-3xl font-bold ${getNetClass(
                latest.fii_net
              )}`}
            >
              {formatNumber(latest.fii_net)}
            </div>
          </div>

          <div className="mt-6 grid grid-cols-2 gap-3">
            <div className="rounded-lg bg-slate-950/50 p-3">
              <div className="text-xs text-slate-500">
                Buy
              </div>

              <div className="mt-1 font-semibold text-slate-200">
                {formatNumber(latest.fii_buy)}
              </div>
            </div>

            <div className="rounded-lg bg-slate-950/50 p-3">
              <div className="text-xs text-slate-500">
                Sell
              </div>

              <div className="mt-1 font-semibold text-slate-200">
                {formatNumber(latest.fii_sell)}
              </div>
            </div>
          </div>
        </div>

        <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-5">
          <div>
            <div className="text-xs font-medium uppercase tracking-wider text-slate-500">
              DII
            </div>

            <div className="mt-1 text-lg font-semibold text-white">
              Domestic Institutional Investors
            </div>
          </div>

          <div className="mt-6">
            <div className="text-xs uppercase tracking-wide text-slate-500">
              Net Flow
            </div>

            <div
              className={`mt-1 text-3xl font-bold ${getNetClass(
                latest.dii_net
              )}`}
            >
              {formatNumber(latest.dii_net)}
            </div>
          </div>

          <div className="mt-6 grid grid-cols-2 gap-3">
            <div className="rounded-lg bg-slate-950/50 p-3">
              <div className="text-xs text-slate-500">
                Buy
              </div>

              <div className="mt-1 font-semibold text-slate-200">
                {formatNumber(latest.dii_buy)}
              </div>
            </div>

            <div className="rounded-lg bg-slate-950/50 p-3">
              <div className="text-xs text-slate-500">
                Sell
              </div>

              <div className="mt-1 font-semibold text-slate-200">
                {formatNumber(latest.dii_sell)}
              </div>
            </div>
          </div>
        </div>
      </div>

      <div className="rounded-xl border border-slate-800 bg-slate-900/60">
        <div className="border-b border-slate-800 p-5">
          <h2 className="text-lg font-semibold text-white">
            Institutional Flow History
          </h2>

          <p className="mt-1 text-sm text-slate-500">
            Daily FII and DII buying, selling and net flow
          </p>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full min-w-[900px] text-sm">
            <thead>
              <tr className="border-b border-slate-800 text-left text-xs uppercase tracking-wider text-slate-500">
                <th className="px-5 py-3 font-medium">
                  Date
                </th>

                <th className="px-5 py-3 text-right font-medium">
                  FII Buy
                </th>

                <th className="px-5 py-3 text-right font-medium">
                  FII Sell
                </th>

                <th className="px-5 py-3 text-right font-medium">
                  FII Net
                </th>

                <th className="px-5 py-3 text-right font-medium">
                  DII Buy
                </th>

                <th className="px-5 py-3 text-right font-medium">
                  DII Sell
                </th>

                <th className="px-5 py-3 text-right font-medium">
                  DII Net
                </th>
              </tr>
            </thead>

            <tbody>
              {data.history.map((row) => (
                <tr
                  key={row.date}
                  className="border-b border-slate-800/60 last:border-0 hover:bg-slate-800/30"
                >
                  <td className="whitespace-nowrap px-5 py-3 text-slate-300">
                    {row.date}
                  </td>

                  <td className="px-5 py-3 text-right text-slate-300">
                    {formatNumber(row.fii_buy)}
                  </td>

                  <td className="px-5 py-3 text-right text-slate-300">
                    {formatNumber(row.fii_sell)}
                  </td>

                  <td
                    className={`px-5 py-3 text-right font-semibold ${getNetClass(
                      row.fii_net
                    )}`}
                  >
                    {formatNumber(row.fii_net)}
                  </td>

                  <td className="px-5 py-3 text-right text-slate-300">
                    {formatNumber(row.dii_buy)}
                  </td>

                  <td className="px-5 py-3 text-right text-slate-300">
                    {formatNumber(row.dii_sell)}
                  </td>

                  <td
                    className={`px-5 py-3 text-right font-semibold ${getNetClass(
                      row.dii_net
                    )}`}
                  >
                    {formatNumber(row.dii_net)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}