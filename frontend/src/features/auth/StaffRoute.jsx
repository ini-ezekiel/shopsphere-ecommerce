import { Navigate, Outlet, useLocation } from "react-router";

import { useAuth } from "./AuthContext";

function StaffRoute() {
  const location = useLocation();

  const { user, isAuthenticated, isAuthLoading } = useAuth();

  if (isAuthLoading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-white">
        <p className="text-neutral-600">Checking staff access…</p>
      </div>
    );
  }

  if (!isAuthenticated) {
    return (
      <Navigate
        to="/login"
        replace
        state={{
          from: location,
        }}
      />
    );
  }

  if (!user?.is_staff) {
    return <Navigate to="/account" replace />;
  }

  return <Outlet />;
}

export default StaffRoute;
