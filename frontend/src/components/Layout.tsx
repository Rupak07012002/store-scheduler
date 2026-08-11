import { NavLink, Outlet, useNavigate } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";

const navLinkClass = ({ isActive }: { isActive: boolean }) =>
  `rounded-md px-3 py-2 text-sm font-medium ${isActive ? "bg-brand-100 text-brand-700" : "text-slate-600 hover:bg-slate-100"}`;

export default function Layout() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  function handleLogout() {
    logout();
    navigate("/login");
  }

  const isManagerLike = user?.role === "owner" || user?.role === "store_manager";

  return (
    <div className="min-h-screen bg-slate-50">
      <header className="border-b border-slate-200 bg-white">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-4 py-3">
          <div className="flex items-center gap-6">
            <span className="text-lg font-semibold text-slate-900">Store Scheduler</span>
            <nav className="flex gap-1">
              {isManagerLike && (
                <>
                  <NavLink to="/stores" className={navLinkClass}>
                    Stores
                  </NavLink>
                  <NavLink to="/swaps" className={navLinkClass}>
                    Swap Requests
                  </NavLink>
                </>
              )}
              {user?.role === "employee" && (
                <>
                  <NavLink to="/my-shifts" className={navLinkClass}>
                    My Shifts
                  </NavLink>
                  <NavLink to="/availability" className={navLinkClass}>
                    Availability
                  </NavLink>
                  <NavLink to="/time-off" className={navLinkClass}>
                    Time Off
                  </NavLink>
                  <NavLink to="/request-swap" className={navLinkClass}>
                    Request Swap
                  </NavLink>
                </>
              )}
            </nav>
          </div>
          <div className="flex items-center gap-3 text-sm text-slate-600">
            <span>
              {user?.full_name} <span className="text-slate-400">({user?.role})</span>
            </span>
            <button onClick={handleLogout} className="rounded-md border border-slate-300 px-3 py-1 hover:bg-slate-100">
              Log out
            </button>
          </div>
        </div>
      </header>
      <main className="mx-auto max-w-6xl px-4 py-6">
        <Outlet />
      </main>
    </div>
  );
}
