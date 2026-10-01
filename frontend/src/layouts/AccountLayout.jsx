import { NavLink, Outlet } from "react-router";

const links = [
  ["Overview", "/account"],
  ["Orders", "/account/orders"],
  ["Refunds", "/account/refunds"],
  ["Wishlist", "/account/wishlist"],
  ["Notifications", "/account/notifications"],
  ["Profile", "/account/profile"],
  ["Security", "/account/security"],
];

function AccountLayout() {
  return (
    <section className="page-container py-10 lg:py-14">
      <p className="eyebrow">My account</p>

      <h1 className="mt-2 text-4xl font-bold tracking-tight">Account</h1>

      <div className="mt-8 grid gap-8 lg:grid-cols-[220px_1fr]">
        <nav
          aria-label="Account navigation"
          className="flex gap-2 overflow-x-auto border-b border-neutral-200 pb-4 lg:block lg:space-y-1 lg:border-b-0 lg:pb-0"
        >
          {links.map(([label, to]) => (
            <NavLink
              key={to}
              to={to}
              end={to === "/account"}
              className={({ isActive }) =>
                `block shrink-0 rounded-xl px-4 py-3 text-sm font-semibold ${
                  isActive
                    ? "bg-black text-white"
                    : "text-neutral-700 hover:bg-neutral-100"
                }`
              }
            >
              {label}
            </NavLink>
          ))}
        </nav>

        <div className="min-w-0">
          <Outlet />
        </div>
      </div>
    </section>
  );
}

export default AccountLayout;
