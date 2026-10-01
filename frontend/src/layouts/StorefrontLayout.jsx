import { Outlet, useLocation } from "react-router";

import StorefrontFooter from "../components/layout/StorefrontFooter";
import StorefrontHeader from "../components/layout/StorefrontHeader";

const authenticationPaths = new Set([
  "/login",
  "/register",
  "/forgot-password",
  "/reset-password",
]);

function StorefrontLayout() {
  const location = useLocation();

  const isAuthenticationPage = authenticationPaths.has(location.pathname);

  return (
    <div className="flex min-h-screen flex-col bg-white text-neutral-900">
      {!isAuthenticationPage && <StorefrontHeader />}

      <main className="flex-1">
        <Outlet />
      </main>

      {!isAuthenticationPage && <StorefrontFooter />}
    </div>
  );
}

export default StorefrontLayout;
