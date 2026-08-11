import { useEffect, useState } from "react";
import { createTimeOff, listTimeOff } from "../api/endpoints";
import type { TimeOffRequest } from "../api/types";
import { useAuth } from "../auth/AuthContext";
import { ApiError } from "../api/client";

export default function TimeOffPage() {
  const { user } = useAuth();
  const employeeId = user?.linked_employee_id ?? null;
  const [requests, setRequests] = useState<TimeOffRequest[]>([]);
  const [form, setForm] = useState({ start_date: "", end_date: "", reason: "" });
  const [error, setError] = useState<string | null>(null);

  async function refresh() {
    if (!employeeId) return;
    setRequests(await listTimeOff(employeeId));
  }

  useEffect(() => {
    refresh();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [employeeId]);

  async function handleSubmit() {
    if (!employeeId || !form.start_date || !form.end_date) return;
    setError(null);
    try {
      await createTimeOff(employeeId, form);
      setForm({ start_date: "", end_date: "", reason: "" });
      await refresh();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to submit request");
    }
  }

  if (!employeeId) {
    return <p className="text-slate-500">Your account isn't linked to an employee record yet.</p>;
  }

  const statusColor: Record<string, string> = {
    pending: "text-amber-600",
    approved: "text-emerald-600",
    denied: "text-red-600",
  };

  return (
    <div className="space-y-4">
      <h1 className="text-xl font-semibold text-slate-900">Time off requests</h1>
      {error && <div className="rounded-md bg-red-50 px-3 py-2 text-sm text-red-700">{error}</div>}
      <div className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-slate-200 text-left text-slate-500">
              <th className="py-2">From</th>
              <th className="py-2">To</th>
              <th className="py-2">Reason</th>
              <th className="py-2">Status</th>
            </tr>
          </thead>
          <tbody>
            {requests.map((r) => (
              <tr key={r.id} className="border-b border-slate-100">
                <td className="py-2">{r.start_date}</td>
                <td className="py-2">{r.end_date}</td>
                <td className="py-2 text-slate-500">{r.reason ?? "-"}</td>
                <td className={`py-2 font-medium capitalize ${statusColor[r.status]}`}>{r.status}</td>
              </tr>
            ))}
            {requests.length === 0 && (
              <tr>
                <td colSpan={4} className="py-4 text-center text-slate-400">
                  No time-off requests yet.
                </td>
              </tr>
            )}
          </tbody>
        </table>

        <div className="mt-4 flex flex-wrap items-end gap-2 border-t border-slate-100 pt-4">
          <div>
            <label className="block text-xs text-slate-500">From</label>
            <input
              type="date"
              value={form.start_date}
              onChange={(e) => setForm({ ...form, start_date: e.target.value })}
              className="rounded-md border border-slate-300 px-2 py-1 text-sm"
            />
          </div>
          <div>
            <label className="block text-xs text-slate-500">To</label>
            <input
              type="date"
              value={form.end_date}
              onChange={(e) => setForm({ ...form, end_date: e.target.value })}
              className="rounded-md border border-slate-300 px-2 py-1 text-sm"
            />
          </div>
          <div className="flex-1">
            <label className="block text-xs text-slate-500">Reason (optional)</label>
            <input
              type="text"
              value={form.reason}
              onChange={(e) => setForm({ ...form, reason: e.target.value })}
              className="w-full rounded-md border border-slate-300 px-2 py-1 text-sm"
            />
          </div>
          <button onClick={handleSubmit} className="rounded-md bg-brand-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-brand-700">
            Request time off
          </button>
        </div>
      </div>
    </div>
  );
}
