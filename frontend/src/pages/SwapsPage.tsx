import { useEffect, useState } from "react";
import { approveSwap, denySwap, listStores, listSwaps } from "../api/endpoints";
import type { Store, SwapRequest } from "../api/types";
import { ApiError } from "../api/client";
import { useAuth } from "../auth/AuthContext";

export default function SwapsPage() {
  const { user } = useAuth();
  const [stores, setStores] = useState<Store[]>([]);
  const [storeId, setStoreId] = useState<string>("");
  const [swaps, setSwaps] = useState<SwapRequest[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    listStores().then((data) => {
      setStores(data);
      const initial = user?.role === "store_manager" ? user.store_id ?? data[0]?.id : data[0]?.id;
      if (initial) setStoreId(initial);
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function refresh() {
    if (!storeId) return;
    setSwaps(await listSwaps(storeId, "pending"));
  }

  useEffect(() => {
    refresh();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [storeId]);

  async function handle(action: "approve" | "deny", id: string) {
    setError(null);
    try {
      if (action === "approve") await approveSwap(id);
      else await denySwap(id);
      await refresh();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Action failed");
    }
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold text-slate-900">Pending swap requests</h1>
        {user?.role === "owner" && (
          <select
            value={storeId}
            onChange={(e) => setStoreId(e.target.value)}
            className="rounded-md border border-slate-300 px-2 py-1 text-sm"
          >
            {stores.map((s) => (
              <option key={s.id} value={s.id}>
                {s.name}
              </option>
            ))}
          </select>
        )}
      </div>
      {error && <div className="rounded-md bg-red-50 px-3 py-2 text-sm text-red-700">{error}</div>}
      <div className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
        {swaps.length === 0 && <p className="text-sm text-slate-400">No pending swap requests.</p>}
        {swaps.map((s) => (
          <div key={s.id} className="flex items-center justify-between border-b border-slate-100 py-2 text-sm last:border-0">
            <span className="text-slate-600">
              Swap {s.source_assignment_id.slice(0, 8)} &harr; {s.target_assignment_id?.slice(0, 8) ?? "open"}
            </span>
            <div className="flex gap-2">
              <button onClick={() => handle("approve", s.id)} className="rounded-md bg-emerald-600 px-3 py-1 text-white hover:bg-emerald-700">
                Approve
              </button>
              <button onClick={() => handle("deny", s.id)} className="rounded-md border border-slate-300 px-3 py-1 hover:bg-slate-100">
                Deny
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
