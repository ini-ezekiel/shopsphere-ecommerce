import { useQuery } from "@tanstack/react-query";
import {
  Bell,
  LogOut,
  Menu,
  Search,
  ShoppingBag,
  UserRound,
  X,
} from "lucide-react";
import { useState } from "react";
import { Link, useNavigate } from "react-router";

import { getCart } from "../../api/cart";
import { useAuth } from "../../features/auth/AuthContext";
import { useNotifications } from "../../features/notifications/NotificationContext";
import BrandLogo from "../ui/BrandLogo";

function CountBadge({ count, showZero = false }) {
  const numericCount = Number(count) || 0;

  if (!showZero && numericCount === 0) {
    return null;
  }

  return (
    <span className="absolute right-0 top-0 flex min-w-5 items-center justify-center rounded-full bg-black px-1 text-[11px] font-bold leading-5 text-white">
      {numericCount > 99 ? "99+" : numericCount}
    </span>
  );
}

function StorefrontHeader() {
  const navigate = useNavigate();

  const { isAuthenticated, logout } = useAuth();

  const { unreadCount } = useNotifications();

  const [searchTerm, setSearchTerm] = useState("");
  const [isMenuOpen, setIsMenuOpen] = useState(false);

  const { data: cart } = useQuery({
    queryKey: ["cart"],
    queryFn: getCart,
    enabled: isAuthenticated,
  });

  async function handleLogout() {
    await logout();
    setIsMenuOpen(false);
    navigate("/");
  }

  function handleSearch(event) {
    event.preventDefault();

    const query = searchTerm.trim();

    if (query) {
      navigate(`/products?search=${encodeURIComponent(query)}`);
    } else {
      navigate("/products");
    }

    setIsMenuOpen(false);
  }

  return (
    <header className="sticky top-0 z-50 border-b border-border bg-white/95 backdrop-blur">
      <div className="mx-auto max-w-360 px-4 sm:px-6 lg:px-8">
        <div className="flex min-h-16 items-center gap-2 sm:gap-4 lg:min-h-20">
          <BrandLogo className="shrink-0" />

          <nav
            aria-label="Main navigation"
            className="ml-4 hidden items-center gap-6 lg:flex"
          >
            <Link
              to="/products"
              className="font-medium text-neutral-700 transition hover:text-black"
            >
              Shop
            </Link>
          </nav>

          {/* Desktop and tablet search */}
          <form
            role="search"
            onSubmit={handleSearch}
            className="ml-auto hidden w-full max-w-md md:block"
          >
            <label htmlFor="desktop-product-search" className="sr-only">
              Search ShopSphere products
            </label>

            <div className="relative">
              <Search
                aria-hidden="true"
                className="pointer-events-none absolute left-4 top-1/2 size-5 -translate-y-1/2 text-neutral-500"
              />

              <input
                id="desktop-product-search"
                type="search"
                value={searchTerm}
                onChange={(event) => setSearchTerm(event.target.value)}
                placeholder="Search products"
                className="min-h-11 w-full rounded-full border border-neutral-300 bg-neutral-50 py-2 pl-12 pr-4 text-sm outline-none transition placeholder:text-neutral-500 focus:border-black focus:bg-white"
              />
            </div>
          </form>

          {/* Desktop account, notifications and cart */}
          <div className="ml-auto hidden items-center gap-1 md:flex">
            <Link
              to={isAuthenticated ? "/account" : "/login"}
              aria-label={isAuthenticated ? "Open account" : "Sign in"}
              className="flex size-11 items-center justify-center rounded-full text-neutral-900 transition hover:bg-neutral-100"
            >
              <UserRound aria-hidden="true" className="size-5" />
            </Link>

            {isAuthenticated && (
              <Link
                to="/account/notifications"
                aria-label={
                  unreadCount > 0
                    ? `Open notifications. ${unreadCount} unread.`
                    : "Open notifications. No unread notifications."
                }
                className="relative flex size-11 items-center justify-center rounded-full text-neutral-900 transition hover:bg-neutral-100"
              >
                <Bell aria-hidden="true" className="size-5" />

                <CountBadge count={unreadCount} showZero />
              </Link>
            )}

            <Link
              to={isAuthenticated ? "/cart" : "/login"}
              aria-label="Open cart"
              className="relative flex size-11 items-center justify-center rounded-full text-neutral-900 transition hover:bg-neutral-100"
            >
              <ShoppingBag aria-hidden="true" className="size-5" />

              <CountBadge count={cart?.total_quantity} />
            </Link>
          </div>

          {/* Mobile notifications and cart */}
          <div className="ml-auto flex items-center md:hidden">
            {isAuthenticated && (
              <Link
                to="/account/notifications"
                aria-label={
                  unreadCount > 0
                    ? `Open notifications. ${unreadCount} unread.`
                    : "Open notifications. No unread notifications."
                }
                className="relative flex size-11 items-center justify-center rounded-full text-neutral-900 transition hover:bg-neutral-100"
              >
                <Bell aria-hidden="true" className="size-5" />

                <CountBadge count={unreadCount} showZero />
              </Link>
            )}

            <Link
              to={isAuthenticated ? "/cart" : "/login"}
              aria-label="Open cart"
              className="relative flex size-11 items-center justify-center rounded-full text-neutral-900 transition hover:bg-neutral-100"
            >
              <ShoppingBag aria-hidden="true" className="size-5" />

              <CountBadge count={cart?.total_quantity} />
            </Link>
          </div>

          {/* Mobile and tablet menu button */}
          <button
            type="button"
            aria-label={
              isMenuOpen ? "Close navigation menu" : "Open navigation menu"
            }
            aria-expanded={isMenuOpen}
            aria-controls="mobile-navigation"
            onClick={() => setIsMenuOpen((current) => !current)}
            className="inline-flex size-11 items-center justify-center rounded-full border border-neutral-300 text-neutral-900 transition hover:bg-neutral-100 lg:hidden"
          >
            {isMenuOpen ? (
              <X aria-hidden="true" className="size-5" />
            ) : (
              <Menu aria-hidden="true" className="size-5" />
            )}
          </button>
        </div>

        {/* Always-visible mobile search */}
        <div className="mx-2 pb-3 md:hidden">
          <form role="search" onSubmit={handleSearch}>
            <label htmlFor="mobile-product-search" className="sr-only">
              Search ShopSphere products
            </label>

            <div className="relative">
              <Search
                aria-hidden="true"
                className="pointer-events-none absolute left-4 top-1/2 size-5 -translate-y-1/2 text-neutral-500"
              />

              <input
                id="mobile-product-search"
                type="search"
                value={searchTerm}
                onChange={(event) => setSearchTerm(event.target.value)}
                placeholder="Search products"
                className="min-h-11 w-full rounded-full border border-neutral-300 bg-neutral-100 py-2 pl-12 pr-4 text-sm outline-none transition placeholder:text-neutral-500 focus:border-black focus:bg-white"
              />
            </div>
          </form>
        </div>

        {/* Mobile and tablet navigation */}
        {isMenuOpen && (
          <div
            id="mobile-navigation"
            className="border-t border-border py-3 lg:hidden"
          >
            <nav aria-label="Mobile navigation" className="grid gap-1">
              <Link
                to="/products"
                onClick={() => setIsMenuOpen(false)}
                className="rounded-xl px-4 py-3 font-semibold text-neutral-900 hover:bg-neutral-100"
              >
                Shop all products
              </Link>

              {isAuthenticated ? (
                <>
                  <Link
                    to="/account"
                    onClick={() => setIsMenuOpen(false)}
                    className="rounded-xl px-4 py-3 font-semibold text-neutral-900 hover:bg-neutral-100"
                  >
                    My account
                  </Link>

                  <Link
                    to="/account/wishlist"
                    onClick={() => setIsMenuOpen(false)}
                    className="rounded-xl px-4 py-3 font-semibold text-neutral-900 hover:bg-neutral-100"
                  >
                    Wishlist
                  </Link>

                  <Link
                    to="/account/notifications"
                    onClick={() => setIsMenuOpen(false)}
                    className="flex items-center justify-between rounded-xl px-4 py-3 font-semibold text-neutral-900 hover:bg-neutral-100"
                  >
                    <span>Notifications</span>

                    <span className="rounded-full bg-black px-2 py-0.5 text-xs font-bold text-white">
                      {unreadCount > 99 ? "99+" : unreadCount}
                    </span>
                  </Link>

                  <Link
                    to="/cart"
                    onClick={() => setIsMenuOpen(false)}
                    className="rounded-xl px-4 py-3 font-semibold text-neutral-900 hover:bg-neutral-100"
                  >
                    Cart
                    {cart?.total_quantity ? ` (${cart.total_quantity})` : ""}
                  </Link>

                  <button
                    type="button"
                    onClick={handleLogout}
                    className="flex items-center gap-2 rounded-xl px-4 py-3 text-left font-semibold text-neutral-700 hover:bg-neutral-100"
                  >
                    <LogOut aria-hidden="true" className="size-4" />
                    Sign out
                  </button>
                </>
              ) : (
                <Link
                  to="/login"
                  onClick={() => setIsMenuOpen(false)}
                  className="rounded-xl px-4 py-3 font-semibold text-neutral-900 hover:bg-neutral-100"
                >
                  Sign in
                </Link>
              )}
            </nav>
          </div>
        )}
      </div>
    </header>
  );
}

export default StorefrontHeader;
