import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { listStores } from "../api/endpoints";
import type { Store } from "../api/types";

export default function StoresPage() {
  const [stores, setStores] = useState<Store[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    listStores().then((data) => {
      setStores(data);
      setLoading(false);
    });
  }, []);

  if (loading) return <p className="text-slate-500">Loading stores...</p>;

  return (
    <div>
      <h1 className="mb-4 text-xl font-semibold text-slate-900">Stores</h1>
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
        {stores.map((store) => (
          <Link
            key={store.id}
            to={`/stores/${store.id}`}
            className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm hover:border-brand-400 hover:shadow"
          >
            <h2 className="font-medium text-slate-900">{store.name}</h2>
            <p className="text-sm text-slate-500">{store.address}</p>
            <p className="mt-2 text-xs text-slate-400">
              Ratio: {store.footfall_to_staff_ratio ?? "default"} customers/hr per staff
            </p>
          </Link>
        ))}
      </div>
    </div>
  );
}
