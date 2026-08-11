import { useEffect, useState } from "react";
import { listShiftTemplates, myShifts } from "../api/endpoints";
import type { ShiftAssignment, ShiftTemplate } from "../api/types";
import { useAuth } from "../auth/AuthContext";

export default function MyShiftsPage() {
  const { user } = useAuth();
  const [shifts, setShifts] = useState<ShiftAssignment[]>([]);
  const [templates, setTemplates] = useState<ShiftTemplate[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([myShifts(), user?.store_id ? listShiftTemplates(user.store_id) : Promise.resolve([])]).then(
      ([shiftData, templateData]) => {
        setShifts(shiftData);
        setTemplates(templateData);
        setLoading(false);
      },
    );
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  if (loading) return <p className="text-slate-500">Loading...</p>;

  const templateLabel = (id: string) => {
    const t = templates.find((tt) => tt.id === id);
    return t ? `${t.name} (${t.start_time}-${t.end_time})` : id.slice(0, 8);
  };

  return (
    <div>
      <h1 className="mb-4 text-xl font-semibold text-slate-900">My published shifts</h1>
      <div className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
        {shifts.length === 0 && <p className="text-sm text-slate-400">No published shifts yet.</p>}
        <table className="w-full text-sm">
          <tbody>
            {shifts.map((s) => (
              <tr key={s.id} className="border-b border-slate-100 last:border-0">
                <td className="py-2 font-medium text-slate-700">{s.date}</td>
                <td className="py-2 text-slate-500">{templateLabel(s.shift_template_id)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
