import { useEffect, useMemo, useState } from "react";
import { useParams } from "react-router-dom";
import {
  addAssignment,
  getComplianceFlags,
  getScheduleRun,
  getStore,
  listEmployees,
  listShiftTemplates,
  publishSchedule,
  removeAssignment,
} from "../api/endpoints";
import type { ComplianceFlag, Employee, ScheduleRun, ShiftTemplate, Store } from "../api/types";
import { ApiError } from "../api/client";

export default function ScheduleReviewPage() {
  const { runId } = useParams<{ runId: string }>();
  const [run, setRun] = useState<ScheduleRun | null>(null);
  const [store, setStore] = useState<Store | null>(null);
  const [employees, setEmployees] = useState<Employee[]>([]);
  const [templates, setTemplates] = useState<ShiftTemplate[]>([]);
  const [flags, setFlags] = useState<ComplianceFlag[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [addForm, setAddForm] = useState({ employee_id: "", shift_template_id: "", date: "" });

  async function refresh() {
    if (!runId) return;
    const r = await getScheduleRun(runId);
    setRun(r);
    const [storeData, emps, tmpls, flagData] = await Promise.all([
      getStore(r.store_id),
      listEmployees(r.store_id),
      listShiftTemplates(r.store_id),
      getComplianceFlags(runId).catch(() => []),
    ]);
    setStore(storeData);
    setEmployees(emps);
    setTemplates(tmpls);
    setFlags(flagData);
  }

  useEffect(() => {
    refresh();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [runId]);

  const employeeName = (id: string) => employees.find((e) => e.id === id)?.full_name ?? id.slice(0, 8);
  const templateName = (id: string) => templates.find((t) => t.id === id)?.name ?? id.slice(0, 8);

  const totalHours = useMemo(() => {
    if (!run) return 0;
    return run.assignments.reduce((sum, a) => {
      const t = templates.find((tt) => tt.id === a.shift_template_id);
      if (!t) return sum;
      const [sh, sm] = t.start_time.split(":").map(Number);
      const [eh, em] = t.end_time.split(":").map(Number);
      return sum + (eh * 60 + em - (sh * 60 + sm)) / 60;
    }, 0);
  }, [run, templates]);

  async function handlePublish() {
    if (!runId) return;
    setError(null);
    try {
      await publishSchedule(runId);
      await refresh();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to publish");
    }
  }

  async function handleRemove(assignmentId: string) {
    if (!runId) return;
    setError(null);
    try {
      await removeAssignment(runId, assignmentId);
      await refresh();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to remove assignment");
    }
  }

  async function handleAdd() {
    if (!runId || !addForm.employee_id || !addForm.shift_template_id || !addForm.date) return;
    setError(null);
    try {
      await addAssignment(runId, addForm);
      setAddForm({ employee_id: "", shift_template_id: "", date: "" });
      await refresh();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to add assignment");
    }
  }

  if (!run || !store) return <p className="text-slate-500">Loading...</p>;

  const hardFlags = flags.filter((f) => f.severity === "hard" && !f.resolved);
  const softFlags = flags.filter((f) => f.severity === "soft" && !f.resolved);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold text-slate-900">
            {store.name} &middot; Week of {run.week_start_date}
          </h1>
          <p className="text-sm capitalize text-slate-500">
            Status: {run.status.replace("_", " ")} &middot; Solver: {run.solver_status ?? "n/a"}
          </p>
        </div>
        {run.status !== "published" && (
          <button
            onClick={handlePublish}
            disabled={hardFlags.length > 0}
            className="rounded-md bg-brand-600 px-4 py-2 text-sm font-medium text-white hover:bg-brand-700 disabled:cursor-not-allowed disabled:opacity-40"
            title={hardFlags.length > 0 ? "Resolve hard compliance flags before publishing" : ""}
          >
            Publish schedule
          </button>
        )}
      </div>

      {error && <div className="rounded-md bg-red-50 px-3 py-2 text-sm text-red-700">{error}</div>}

      <section className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
        <h2 className="mb-2 font-medium text-slate-900">Compliance</h2>
        {flags.length === 0 && <p className="text-sm text-emerald-600">No compliance issues.</p>}
        {hardFlags.map((f) => (
          <div key={f.id} className="mb-1 rounded-md bg-red-50 px-3 py-2 text-sm text-red-700">
            <span className="font-medium">Blocking:</span> {f.message}
          </div>
        ))}
        {softFlags.map((f) => (
          <div key={f.id} className="mb-1 rounded-md bg-amber-50 px-3 py-2 text-sm text-amber-700">
            <span className="font-medium">Warning:</span> {f.message}
          </div>
        ))}
      </section>

      <section className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
        <h2 className="mb-2 font-medium text-slate-900">Labor summary</h2>
        <p className="text-sm text-slate-600">
          {run.assignments.length} shifts scheduled &middot; {totalHours.toFixed(1)} total scheduled hours
          {store.avg_transaction_value != null && (
            <span className="ml-1 text-slate-400">
              (revenue estimate uses ${store.avg_transaction_value}/transaction &times; predicted footfall - see the
              compliance dashboard note on this being an estimate, not real Shopify revenue)
            </span>
          )}
        </p>
      </section>

      <section className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
        <h2 className="mb-3 font-medium text-slate-900">Assignments</h2>
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-slate-200 text-left text-slate-500">
              <th className="py-2">Date</th>
              <th className="py-2">Shift</th>
              <th className="py-2">Employee</th>
              <th className="py-2">Status</th>
              <th className="py-2"></th>
            </tr>
          </thead>
          <tbody>
            {[...run.assignments]
              .sort((a, b) => a.date.localeCompare(b.date))
              .map((a) => (
                <tr key={a.id} className="border-b border-slate-100">
                  <td className="py-2">{a.date}</td>
                  <td className="py-2">{templateName(a.shift_template_id)}</td>
                  <td className="py-2">
                    {employeeName(a.employee_id)}
                    {a.manually_edited && <span className="ml-2 text-xs text-amber-600">(edited)</span>}
                  </td>
                  <td className="py-2 capitalize">{a.status}</td>
                  <td className="py-2 text-right">
                    {run.status !== "published" && (
                      <button onClick={() => handleRemove(a.id)} className="text-red-600 hover:underline">
                        Remove
                      </button>
                    )}
                  </td>
                </tr>
              ))}
          </tbody>
        </table>

        {run.status !== "published" && (
          <div className="mt-4 flex flex-wrap items-end gap-2 border-t border-slate-100 pt-4">
            <div>
              <label className="block text-xs text-slate-500">Employee</label>
              <select
                value={addForm.employee_id}
                onChange={(e) => setAddForm({ ...addForm, employee_id: e.target.value })}
                className="rounded-md border border-slate-300 px-2 py-1 text-sm"
              >
                <option value="">Select...</option>
                {employees.map((e) => (
                  <option key={e.id} value={e.id}>
                    {e.full_name}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-xs text-slate-500">Shift</label>
              <select
                value={addForm.shift_template_id}
                onChange={(e) => setAddForm({ ...addForm, shift_template_id: e.target.value })}
                className="rounded-md border border-slate-300 px-2 py-1 text-sm"
              >
                <option value="">Select...</option>
                {templates.map((t) => (
                  <option key={t.id} value={t.id}>
                    {t.name}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-xs text-slate-500">Date</label>
              <input
                type="date"
                value={addForm.date}
                onChange={(e) => setAddForm({ ...addForm, date: e.target.value })}
                className="rounded-md border border-slate-300 px-2 py-1 text-sm"
              />
            </div>
            <button
              onClick={handleAdd}
              className="rounded-md bg-slate-800 px-3 py-1.5 text-sm font-medium text-white hover:bg-slate-900"
            >
              Add assignment
            </button>
          </div>
        )}
      </section>
    </div>
  );
}
