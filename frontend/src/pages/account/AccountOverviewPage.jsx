import { Link } from "react-router";

import { useAuth } from "../../features/auth/AuthContext";

function AccountOverviewPage() {
  const { user } = useAuth();

  return (
    <div>
      <h2 className="text-2xl font-bold">Hello, {user?.first_name || user?.username}</h2>
      <p className="mt-2 text-neutral-600">Manage your details and follow your orders from one place.</p>
      <div className="mt-7 grid gap-4 sm:grid-cols-2">
        <Link to="/account/orders" className="rounded-2xl border border-neutral-200 p-6 transition hover:border-black">
          <h3 className="font-bold">Your orders</h3>
          <p className="mt-2 text-sm leading-6 text-neutral-600">Check payment, fulfilment, and delivery status.</p>
        </Link>
        <Link to="/account/profile" className="rounded-2xl border border-neutral-200 p-6 transition hover:border-black">
          <h3 className="font-bold">Profile details</h3>
          <p className="mt-2 text-sm leading-6 text-neutral-600">Keep your customer information up to date.</p>
        </Link>
      </div>
    </div>
  );
}

export default AccountOverviewPage;
