import { useQuery } from "@tanstack/react-query";
import { Banknote, ChevronRight } from "lucide-react";
import { Link } from "react-router";

import { getRefunds } from "../../api/refunds";
import { formatDate, formatNaira } from "../../lib/format";

function getStatusClass(status) {
  if (status === "processed") {
    return "bg-green-100 text-green-700";
  }

  if (status === "failed" || status === "needs_attention") {
    return "bg-red-100 text-red-700";
  }

  return "bg-amber-100 text-amber-700";
}

function RefundListPage() {
  const { data, isPending, isError, refetch } = useQuery({
    queryKey: ["refunds"],
    queryFn: getRefunds,
  });

  const refunds = Array.isArray(data) ? data : data?.results || [];

  return (
    <div>
      <div>
        <h2 className="text-2xl font-bold">Refunds</h2>

        <p className="mt-2 text-sm text-neutral-600">
          Track refunds associated with your orders.
        </p>
      </div>

      {isPending && (
        <p className="mt-6 text-neutral-600">Loading your refunds…</p>
      )}

      {isError && (
        <section className="mt-6 rounded-2xl bg-red-50 p-6 text-red-700">
          <p>We couldn’t load your refunds.</p>

          <button
            type="button"
            onClick={() => refetch()}
            className="mt-4 font-bold underline"
          >
            Try again
          </button>
        </section>
      )}

      {!isPending && !isError && refunds.length === 0 && (
        <section className="mt-6 rounded-2xl border border-dashed border-neutral-300 px-6 py-14 text-center">
          <Banknote className="mx-auto size-10 text-neutral-400" />

          <h3 className="mt-4 text-lg font-bold">No refunds</h3>

          <p className="mx-auto mt-2 max-w-md text-sm leading-6 text-neutral-600">
            Refunds issued for your orders will appear here.
          </p>

          <Link
            to="/account/orders"
            className="button-primary mt-6 inline-flex"
          >
            View orders
          </Link>
        </section>
      )}

      {!isPending && !isError && refunds.length > 0 && (
        <div className="mt-6 space-y-3">
          {refunds.map((refund) => (
            <Link
              key={refund.id}
              to={`/account/refunds/${refund.reference}`}
              className="flex flex-col gap-4 rounded-2xl border border-neutral-200 p-5 transition hover:border-black sm:flex-row sm:items-center sm:justify-between"
            >
              <div className="min-w-0">
                <p className="font-bold text-neutral-950">{refund.reference}</p>

                <p className="mt-1 text-sm text-neutral-600">
                  Order {refund.order_number}
                </p>

                <p className="mt-1 text-xs text-neutral-500">
                  Started {formatDate(refund.created_at)}
                </p>
              </div>

              <div className="flex items-center justify-between gap-4 sm:justify-end">
                <div className="sm:text-right">
                  <p className="font-bold">{formatNaira(refund.amount)}</p>

                  <span
                    className={`mt-2 inline-flex rounded-full px-3 py-1 text-xs font-bold ${getStatusClass(
                      refund.status,
                    )}`}
                  >
                    {refund.status_display}
                  </span>
                </div>

                <ChevronRight className="size-5 text-neutral-400" />
              </div>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}

export default RefundListPage;
