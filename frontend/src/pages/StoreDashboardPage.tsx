import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { generateSchedule, getForecast, listScheduleRuns, getStore } from "../api/endpoints";
import type { HeadcountRequirement, ScheduleRun, Store } from "../api/types";
import ForecastChart, { nextMonday } from "../components/ForecastChart";
import { ApiError } from "../api/client";

export default function StoreDashboardPage() {
  const { storeId } = useParams<{ storeId: string }>();
  const [store, setStore] = useState<Store | null>(null);
  const [forecast, setForecast] = useState<HeadcountRequirement[]>([]);
  const [runs, setRuns] = useState<ScheduleRun[]>([]);
  const [weekStart, setWeekStart] = useState(nextMonday());
  const [generating, setGenerating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function refresh() {
    if (!storeId) return;
    const [storeData, forecastData, runsData] = await Promise.all([
      getStore(storeId),
      getForecast(storeId, weekStart),
      listScheduleRuns(storeId),
    ]);
    setStore(storeData);
    setForecast(forecastData);
    setRuns(runsData);
  }

  useEffect(() => {
    refresh();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [storeId, weekStart]);

  async function handleGenerate() {
    if (!storeId) return;
    setGenerating(true);
    setError(null);
    try {
      await generateSchedule(storeId, weekStart);
      await refresh();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to generate schedule");
    } finally {
      setGenerating(false);
    }
  }

  if (!store) return <p className="text-slate-500">Loading...</p>;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-semibold text-slate-900">{store.name}</h1>
        <p className="text-sm text-slate-500">{store.address}</p>
      </div>

      <section className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
        <div className="mb-3 flex items-center justify-between">
          <h2 className="font-medium text-slate-900">Footfall forecast &amp; required headcount</h2>
          <div className="flex items-center gap-2">
            <input
              type="date"
              value={weekStart}
              onChange={(e) => setWeekStart(e.target.value)}
              className="rounded-md border border-slate-300 px-2 py-1 text-sm"
            />
            <button
              onClick={handleGenerate}
              disabled={generating}
              className="rounded-md bg-brand-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-brand-700 disabled:opacity-50"
            >
              {generating ? "Generating..." : "Generate schedule for this week"}
            </button>
          </div>
        </div>
        {error && <div className="mb-3 rounded-md bg-red-50 px-3 py-2 text-sm text-red-700">{error}</div>}
        <ForecastChart data={forecast} />
      </section>

      <section className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
        <h2 className="mb-3 font-medium text-slate-900">Schedule runs</h2>
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-slate-200 text-left text-slate-500">
              <th className="py-2">Week</th>
              <th className="py-2">Status</th>
              <th className="py-2">Solver</th>
              <th className="py-2">Shifts</th>
              <th className="py-2"></th>
            </tr>
          </thead>
          <tbody>
            {runs.map((run) => (
              <tr key={run.id} className="border-b border-slate-100">
                <td className="py-2">{run.week_start_date}</td>
                <td className="py-2 capitalize">{run.status.replace("_", " ")}</td>
                <td className="py-2 capitalize">{run.solver_status ?? "-"}</td>
                <td className="py-2">{run.assignments.length}</td>
                <td className="py-2 text-right">
                  <Link to={`/schedules/${run.id}`} className="text-brand-600 hover:underline">
                    Review
                  </Link>
                </td>
              </tr>
            ))}
            {runs.length === 0 && (
              <tr>
                <td colSpan={5} className="py-4 text-center text-slate-400">
                  No schedule runs yet - generate one above.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </section>
    </div>
  );
}
