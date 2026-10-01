import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router";

import { getOrders } from "../../api/orders";
import { formatDate, formatNaira } from "../../lib/format";

function OrderListPage() {
  const { data, isPending, isError } = useQuery({ queryKey: ["orders"], queryFn: getOrders });
  const orders = Array.isArray(data) ? data : (data?.results ?? []);

  return (
    <div>
      <h2 className="text-2xl font-bold">Your orders</h2>
      {isPending && <p className="mt-6 text-neutral-600">Loading orders…</p>}
      {isError && <p className="mt-6 rounded-xl bg-red-50 p-4 text-red-700">We couldn’t load your orders.</p>}
      {!isPending && !isError && orders.length === 0 && (
        <div className="mt-6 rounded-2xl border border-neutral-200 p-8 text-center">
          <p className="text-neutral-600">You haven’t placed an order yet.</p>
          <Link to="/products" className="button-primary mt-5">Start shopping</Link>
        </div>
      )}
      <div className="mt-6 space-y-3">
        {orders.map((order) => (
          <Link key={order.id} to={`/account/orders/${order.order_number}`} className="flex flex-col gap-3 rounded-2xl border border-neutral-200 p-5 transition hover:border-black sm:flex-row sm:items-center sm:justify-between">
            <div><p className="font-bold">{order.order_number}</p><p className="mt-1 text-sm text-neutral-500">Placed {formatDate(order.created_at)}</p></div>
            <div className="sm:text-right"><p className="font-bold">{formatNaira(order.total_amount)}</p><p className="mt-1 text-sm text-neutral-600">{order.status_display}</p></div>
          </Link>
        ))}
      </div>
    </div>
  );
}

export default OrderListPage;
