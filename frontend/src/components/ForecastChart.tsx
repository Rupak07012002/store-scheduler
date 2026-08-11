import type { HeadcountRequirement } from "../api/types";

function nextMonday(): string {
  const today = new Date();
  const day = today.getDay(); // 0=Sunday
  const diff = ((8 - day) % 7) || 7;
  const monday = new Date(today);
  monday.setDate(today.getDate() + diff);
  return monday.toISOString().slice(0, 10);
}

export { nextMonday };

export default function ForecastChart({ data }: { data: HeadcountRequirement[] }) {
  if (data.length === 0) {
    return <p className="text-sm text-slate-500">No forecast data yet.</p>;
  }

  const max = Math.max(...data.map((d) => d.predicted_footfall), 1);
  const byDate = new Map<string, HeadcountRequirement[]>();
  for (const point of data) {
    const list = byDate.get(point.date) ?? [];
    list.push(point);
    byDate.set(point.date, list);
  }

  return (
    <div className="space-y-4">
      {Array.from(byDate.entries()).map(([date, points]) => (
        <div key={date}>
          <p className="mb-1 text-sm font-medium text-slate-700">{date}</p>
          <div className="space-y-1">
            {points.map((p) => (
              <div key={p.shift_template_id} className="flex items-center gap-2 text-xs">
                <span className="w-20 shrink-0 text-slate-500">{p.shift_template_name}</span>
                <div className="h-4 flex-1 rounded bg-slate-100">
                  <div
                    className="h-4 rounded bg-brand-500"
                    style={{ width: `${(p.predicted_footfall / max) * 100}%` }}
                  />
                </div>
                <span className="w-32 shrink-0 text-slate-500">
                  {p.predicted_footfall.toFixed(1)} customers &middot; {p.required_headcount} staff
                </span>
              </div>
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}
