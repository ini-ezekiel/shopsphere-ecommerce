import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link, useParams } from "react-router";
import { toast } from "sonner";

import { cancelOrder, getOrder } from "../../api/orders";
import { getApiError } from "../../lib/errors";
import { formatDate, formatNaira } from "../../lib/format";

function OrderDetailPage() {
  const { orderNumber } = useParams();
  const queryClient = useQueryClient();
  const {
    data: order,
    isPending,
    isError,
  } = useQuery({
    queryKey: ["order", orderNumber],
    queryFn: () => getOrder(orderNumber),
  });
  const cancelMutation = useMutation({
    mutationFn: () => cancelOrder(orderNumber),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["order", orderNumber] });
      queryClient.invalidateQueries({ queryKey: ["orders"] });
      toast.success("Order cancelled.");
    },
    onError: (error) =>
      toast.error(getApiError(error, "Unable to cancel this order.")),
  });

  if (isPending) return <p className="text-neutral-600">Loading order…</p>;
  if (isError)
    return (
      <p className="rounded-xl bg-red-50 p-4 text-red-700">
        We couldn’t load this order.
      </p>
    );

  return (
    <div>
      <Link
        to="/account/orders"
        className="text-sm font-semibold text-neutral-600 hover:text-black"
      >
        ← Back to orders
      </Link>
      <div className="mt-5 flex flex-wrap items-end justify-between gap-4">
        <div>
          <h2 className="text-2xl font-bold">Order {order.order_number}</h2>
          <p className="mt-2 text-sm text-neutral-500">
            Placed {formatDate(order.created_at)}
          </p>
        </div>
        <span className="rounded-full bg-neutral-100 px-4 py-2 text-sm font-bold">
          {order.status_display}
        </span>
      </div>
      <div className="mt-7 divide-y divide-neutral-200 rounded-2xl border border-neutral-200 px-5">
        {order.items.map((item) => (
          <div key={item.id} className="flex justify-between gap-4 py-5">
            <div>
              <p className="font-bold">{item.product_name}</p>
              <p className="mt-1 text-sm text-neutral-500">
                {item.quantity} × {item.variant_name}
              </p>
            </div>
            <p className="font-semibold">{formatNaira(item.line_total)}</p>
          </div>
        ))}
      </div>
      <div className="mt-6 ml-auto max-w-sm space-y-3 rounded-2xl bg-neutral-100 p-5 text-sm">
        <div className="flex justify-between">
          <span>Subtotal</span>
          <span>{formatNaira(order.subtotal)}</span>
        </div>
        <div className="flex justify-between">
          <span>Shipping</span>
          <span>{formatNaira(order.shipping_fee)}</span>
        </div>
        <div className="flex justify-between border-t border-neutral-300 pt-3 text-base font-bold">
          <span>Total</span>
          <span>{formatNaira(order.total_amount)}</span>
        </div>
      </div>
      {order.delivery_address && (
        <div className="mt-6 rounded-2xl border border-neutral-200 p-5">
          <h3 className="font-bold">Delivery address</h3>
          <p className="mt-2 text-sm leading-6 text-neutral-600">
            {order.delivery_address.recipient_name}
            <br />
            {order.delivery_address.address_line_1}
            <br />
            {order.delivery_address.city}, {order.delivery_address.state}
          </p>
        </div>
      )}
      {order.status === "pending_payment" && (
        <button
          type="button"
          disabled={cancelMutation.isPending}
          onClick={() => cancelMutation.mutate()}
          className="mt-6 text-sm font-bold text-red-700 hover:underline"
        >
          Cancel order
        </button>
      )}
    </div>
  );
}

export default OrderDetailPage;
