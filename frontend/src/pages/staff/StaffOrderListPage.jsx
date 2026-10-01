import { useQuery } from "@tanstack/react-query";
import { ChevronLeft, ChevronRight, Search } from "lucide-react";
import { Link, useSearchParams } from "react-router";

import { getStaffOrders } from "../../api/staff";
import { formatDate, formatNaira } from "../../lib/format";

const orderStatuses = [
  {
    label: "All statuses",
    value: "",
  },
  {
    label: "Pending payment",
    value: "pending_payment",
  },
  {
    label: "Confirmed",
    value: "confirmed",
  },
  {
    label: "Processing",
    value: "processing",
  },
  {
    label: "Shipped",
    value: "shipped",
  },
  {
    label: "Delivered",
    value: "delivered",
  },
  {
    label: "Cancelled",
    value: "cancelled",
  },
];

function getStatusClass(status) {
  if (status === "delivered") {
    return "bg-green-100 text-green-700";
  }

  if (status === "cancelled") {
    return "bg-red-100 text-red-700";
  }

  if (status === "processing" || status === "shipped") {
    return "bg-blue-100 text-blue-700";
  }

  return "bg-amber-100 text-amber-700";
}

function StaffOrderListPage() {
  const [searchParams, setSearchParams] = useSearchParams();

  const search = searchParams.get("search") || "";
  const status = searchParams.get("status") || "";
  const ordering = searchParams.get("ordering") || "-created_at";
  const page = Math.max(1, Number(searchParams.get("page") || 1));

  const { data, isPending, isError, refetch } = useQuery({
    queryKey: ["staff", "orders", search, status, ordering, page],
    queryFn: () =>
      getStaffOrders({
        search: search || undefined,
        status: status || undefined,
        ordering,
        page,
      }),
  });

  const orders = Array.isArray(data) ? data : data?.results || [];

  function updateParameter(name, value) {
    const next = new URLSearchParams(searchParams);

    if (value) {
      next.set(name, value);
    } else {
      next.delete(name);
    }

    if (name !== "page") {
      next.delete("page");
    }

    setSearchParams(next);
  }

  function handleSearch(event) {
    event.preventDefault();

    const formData = new FormData(event.currentTarget);

    updateParameter("search", String(formData.get("search") || "").trim());
  }

  return (
    <div>
      <div>
        <p className="text-xs font-bold uppercase tracking-widest text-neutral-500">
          Fulfilment
        </p>

        <h1 className="mt-2 text-3xl font-bold tracking-tight sm:text-4xl">
          Orders
        </h1>

        <p className="mt-2 text-sm text-neutral-600">
          Search orders and manage fulfilment status.
        </p>
      </div>

      <section className="mt-7 rounded-2xl border border-neutral-200 bg-white p-4">
        <div className="grid gap-4 lg:grid-cols-[1fr_220px_220px]">
          <form onSubmit={handleSearch} className="flex gap-2">
            <label htmlFor="staff-order-search" className="sr-only">
              Search orders
            </label>

            <div className="relative flex-1">
              <Search className="pointer-events-none absolute left-4 top-1/2 size-5 -translate-y-1/2 text-neutral-500" />

              <input
                id="staff-order-search"
                name="search"
                type="search"
                defaultValue={search}
                placeholder="Order, email, phone or tracking number"
                className="field pl-12"
              />
            </div>

            <button type="submit" className="button-primary">
              Search
            </button>
          </form>

          <label className="sr-only" htmlFor="order-status">
            Order status
          </label>

          <select
            id="order-status"
            value={status}
            onChange={(event) => updateParameter("status", event.target.value)}
            className="field bg-white"
          >
            {orderStatuses.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>

          <label className="sr-only" htmlFor="order-ordering">
            Sort orders
          </label>

          <select
            id="order-ordering"
            value={ordering}
            onChange={(event) =>
              updateParameter("ordering", event.target.value)
            }
            className="field bg-white"
          >
            <option value="-created_at">Newest first</option>

            <option value="created_at">Oldest first</option>

            <option value="-total_amount">Highest total</option>

            <option value="total_amount">Lowest total</option>
          </select>
        </div>
      </section>

      {isPending && <p className="mt-6 text-neutral-600">Loading orders…</p>}

      {isError && (
        <section className="mt-6 rounded-2xl bg-red-50 p-6 text-red-700">
          <p>We couldn’t load staff orders.</p>

          <button
            type="button"
            onClick={() => refetch()}
            className="mt-4 font-bold underline"
          >
            Try again
          </button>
        </section>
      )}

      {!isPending && !isError && orders.length === 0 && (
        <section className="mt-6 rounded-2xl border border-dashed border-neutral-300 bg-white p-10 text-center">
          <h2 className="text-lg font-bold">No matching orders</h2>

          <p className="mt-2 text-sm text-neutral-600">
            Try changing the search or status filter.
          </p>
        </section>
      )}

      {!isPending && !isError && orders.length > 0 && (
        <section className="mt-6 overflow-hidden rounded-2xl border border-neutral-200 bg-white">
          <div className="overflow-x-auto">
            <table className="w-full min-w-220 text-left">
              <thead className="border-b border-neutral-200 bg-neutral-50 text-xs uppercase tracking-wide text-neutral-500">
                <tr>
                  <th className="px-5 py-4">Order</th>

                  <th className="px-5 py-4">Customer</th>

                  <th className="px-5 py-4">Status</th>

                  <th className="px-5 py-4">Total</th>

                  <th className="px-5 py-4">Created</th>

                  <th className="px-5 py-4">
                    <span className="sr-only">Open</span>
                  </th>
                </tr>
              </thead>

              <tbody className="divide-y divide-neutral-200">
                {orders.map((order) => (
                  <tr key={order.id} className="hover:bg-neutral-50">
                    <td className="px-5 py-4 font-bold">
                      {order.order_number}
                    </td>

                    <td className="px-5 py-4">
                      <p className="font-semibold">{order.recipient_name}</p>

                      <p className="mt-1 text-sm text-neutral-500">
                        {order.customer_email}
                      </p>
                    </td>

                    <td className="px-5 py-4">
                      <span
                        className={`inline-flex rounded-full px-3 py-1 text-xs font-bold ${getStatusClass(
                          order.status,
                        )}`}
                      >
                        {order.status_display}
                      </span>
                    </td>

                    <td className="px-5 py-4 font-semibold">
                      {formatNaira(order.total_amount)}
                    </td>

                    <td className="px-5 py-4 text-sm text-neutral-500">
                      {formatDate(order.created_at)}
                    </td>

                    <td className="px-5 py-4">
                      <Link
                        to={`/staff/orders/${order.order_number}`}
                        aria-label={`Open ${order.order_number}`}
                        className="flex size-10 items-center justify-center rounded-full hover:bg-neutral-200"
                      >
                        <ChevronRight className="size-5" />
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div className="flex items-center justify-between border-t border-neutral-200 px-5 py-4">
            <p className="text-sm text-neutral-500">
              {data?.count ?? orders.length} orders
            </p>

            <div className="flex gap-2">
              <button
                type="button"
                disabled={!data?.previous}
                onClick={() => updateParameter("page", String(page - 1))}
                className="button-secondary inline-flex items-center gap-2"
              >
                <ChevronLeft className="size-4" />
                Previous
              </button>

              <button
                type="button"
                disabled={!data?.next}
                onClick={() => updateParameter("page", String(page + 1))}
                className="button-secondary inline-flex items-center gap-2"
              >
                Next
                <ChevronRight className="size-4" />
              </button>
            </div>
          </div>
        </section>
      )}
    </div>
  );
}

export default StaffOrderListPage;
