import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowLeft, PackageCheck, RotateCcw, Truck } from "lucide-react";
import { useState } from "react";
import { Link, useParams } from "react-router";
import { toast } from "sonner";

import {
  getStaffOrder,
  initiateStaffRefund,
  updateStaffOrderStatus,
} from "../../api/staff";
import { getApiError } from "../../lib/errors";
import { formatNaira } from "../../lib/format";

const nextTransitions = {
  confirmed: {
    status: "processing",
    label: "Start processing",
  },
  processing: {
    status: "shipped",
    label: "Mark as shipped",
  },
  shipped: {
    status: "delivered",
    label: "Mark as delivered",
  },
};

function formatDateTime(value) {
  if (!value) {
    return "Not available";
  }

  return new Intl.DateTimeFormat("en-NG", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

function getStatusClasses(status) {
  const classes = {
    pending_payment: "bg-amber-100 text-amber-800",
    confirmed: "bg-blue-100 text-blue-800",
    processing: "bg-purple-100 text-purple-800",
    shipped: "bg-indigo-100 text-indigo-800",
    delivered: "bg-green-100 text-green-800",
    cancelled: "bg-red-100 text-red-800",
    successful: "bg-green-100 text-green-800",
    failed: "bg-red-100 text-red-800",
    initialized: "bg-amber-100 text-amber-800",
    pending: "bg-amber-100 text-amber-800",
    needs_attention: "bg-red-100 text-red-800",
    processed: "bg-green-100 text-green-800",
  };

  return classes[status] || "bg-neutral-100 text-neutral-700";
}

function StatusBadge({ status, label }) {
  return (
    <span
      className={`inline-flex rounded-full px-3 py-1 text-xs font-bold ${getStatusClasses(
        status,
      )}`}
    >
      {label || status}
    </span>
  );
}

function StaffOrderDetailPage() {
  const { orderNumber } = useParams();
  const queryClient = useQueryClient();

  const [note, setNote] = useState("");
  const [carrier, setCarrier] = useState("");
  const [trackingNumber, setTrackingNumber] = useState("");

  const [selectedPaymentReference, setSelectedPaymentReference] = useState("");
  const [refundReason, setRefundReason] = useState("");

  const {
    data: order,
    isPending,
    isError,
    error,
  } = useQuery({
    queryKey: ["staff-order", orderNumber],
    queryFn: () => getStaffOrder(orderNumber),
    enabled: Boolean(orderNumber),
  });

  const statusMutation = useMutation({
    mutationFn: (payload) => updateStaffOrderStatus(orderNumber, payload),

    onSuccess: (updatedOrder) => {
      queryClient.setQueryData(["staff-order", orderNumber], updatedOrder);

      queryClient.invalidateQueries({
        queryKey: ["staff-orders"],
      });

      queryClient.invalidateQueries({
        queryKey: ["staff-dashboard"],
      });

      setNote("");
      setCarrier("");
      setTrackingNumber("");

      toast.success(
        updatedOrder.transitioned === false
          ? "The order already has this status."
          : "Order status updated successfully.",
      );
    },

    onError: (mutationError) => {
      toast.error(
        getApiError(mutationError, "Unable to update the order status."),
      );
    },
  });

  const refundMutation = useMutation({
    mutationFn: ({ paymentReference, reason }) =>
      initiateStaffRefund(paymentReference, reason),

    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: ["staff-order", orderNumber],
      });

      queryClient.invalidateQueries({
        queryKey: ["staff-orders"],
      });

      queryClient.invalidateQueries({
        queryKey: ["staff-refunds"],
      });

      queryClient.invalidateQueries({
        queryKey: ["staff-dashboard"],
      });

      setSelectedPaymentReference("");
      setRefundReason("");

      toast.success("Refund initiated successfully.");
    },

    onError: (mutationError) => {
      toast.error(
        getApiError(mutationError, "Unable to initiate this refund."),
      );
    },
  });

  function handleStatusUpdate(event) {
    event.preventDefault();

    const transition = nextTransitions[order.status];

    if (!transition) {
      return;
    }

    const payload = {
      status: transition.status,
      note: note.trim(),
    };

    if (transition.status === "shipped") {
      payload.carrier = carrier.trim();
      payload.tracking_number = trackingNumber.trim();
    }

    statusMutation.mutate(payload);
  }

  function handleRefund(event, paymentReference) {
    event.preventDefault();

    const reason = refundReason.trim();

    if (reason.length < 5) {
      toast.error("Enter a refund reason containing at least 5 characters.");
      return;
    }

    refundMutation.mutate({
      paymentReference,
      reason,
    });
  }

  if (isPending) {
    return (
      <div className="rounded-2xl border border-neutral-200 bg-white p-8">
        <p className="text-neutral-600">Loading order details…</p>
      </div>
    );
  }

  if (isError) {
    return (
      <div className="rounded-2xl border border-red-200 bg-red-50 p-6">
        <p className="font-semibold text-red-800">
          {getApiError(error, "Unable to load this order.")}
        </p>

        <Link
          to="/staff/orders"
          className="mt-4 inline-flex font-semibold text-red-800 hover:underline"
        >
          Back to orders
        </Link>
      </div>
    );
  }

  const transition = nextTransitions[order.status];
  const payments = order.payments || [];
  const address = order.delivery_address;

  return (
    <div className="space-y-6">
      <Link
        to="/staff/orders"
        className="inline-flex items-center gap-2 text-sm font-semibold text-neutral-600 hover:text-black"
      >
        <ArrowLeft className="size-4" />
        Back to orders
      </Link>

      <section className="flex flex-wrap items-start justify-between gap-5">
        <div>
          <p className="text-sm font-semibold uppercase tracking-wide text-neutral-500">
            Order details
          </p>

          <h1 className="mt-2 break-all text-2xl font-bold tracking-tight text-neutral-950 sm:text-3xl">
            {order.order_number}
          </h1>

          <p className="mt-2 text-sm text-neutral-500">
            Placed {formatDateTime(order.created_at)}
          </p>
        </div>

        <div className="flex flex-wrap gap-2">
          <StatusBadge status={order.status} label={order.status_display} />

          <StatusBadge
            status={order.inventory_status}
            label={order.inventory_status_display}
          />
        </div>
      </section>

      <div className="grid gap-6 xl:grid-cols-[minmax(0,1.5fr)_minmax(300px,0.8fr)]">
        <div className="space-y-6">
          <section className="overflow-hidden rounded-2xl border border-neutral-200 bg-white">
            <div className="border-b border-neutral-200 px-5 py-4">
              <h2 className="font-bold text-neutral-950">Order items</h2>
            </div>

            <div className="divide-y divide-neutral-200">
              {order.items?.map((item) => (
                <article
                  key={item.id}
                  className="flex flex-wrap justify-between gap-4 px-5 py-5"
                >
                  <div>
                    <p className="font-bold text-neutral-950">
                      {item.product_name}
                    </p>

                    <p className="mt-1 text-sm text-neutral-500">
                      {item.variant_name} · SKU: {item.sku}
                    </p>

                    {Object.keys(item.attributes || {}).length > 0 && (
                      <p className="mt-1 text-sm text-neutral-500">
                        {Object.entries(item.attributes)
                          .map(([key, value]) => `${key}: ${value}`)
                          .join(" · ")}
                      </p>
                    )}

                    <p className="mt-2 text-sm text-neutral-600">
                      {item.quantity} × {formatNaira(item.unit_price)}
                    </p>
                  </div>

                  <p className="font-bold text-neutral-950">
                    {formatNaira(item.line_total)}
                  </p>
                </article>
              ))}
            </div>
          </section>

          <section className="overflow-hidden rounded-2xl border border-neutral-200 bg-white">
            <div className="border-b border-neutral-200 px-5 py-4">
              <h2 className="font-bold text-neutral-950">
                Payments and refunds
              </h2>
            </div>

            {payments.length === 0 ? (
              <p className="px-5 py-6 text-sm text-neutral-500">
                No payment attempt is attached to this order.
              </p>
            ) : (
              <div className="divide-y divide-neutral-200">
                {payments.map((payment) => {
                  const canRefund =
                    payment.status === "successful" && !payment.refund;

                  const refundFormOpen =
                    selectedPaymentReference === payment.reference;

                  return (
                    <article key={payment.id} className="space-y-4 px-5 py-5">
                      <div className="flex flex-wrap items-start justify-between gap-4">
                        <div>
                          <p className="break-all font-bold text-neutral-950">
                            {payment.reference}
                          </p>

                          <p className="mt-1 text-sm text-neutral-500">
                            {payment.provider_display || payment.provider}
                            {payment.channel ? ` · ${payment.channel}` : ""}
                          </p>

                          <p className="mt-1 text-xs text-neutral-500">
                            Created {formatDateTime(payment.created_at)}
                          </p>
                        </div>

                        <div className="text-right">
                          <p className="font-bold text-neutral-950">
                            {formatNaira(payment.amount)}
                          </p>

                          <div className="mt-2">
                            <StatusBadge
                              status={payment.status}
                              label={payment.status_display}
                            />
                          </div>
                        </div>
                      </div>

                      {payment.gateway_response && (
                        <p className="rounded-xl bg-neutral-50 p-3 text-sm text-neutral-600">
                          {payment.gateway_response}
                        </p>
                      )}

                      {payment.refund && (
                        <div className="rounded-xl border border-neutral-200 bg-neutral-50 p-4">
                          <div className="flex flex-wrap items-center justify-between gap-3">
                            <div>
                              <p className="font-semibold text-neutral-950">
                                Refund {payment.refund.reference}
                              </p>

                              <p className="mt-1 text-sm text-neutral-600">
                                {payment.refund.reason}
                              </p>
                            </div>

                            <StatusBadge
                              status={payment.refund.status}
                              label={payment.refund.status_display}
                            />
                          </div>
                        </div>
                      )}

                      {canRefund && !refundFormOpen && (
                        <button
                          type="button"
                          onClick={() => {
                            setSelectedPaymentReference(payment.reference);
                            setRefundReason("");
                          }}
                          className="inline-flex items-center gap-2 rounded-xl border border-red-200 px-4 py-2 text-sm font-bold text-red-700 hover:bg-red-50"
                        >
                          <RotateCcw className="size-4" />
                          Initiate full refund
                        </button>
                      )}

                      {canRefund && refundFormOpen && (
                        <form
                          onSubmit={(event) =>
                            handleRefund(event, payment.reference)
                          }
                          className="rounded-xl border border-red-200 bg-red-50 p-4"
                        >
                          <label
                            htmlFor={`refund-reason-${payment.id}`}
                            className="text-sm font-bold text-neutral-900"
                          >
                            Refund reason
                          </label>

                          <textarea
                            id={`refund-reason-${payment.id}`}
                            value={refundReason}
                            onChange={(event) =>
                              setRefundReason(event.target.value)
                            }
                            rows={4}
                            maxLength={1000}
                            placeholder="Explain why this payment is being refunded"
                            className="mt-2 w-full rounded-xl border border-neutral-300 bg-white px-4 py-3 text-sm outline-none focus:border-black"
                          />

                          <div className="mt-3 flex flex-wrap gap-3">
                            <button
                              type="submit"
                              disabled={refundMutation.isPending}
                              className="rounded-xl bg-red-700 px-4 py-2 text-sm font-bold text-white hover:bg-red-800 disabled:cursor-not-allowed disabled:opacity-60"
                            >
                              {refundMutation.isPending
                                ? "Processing…"
                                : "Confirm full refund"}
                            </button>

                            <button
                              type="button"
                              disabled={refundMutation.isPending}
                              onClick={() => {
                                setSelectedPaymentReference("");
                                setRefundReason("");
                              }}
                              className="rounded-xl border border-neutral-300 bg-white px-4 py-2 text-sm font-bold text-neutral-700 hover:bg-neutral-100"
                            >
                              Cancel
                            </button>
                          </div>
                        </form>
                      )}
                    </article>
                  );
                })}
              </div>
            )}
          </section>

          <section className="overflow-hidden rounded-2xl border border-neutral-200 bg-white">
            <div className="border-b border-neutral-200 px-5 py-4">
              <h2 className="font-bold text-neutral-950">Status history</h2>
            </div>

            {order.status_history?.length ? (
              <div className="divide-y divide-neutral-200">
                {order.status_history.map((history) => (
                  <article key={history.id} className="px-5 py-4">
                    <div className="flex flex-wrap items-center justify-between gap-3">
                      <p className="font-semibold text-neutral-950">
                        {history.from_status_display} →{" "}
                        {history.to_status_display}
                      </p>

                      <p className="text-xs text-neutral-500">
                        {formatDateTime(history.created_at)}
                      </p>
                    </div>

                    <p className="mt-1 text-sm text-neutral-500">
                      Updated by {history.changed_by_email}
                    </p>

                    {history.note && (
                      <p className="mt-2 text-sm text-neutral-700">
                        {history.note}
                      </p>
                    )}
                  </article>
                ))}
              </div>
            ) : (
              <p className="px-5 py-6 text-sm text-neutral-500">
                No fulfillment status changes yet.
              </p>
            )}
          </section>
        </div>

        <aside className="space-y-6">
          <section className="rounded-2xl border border-neutral-200 bg-white p-5">
            <h2 className="font-bold text-neutral-950">Customer</h2>

            <p className="mt-3 break-all text-sm text-neutral-700">
              {order.customer_email}
            </p>
          </section>

          <section className="rounded-2xl border border-neutral-200 bg-white p-5">
            <h2 className="font-bold text-neutral-950">Delivery address</h2>

            {address ? (
              <div className="mt-3 text-sm leading-6 text-neutral-600">
                <p className="font-semibold text-neutral-900">
                  {address.recipient_name}
                </p>
                <p>{address.phone_number}</p>
                <p>{address.address_line_1}</p>

                {address.address_line_2 && <p>{address.address_line_2}</p>}

                {address.landmark && <p>Landmark: {address.landmark}</p>}

                <p>
                  {address.city}, {address.state}
                </p>

                {address.postal_code && <p>{address.postal_code}</p>}

                <p>{address.country}</p>

                <p className="mt-3 font-semibold">
                  Estimated delivery: {address.estimated_delivery_days} days
                </p>
              </div>
            ) : (
              <p className="mt-3 text-sm text-neutral-500">
                No delivery address available.
              </p>
            )}
          </section>

          <section className="rounded-2xl border border-neutral-200 bg-white p-5">
            <h2 className="font-bold text-neutral-950">Order summary</h2>

            <div className="mt-4 space-y-3 text-sm">
              <div className="flex justify-between gap-4">
                <span className="text-neutral-600">Subtotal</span>
                <span className="font-semibold">
                  {formatNaira(order.subtotal)}
                </span>
              </div>

              <div className="flex justify-between gap-4">
                <span className="text-neutral-600">Discount</span>
                <span className="font-semibold">
                  -{formatNaira(order.discount_amount)}
                </span>
              </div>

              <div className="flex justify-between gap-4">
                <span className="text-neutral-600">Shipping</span>
                <span className="font-semibold">
                  {formatNaira(order.shipping_fee)}
                </span>
              </div>

              <div className="flex justify-between gap-4 border-t border-neutral-200 pt-3 text-base">
                <span className="font-bold">Total</span>
                <span className="font-bold">
                  {formatNaira(order.total_amount)}
                </span>
              </div>
            </div>
          </section>

          {order.shipment && (
            <section className="rounded-2xl border border-neutral-200 bg-white p-5">
              <div className="flex items-center gap-2">
                <Truck className="size-5" />

                <h2 className="font-bold text-neutral-950">Shipment</h2>
              </div>

              <div className="mt-4 space-y-2 text-sm text-neutral-600">
                <StatusBadge
                  status={order.shipment.status}
                  label={order.shipment.status_display}
                />

                {order.shipment.carrier && (
                  <p>Carrier: {order.shipment.carrier}</p>
                )}

                {order.shipment.tracking_number && (
                  <p className="break-all">
                    Tracking: {order.shipment.tracking_number}
                  </p>
                )}

                {order.shipment.shipped_at && (
                  <p>Shipped: {formatDateTime(order.shipment.shipped_at)}</p>
                )}

                {order.shipment.delivered_at && (
                  <p>
                    Delivered: {formatDateTime(order.shipment.delivered_at)}
                  </p>
                )}
              </div>
            </section>
          )}

          {transition && (
            <section className="rounded-2xl border border-neutral-200 bg-white p-5">
              <div className="flex items-center gap-2">
                <PackageCheck className="size-5" />

                <h2 className="font-bold text-neutral-950">
                  Update fulfillment
                </h2>
              </div>

              <form onSubmit={handleStatusUpdate} className="mt-4 space-y-4">
                {transition.status === "shipped" && (
                  <>
                    <div>
                      <label
                        htmlFor="shipment-carrier"
                        className="text-sm font-semibold text-neutral-800"
                      >
                        Carrier
                      </label>

                      <input
                        id="shipment-carrier"
                        value={carrier}
                        onChange={(event) => setCarrier(event.target.value)}
                        required
                        maxLength={100}
                        placeholder="Example: DHL"
                        className="mt-2 min-h-11 w-full rounded-xl border border-neutral-300 px-4 text-sm outline-none focus:border-black"
                      />
                    </div>

                    <div>
                      <label
                        htmlFor="shipment-tracking"
                        className="text-sm font-semibold text-neutral-800"
                      >
                        Tracking number
                      </label>

                      <input
                        id="shipment-tracking"
                        value={trackingNumber}
                        onChange={(event) =>
                          setTrackingNumber(event.target.value)
                        }
                        required
                        maxLength={100}
                        placeholder="Enter tracking number"
                        className="mt-2 min-h-11 w-full rounded-xl border border-neutral-300 px-4 text-sm outline-none focus:border-black"
                      />
                    </div>
                  </>
                )}

                <div>
                  <label
                    htmlFor="status-note"
                    className="text-sm font-semibold text-neutral-800"
                  >
                    Internal note
                  </label>

                  <textarea
                    id="status-note"
                    value={note}
                    onChange={(event) => setNote(event.target.value)}
                    rows={3}
                    maxLength={2000}
                    placeholder="Optional status note"
                    className="mt-2 w-full rounded-xl border border-neutral-300 px-4 py-3 text-sm outline-none focus:border-black"
                  />
                </div>

                <button
                  type="submit"
                  disabled={statusMutation.isPending}
                  className="w-full rounded-xl bg-black px-4 py-3 text-sm font-bold text-white hover:bg-neutral-800 disabled:cursor-not-allowed disabled:opacity-60"
                >
                  {statusMutation.isPending ? "Updating…" : transition.label}
                </button>
              </form>
            </section>
          )}
        </aside>
      </div>
    </div>
  );
}

export default StaffOrderDetailPage;
