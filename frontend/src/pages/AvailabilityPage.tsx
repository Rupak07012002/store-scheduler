import { useEffect, useState } from "react";
import { createAvailability, deleteAvailability, listAvailability } from "../api/endpoints";
import type { Availability } from "../api/types";
import { useAuth } from "../auth/AuthContext";
import { ApiError } from "../api/client";

const DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"];

export default function AvailabilityPage() {
  const { user } = useAuth();
  const employeeId = user?.linked_employee_id ?? null;
  const [windows, setWindows] = useState<Availability[]>([]);
  const [form, setForm] = useState({ day_of_week: 0, start_time: "08:00", end_time: "22:00" });
  const [error, setError] = useState<string | null>(null);

  async function refresh() {
    if (!employeeId) return;
    setWindows(await listAvailability(employeeId));
  }

  useEffect(() => {
    refresh();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [employeeId]);

  async function handleAdd() {
    if (!employeeId) return;
    setError(null);
    try {
      await createAvailability(employeeId, { ...form, is_available: true });
      await refresh();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to add availability");
    }
  }

  async function handleDelete(id: string) {
    setError(null);
    try {
      await deleteAvailability(id);
      await refresh();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to delete");
    }
  }

  if (!employeeId) {
    return <p className="text-slate-500">Your account isn't linked to an employee record yet.</p>;
  }

  return (
    <div className="space-y-4">
      <h1 className="text-xl font-semibold text-slate-900">My availability</h1>
      {error && <div className="rounded-md bg-red-50 px-3 py-2 text-sm text-red-700">{error}</div>}
      <div className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-slate-200 text-left text-slate-500">
              <th className="py-2">Day</th>
              <th className="py-2">From</th>
              <th className="py-2">To</th>
              <th className="py-2"></th>
            </tr>
          </thead>
          <tbody>
            {windows.map((w) => (
              <tr key={w.id} className="border-b border-slate-100">
                <td className="py-2">{DAYS[w.day_of_week]}</td>
                <td className="py-2">{w.start_time}</td>
                <td className="py-2">{w.end_time}</td>
                <td className="py-2 text-right">
                  <button onClick={() => handleDelete(w.id)} className="text-red-600 hover:underline">
                    Remove
                  </button>
                </td>
              </tr>
            ))}
            {windows.length === 0 && (
              <tr>
                <td colSpan={4} className="py-4 text-center text-slate-400">
                  No availability windows set - add one below.
                </td>
              </tr>
            )}
          </tbody>
        </table>

        <div className="mt-4 flex flex-wrap items-end gap-2 border-t border-slate-100 pt-4">
          <div>
            <label className="block text-xs text-slate-500">Day</label>
            <select
              value={form.day_of_week}
              onChange={(e) => setForm({ ...form, day_of_week: Number(e.target.value) })}
              className="rounded-md border border-slate-300 px-2 py-1 text-sm"
            >
              {DAYS.map((d, i) => (
                <option key={d} value={i}>
                  {d}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-xs text-slate-500">From</label>
            <input
              type="time"
              value={form.start_time}
              onChange={(e) => setForm({ ...form, start_time: e.target.value })}
              className="rounded-md border border-slate-300 px-2 py-1 text-sm"
            />
          </div>
          <div>
            <label className="block text-xs text-slate-500">To</label>
            <input
              type="time"
              value={form.end_time}
              onChange={(e) => setForm({ ...form, end_time: e.target.value })}
              className="rounded-md border border-slate-300 px-2 py-1 text-sm"
            />
          </div>
          <button onClick={handleAdd} className="rounded-md bg-brand-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-brand-700">
            Add availability
          </button>
        </div>
      </div>
    </div>
  );
}
