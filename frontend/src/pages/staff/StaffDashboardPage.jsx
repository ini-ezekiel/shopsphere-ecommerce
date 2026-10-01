import { useQuery } from "@tanstack/react-query";
import {
  Boxes,
  CircleDollarSign,
  PackageCheck,
  RotateCcw,
  ShoppingCart,
  Users,
} from "lucide-react";
import { Link } from "react-router";
import { useState } from "react";

import { getStaffDashboard } from "../../api/staff";
import { formatDate, formatNaira } from "../../lib/format";

const periods = [
  {
    label: "Today",
    value: "today",
  },
  {
    label: "7 days",
    value: "7d",
  },
  {
    label: "30 days",
    value: "30d",
  },
  {
    label: "All time",
    value: "all",
  },
];

function MetricCard({ label, value, description, icon: Icon }) {
  return (
    <section className="rounded-2xl border border-neutral-200 bg-white p-5">
      <div className="flex items-start justify-between gap-4">
        <div>
          <p className="text-sm font-semibold text-neutral-500">{label}</p>

          <p className="mt-3 text-3xl font-bold tracking-tight">{value}</p>

          {description && (
            <p className="mt-2 text-xs leading-5 text-neutral-500">
              {description}
            </p>
          )}
        </div>

        <div className="flex size-11 shrink-0 items-center justify-center rounded-xl bg-neutral-100">
          <Icon className="size-5" />
        </div>
      </div>
    </section>
  );
}

function StaffDashboardPage() {
  const [period, setPeriod] = useState("30d");

  const {
    data: summary,
    isPending,
    isError,
    refetch,
  } = useQuery({
    queryKey: ["staff", "dashboard", period],
    queryFn: () => getStaffDashboard(period),
  });

  if (isPending) {
    return <p className="text-neutral-600">Loading staff dashboard…</p>;
  }

  if (isError) {
    return (
      <section className="rounded-2xl bg-red-50 p-6 text-red-700">
        <h1 className="text-xl font-bold">Dashboard unavailable</h1>

        <p className="mt-2">We couldn’t load the dashboard summary.</p>

        <button
          type="button"
          onClick={() => refetch()}
          className="mt-4 font-bold underline"
        >
          Try again
        </button>
      </section>
    );
  }

  return (
    <div>
      <div className="flex flex-wrap items-end justify-between gap-5">
        <div>
          <p className="text-xs font-bold uppercase tracking-widest text-neutral-500">
            Administration
          </p>

          <h1 className="mt-2 text-3xl font-bold tracking-tight sm:text-4xl">
            Dashboard
          </h1>

          <p className="mt-2 text-sm text-neutral-600">
            Generated {formatDate(summary.generated_at)}
          </p>
        </div>

        <label className="text-sm font-semibold text-neutral-700">
          Reporting period
          <select
            value={period}
            onChange={(event) => setPeriod(event.target.value)}
            className="field mt-2 min-w-40 bg-white"
          >
            {periods.map((periodOption) => (
              <option key={periodOption.value} value={periodOption.value}>
                {periodOption.label}
              </option>
            ))}
          </select>
        </label>
      </div>

      <div className="mt-8 grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <MetricCard
          label="Net sales"
          value={formatNaira(summary.financial.net_sales)}
          description={`${formatNaira(
            summary.financial.gross_paid_amount,
          )} gross payments`}
          icon={CircleDollarSign}
        />

        <MetricCard
          label="Orders"
          value={summary.orders.total}
          description={`${summary.orders.delivered} delivered`}
          icon={ShoppingCart}
        />

        <MetricCard
          label="Active products"
          value={summary.catalog.active_products}
          description={`${summary.catalog.active_variants} active variants`}
          icon={PackageCheck}
        />

        <MetricCard
          label="Customers"
          value={summary.customers.total_customers}
          description={`${summary.customers.new_customers} new in this period`}
          icon={Users}
        />
      </div>

      <div className="mt-4 grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <MetricCard
          label="Pending payment"
          value={summary.orders.pending_payment}
          icon={ShoppingCart}
        />

        <MetricCard
          label="Processing"
          value={summary.orders.processing}
          icon={PackageCheck}
        />

        <MetricCard
          label="Low stock"
          value={summary.catalog.low_stock_variants}
          icon={Boxes}
        />

        <MetricCard
          label="Refunded"
          value={formatNaira(summary.financial.processed_refund_amount)}
          icon={RotateCcw}
        />
      </div>

      <div className="mt-8 grid gap-6 xl:grid-cols-2">
        <section className="rounded-2xl border border-neutral-200 bg-white">
          <div className="flex items-center justify-between border-b border-neutral-200 p-5">
            <div>
              <h2 className="text-lg font-bold">Recent orders</h2>

              <p className="mt-1 text-sm text-neutral-500">
                Latest customer orders
              </p>
            </div>

            <Link
              to="/staff/orders"
              className="text-sm font-bold hover:underline"
            >
              View all
            </Link>
          </div>

          {summary.recent_orders.length === 0 ? (
            <p className="p-6 text-sm text-neutral-500">
              No orders in this period.
            </p>
          ) : (
            <div className="divide-y divide-neutral-200">
              {summary.recent_orders.map((order) => (
                <Link
                  key={order.order_number}
                  to={`/staff/orders/${order.order_number}`}
                  className="flex items-center justify-between gap-4 p-5 transition hover:bg-neutral-50"
                >
                  <div className="min-w-0">
                    <p className="truncate font-bold">{order.order_number}</p>

                    <p className="mt-1 truncate text-sm text-neutral-500">
                      {order.customer_email}
                    </p>
                  </div>

                  <div className="shrink-0 text-right">
                    <p className="font-bold">
                      {formatNaira(order.total_amount)}
                    </p>

                    <p className="mt-1 text-xs text-neutral-500">
                      {order.status_display}
                    </p>
                  </div>
                </Link>
              ))}
            </div>
          )}
        </section>

        <section className="rounded-2xl border border-neutral-200 bg-white">
          <div className="border-b border-neutral-200 p-5">
            <h2 className="text-lg font-bold">Recent refunds</h2>

            <p className="mt-1 text-sm text-neutral-500">
              Latest refund activity
            </p>
          </div>

          {summary.recent_refunds.length === 0 ? (
            <p className="p-6 text-sm text-neutral-500">
              No refunds in this period.
            </p>
          ) : (
            <div className="divide-y divide-neutral-200">
              {summary.recent_refunds.map((refund) => (
                <div
                  key={refund.reference}
                  className="flex items-center justify-between gap-4 p-5"
                >
                  <div className="min-w-0">
                    <p className="truncate font-bold">{refund.reference}</p>

                    <Link
                      to={`/staff/orders/${refund.order_number}`}
                      className="mt-1 block truncate text-sm text-neutral-500 hover:text-black hover:underline"
                    >
                      {refund.order_number}
                    </Link>
                  </div>

                  <div className="shrink-0 text-right">
                    <p className="font-bold">{formatNaira(refund.amount)}</p>

                    <p className="mt-1 text-xs text-neutral-500">
                      {refund.status_display}
                    </p>
                  </div>
                </div>
              ))}
            </div>
          )}
        </section>
      </div>
    </div>
  );
}

export default StaffDashboardPage;
