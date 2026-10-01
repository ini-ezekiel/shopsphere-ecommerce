import {
  Boxes,
  ClipboardList,
  LayoutDashboard,
  LogOut,
  MessageSquareText,
  PackageSearch,
  ShoppingBag,
  Store,
} from "lucide-react";
import { NavLink, Outlet, useNavigate } from "react-router";

import BrandLogo from "../components/ui/BrandLogo";
import { useAuth } from "../features/auth/AuthContext";

const links = [
  {
    label: "Dashboard",
    to: "/staff",
    icon: LayoutDashboard,
    end: true,
  },
  {
    label: "Orders",
    to: "/staff/orders",
    icon: ClipboardList,
  },
  {
    label: "Products",
    to: "/staff/products",
    icon: PackageSearch,
  },
  {
    label: "Inventory",
    to: "/staff/inventory",
    icon: Boxes,
  },
  {
    label: "Reviews",
    to: "/staff/reviews",
    icon: MessageSquareText,
  },
];

function StaffLayout() {
  const navigate = useNavigate();

  const { user, logout } = useAuth();

  async function handleSignOut() {
    await logout().catch(() => undefined);
    navigate("/", { replace: true });
  }

  return (
    <div className="min-h-screen bg-neutral-100 text-neutral-950">
      <header className="sticky top-0 z-40 border-b border-neutral-200 bg-white lg:hidden">
        <div className="flex min-h-16 items-center justify-between px-4">
          <BrandLogo />

          <NavLink
            to="/"
            aria-label="Open storefront"
            className="flex size-10 items-center justify-center rounded-full hover:bg-neutral-100"
          >
            <Store className="size-5" />
          </NavLink>
        </div>

        <nav
          aria-label="Staff navigation"
          className="flex gap-2 overflow-x-auto border-t border-neutral-200 px-4 py-3"
        >
          {links.map(({ label, to, icon: Icon, end }) => (
            <NavLink
              key={to}
              to={to}
              end={end}
              className={({ isActive }) =>
                `flex shrink-0 items-center gap-2 rounded-xl px-4 py-2.5 text-sm font-semibold ${
                  isActive
                    ? "bg-black text-white"
                    : "bg-neutral-100 text-neutral-700"
                }`
              }
            >
              <Icon className="size-4" />
              {label}
            </NavLink>
          ))}
        </nav>
      </header>

      <aside className="fixed inset-y-0 left-0 hidden w-64 flex-col border-r border-neutral-200 bg-white lg:flex">
        <div className="flex min-h-20 items-center border-b border-neutral-200 px-6">
          <BrandLogo />
        </div>

        <div className="px-6 py-5">
          <p className="text-xs font-bold uppercase tracking-widest text-neutral-500">
            Staff dashboard
          </p>

          <p className="mt-2 truncate text-sm font-semibold">{user?.email}</p>
        </div>

        <nav aria-label="Staff navigation" className="flex-1 space-y-1 px-3">
          {links.map(({ label, to, icon: Icon, end }) => (
            <NavLink
              key={to}
              to={to}
              end={end}
              className={({ isActive }) =>
                `flex items-center gap-3 rounded-xl px-4 py-3 text-sm font-semibold transition ${
                  isActive
                    ? "bg-black text-white"
                    : "text-neutral-700 hover:bg-neutral-100"
                }`
              }
            >
              <Icon className="size-5" />
              {label}
            </NavLink>
          ))}
        </nav>

        <div className="space-y-1 border-t border-neutral-200 p-3">
          <NavLink
            to="/"
            className="flex items-center gap-3 rounded-xl px-4 py-3 text-sm font-semibold text-neutral-700 hover:bg-neutral-100"
          >
            <ShoppingBag className="size-5" />
            View storefront
          </NavLink>

          <button
            type="button"
            onClick={handleSignOut}
            className="flex w-full items-center gap-3 rounded-xl px-4 py-3 text-left text-sm font-semibold text-red-700 hover:bg-red-50"
          >
            <LogOut className="size-5" />
            Sign out
          </button>
        </div>
      </aside>

      <main className="min-w-0 lg:pl-64">
        <div className="mx-auto max-w-400 px-4 py-8 sm:px-6 lg:px-8 lg:py-10">
          <Outlet />
        </div>
      </main>
    </div>
  );
}

export default StaffLayout;
