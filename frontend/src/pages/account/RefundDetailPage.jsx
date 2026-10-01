import { useQuery } from "@tanstack/react-query";
import { Link, useParams } from "react-router";

import { getRefund } from "../../api/refunds";
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

function RefundDetailPage() {
  const { reference } = useParams();

  const {
    data: refund,
    isPending,
    isError,
    refetch,
  } = useQuery({
    queryKey: ["refund", reference],
    queryFn: () => getRefund(reference),
    enabled: Boolean(reference),
  });

  if (isPending) {
    return <p className="text-neutral-600">Loading refund…</p>;
  }

  if (isError) {
    return (
      <section className="rounded-2xl bg-red-50 p-6 text-red-700">
        <p>We couldn’t load this refund.</p>

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
      <Link
        to="/account/refunds"
        className="text-sm font-semibold text-neutral-600 hover:text-black"
      >
        ← Back to refunds
      </Link>

      <div className="mt-5 flex flex-wrap items-start justify-between gap-4">
        <div>
          <h2 className="break-all text-2xl font-bold">
            Refund {refund.reference}
          </h2>

          <p className="mt-2 text-sm text-neutral-500">
            Started {formatDate(refund.created_at)}
          </p>
        </div>

        <span
          className={`rounded-full px-4 py-2 text-sm font-bold ${getStatusClass(
            refund.status,
          )}`}
        >
          {refund.status_display}
        </span>
      </div>

      <section className="mt-7 rounded-2xl border border-neutral-200 p-6">
        <h3 className="text-lg font-bold">Refund information</h3>

        <dl className="mt-5 grid gap-5 sm:grid-cols-2">
          <div>
            <dt className="text-sm text-neutral-500">Amount</dt>

            <dd className="mt-1 font-bold">{formatNaira(refund.amount)}</dd>
          </div>

          <div>
            <dt className="text-sm text-neutral-500">Provider</dt>

            <dd className="mt-1 font-bold">{refund.provider_display}</dd>
          </div>

          <div>
            <dt className="text-sm text-neutral-500">Payment reference</dt>

            <dd className="mt-1 break-all font-semibold">
              {refund.payment_reference}
            </dd>
          </div>

          <div>
            <dt className="text-sm text-neutral-500">Provider status</dt>

            <dd className="mt-1 font-semibold">
              {refund.provider_status || "Pending update"}
            </dd>
          </div>

          <div>
            <dt className="text-sm text-neutral-500">Last updated</dt>

            <dd className="mt-1 font-semibold">
              {formatDate(refund.updated_at)}
            </dd>
          </div>

          <div>
            <dt className="text-sm text-neutral-500">Processed</dt>

            <dd className="mt-1 font-semibold">
              {refund.processed_at
                ? formatDate(refund.processed_at)
                : "Not processed yet"}
            </dd>
          </div>
        </dl>
      </section>

      <section className="mt-6 rounded-2xl border border-neutral-200 p-6">
        <h3 className="text-lg font-bold">Reason</h3>

        <p className="mt-3 leading-7 text-neutral-600">{refund.reason}</p>
      </section>

      <Link
        to={`/account/orders/${refund.order_number}`}
        className="button-secondary mt-6 inline-flex"
      >
        View related order
      </Link>
    </div>
  );
}

export default RefundDetailPage;
