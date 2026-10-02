import { ArrowUp, LockKeyhole, Mail, MapPin, PackageCheck } from "lucide-react";
import { Link } from "react-router";

import { useAuth } from "../../features/auth/AuthContext";
import BrandLogo from "../ui/BrandLogo";

function StorefrontFooter() {
  const { isAuthenticated, isAuthLoading } = useAuth();

  function handleBackToTop() {
    window.scrollTo({
      top: 0,
      left: 0,
      behavior: "smooth",
    });
  }

  return (
    <footer className="mt-auto border-t border-neutral-200 bg-white">
      <div className="page-container grid gap-10 py-12 sm:grid-cols-2 lg:grid-cols-[1.4fr_0.8fr_0.8fr_1fr] lg:py-16">
        <div>
          <BrandLogo />

          <p className="mt-4 max-w-sm text-sm leading-7 text-neutral-600">
            Dependable fashion, footwear, accessories, and everyday
            essentials—all within one clean and secure shopping experience.
          </p>

          <div className="mt-6 space-y-3 text-sm text-neutral-600">
            <a
              href="mailto:shopsphere.verify.support@gmail.com"
              className="flex items-start gap-3 hover:text-black"
            >
              <Mail aria-hidden="true" className="mt-0.5 size-4 shrink-0" />

              <span>shopsphere.verify.support@gmail.com</span>
            </a>

            <p className="flex items-center gap-3">
              <MapPin aria-hidden="true" className="size-4 shrink-0" />
              <span>Uyo, Akwa Ibom, Nigeria</span>
            </p>
          </div>
        </div>

        <div>
          <h2 className="text-sm font-bold">Shop</h2>

          <div className="mt-4 grid gap-3 text-sm text-neutral-600">
            <Link to="/products" className="hover:text-black">
              All products
            </Link>

            {!isAuthLoading && isAuthenticated && (
              <>
                <Link to="/cart" className="hover:text-black">
                  Cart
                </Link>

                <Link to="/account/wishlist" className="hover:text-black">
                  Wishlist
                </Link>
              </>
            )}
          </div>
        </div>

        <div>
          <h2 className="text-sm font-bold">Account</h2>

          <div className="mt-4 grid min-h-24 gap-3 text-sm text-neutral-600">
            {!isAuthLoading &&
              (isAuthenticated ? (
                <>
                  <Link to="/account" className="hover:text-black">
                    My account
                  </Link>

                  <Link to="/account/orders" className="hover:text-black">
                    Orders
                  </Link>

                  <Link
                    to="/account/notifications"
                    className="hover:text-black"
                  >
                    Notifications
                  </Link>
                </>
              ) : (
                <>
                  <Link to="/login" className="hover:text-black">
                    Sign in
                  </Link>

                  <Link to="/register" className="hover:text-black">
                    Create an account
                  </Link>
                </>
              ))}
          </div>
        </div>

        <div>
          <h2 className="text-sm font-bold">Company</h2>

          <div className="mt-4 grid gap-3 text-sm text-neutral-600">
            <Link to="/about" className="hover:text-black">
              About ShopSphere
            </Link>

            <a
              href="mailto:shopsphere.verify.support@gmail.com"
              className="hover:text-black"
            >
              Contact us
            </a>
          </div>

          <div className="mt-7 space-y-3 border-t border-neutral-200 pt-6 text-xs leading-5 text-neutral-500">
            <p className="flex gap-2">
              <LockKeyhole
                aria-hidden="true"
                className="mt-0.5 size-4 shrink-0"
              />

              <span>Secure checkout through Paystack</span>
            </p>

            <p className="flex gap-2">
              <PackageCheck
                aria-hidden="true"
                className="mt-0.5 size-4 shrink-0"
              />

              <span>Order updates from your account</span>
            </p>
          </div>
        </div>
      </div>

      <div className="border-t border-neutral-200">
        <div className="page-container grid items-center gap-4 py-5 text-xs text-neutral-500 sm:grid-cols-[1fr_auto_1fr]">
          <p className="text-center sm:text-left">
            Simple choices. Strong personal style.
          </p>

          <button
            type="button"
            onClick={handleBackToTop}
            className="inline-flex min-h-10 items-center justify-center gap-2 justify-self-center rounded-full bg-amber-400 px-5 font-bold text-black transition hover:bg-amber-300 focus:outline-none focus:ring-2 focus:ring-amber-500 focus:ring-offset-2"
          >
            Back to top
            <ArrowUp aria-hidden="true" className="size-4" />
          </button>

          <p className="text-center sm:justify-self-end sm:text-right">
            © {new Date().getFullYear()} ShopSphere. All rights reserved.
          </p>
        </div>
      </div>
    </footer>
  );
}

export default StorefrontFooter;
