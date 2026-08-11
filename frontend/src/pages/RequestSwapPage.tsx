import { useEffect, useState } from "react";
import { listEmployees, listScheduleRuns, listShiftTemplates, myShifts, requestSwap } from "../api/endpoints";
import type { Employee, ShiftAssignment, ShiftTemplate } from "../api/types";
import { useAuth } from "../auth/AuthContext";
import { ApiError } from "../api/client";

export default function RequestSwapPage() {
  const { user } = useAuth();
  const [myOwnShifts, setMyOwnShifts] = useState<ShiftAssignment[]>([]);
  const [otherShifts, setOtherShifts] = useState<ShiftAssignment[]>([]);
  const [employees, setEmployees] = useState<Employee[]>([]);
  const [templates, setTemplates] = useState<ShiftTemplate[]>([]);
  const [sourceId, setSourceId] = useState("");
  const [targetId, setTargetId] = useState("");
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!user?.store_id) return;
    Promise.all([
      myShifts(),
      listScheduleRuns(user.store_id),
      listEmployees(user.store_id),
      listShiftTemplates(user.store_id),
    ]).then(([mine, runs, emps, tmpls]) => {
      setMyOwnShifts(mine);
      const others = runs
        .filter((r) => r.status === "published")
        .flatMap((r) => r.assignments)
        .filter((a) => a.employee_id !== user.linked_employee_id && a.status === "published");
      setOtherShifts(others);
      setEmployees(emps);
      setTemplates(tmpls);
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [user?.store_id]);

  const employeeName = (id: string) => employees.find((e) => e.id === id)?.full_name ?? id.slice(0, 8);
  const templateName = (id: string) => templates.find((t) => t.id === id)?.name ?? id.slice(0, 8);

  async function handleSubmit() {
    if (!sourceId || !targetId) return;
    setError(null);
    setMessage(null);
    try {
      await requestSwap({ source_assignment_id: sourceId, target_assignment_id: targetId });
      setMessage("Swap request submitted - your manager will review it.");
      setSourceId("");
      setTargetId("");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to submit swap request");
    }
  }

  return (
    <div className="space-y-4">
      <h1 className="text-xl font-semibold text-slate-900">Request a shift swap</h1>
      {message && <div className="rounded-md bg-emerald-50 px-3 py-2 text-sm text-emerald-700">{message}</div>}
      {error && <div className="rounded-md bg-red-50 px-3 py-2 text-sm text-red-700">{error}</div>}
      <div className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
        <div className="grid gap-4 sm:grid-cols-2">
          <div>
            <label className="block text-sm font-medium text-slate-700">Your shift to give up</label>
            <select
              value={sourceId}
              onChange={(e) => setSourceId(e.target.value)}
              className="mt-1 w-full rounded-md border border-slate-300 px-2 py-2 text-sm"
            >
              <option value="">Select...</option>
              {myOwnShifts.map((s) => (
                <option key={s.id} value={s.id}>
                  {s.date} &middot; {templateName(s.shift_template_id)}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-700">Shift you want instead</label>
            <select
              value={targetId}
              onChange={(e) => setTargetId(e.target.value)}
              className="mt-1 w-full rounded-md border border-slate-300 px-2 py-2 text-sm"
            >
              <option value="">Select...</option>
              {otherShifts.map((s) => (
                <option key={s.id} value={s.id}>
                  {s.date} &middot; {templateName(s.shift_template_id)} &middot; {employeeName(s.employee_id)}
                </option>
              ))}
            </select>
          </div>
        </div>
        <button
          onClick={handleSubmit}
          disabled={!sourceId || !targetId}
          className="mt-4 rounded-md bg-brand-600 px-4 py-2 text-sm font-medium text-white hover:bg-brand-700 disabled:opacity-50"
        >
          Submit swap request
        </button>
      </div>
    </div>
  );
}
