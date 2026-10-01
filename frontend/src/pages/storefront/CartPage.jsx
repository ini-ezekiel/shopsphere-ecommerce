import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Minus, Plus, ShoppingBag, Trash2 } from "lucide-react";
import { Link } from "react-router";
import { toast } from "sonner";

import { clearCart, getCart, removeCartItem, updateCartItem } from "../../api/cart";
import { getApiError } from "../../lib/errors";
import { formatNaira } from "../../lib/format";

function CartPage() {
  const queryClient = useQueryClient();
  const { data: cart, isPending, isError, refetch } = useQuery({
    queryKey: ["cart"],
    queryFn: getCart,
  });

  const mutation = useMutation({
    mutationFn: async ({ action, itemId, quantity }) => {
      if (action === "remove") return removeCartItem(itemId);
      if (action === "clear") return clearCart();
      return updateCartItem(itemId, quantity);
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["cart"] }),
    onError: (error) => toast.error(getApiError(error, "Unable to update your cart.")),
  });

  if (isPending) {
    return <div className="page-container min-h-[60vh] py-12 text-neutral-600">Loading your cart…</div>;
  }

  if (isError) {
    return (
      <div className="page-container flex min-h-[60vh] flex-col items-center justify-center text-center">
        <h1 className="text-2xl font-bold">We couldn’t load your cart</h1>
        <button type="button" onClick={() => refetch()} className="button-primary mt-6">Try again</button>
      </div>
    );
  }

  if (!cart?.items?.length) {
    return (
      <section className="page-container flex min-h-[65vh] flex-col items-center justify-center text-center">
        <div className="flex size-16 items-center justify-center rounded-full bg-neutral-100">
          <ShoppingBag className="size-7" aria-hidden="true" />
        </div>
        <h1 className="mt-6 text-3xl font-bold">Your cart is empty</h1>
        <p className="mt-3 text-neutral-600">Find something you like and add it to your bag.</p>
        <Link to="/products" className="button-primary mt-7">Shop products</Link>
      </section>
    );
  }

  return (
    <section className="page-container py-10 lg:py-14">
      <div className="flex items-end justify-between gap-4 border-b border-neutral-200 pb-7">
        <div>
          <p className="eyebrow">Your bag</p>
          <h1 className="mt-2 text-4xl font-bold tracking-tight">Shopping cart</h1>
          <p className="mt-2 text-neutral-600">{cart.total_quantity} item{cart.total_quantity === 1 ? "" : "s"}</p>
        </div>
        <button
          type="button"
          onClick={() => mutation.mutate({ action: "clear" })}
          disabled={mutation.isPending}
          className="text-sm font-semibold text-neutral-600 hover:text-red-700"
        >
          Clear cart
        </button>
      </div>

      <div className="mt-8 grid gap-10 lg:grid-cols-[1fr_360px]">
        <div className="divide-y divide-neutral-200 border-y border-neutral-200">
          {cart.items.map((item) => (
            <article key={item.id} className="grid grid-cols-[96px_1fr] gap-4 py-6 sm:grid-cols-[128px_1fr_auto]">
              <Link to={`/products/${item.variant.product_slug}`} className="aspect-square overflow-hidden rounded-xl bg-neutral-100 p-2">
                {item.variant.primary_image ? (
                  <img src={item.variant.primary_image} alt={item.variant.product_name} className="h-full w-full object-contain" />
                ) : null}
              </Link>
              <div>
                <Link to={`/products/${item.variant.product_slug}`} className="font-bold text-neutral-950 hover:underline">
                  {item.variant.product_name}
                </Link>
                <p className="mt-1 text-sm text-neutral-500">{item.variant.name}</p>
                <p className="mt-2 font-semibold">{formatNaira(item.unit_price)}</p>

                <div className="mt-4 inline-flex items-center rounded-full border border-neutral-300">
                  <button
                    type="button"
                    aria-label="Decrease quantity"
                    disabled={item.quantity <= 1 || mutation.isPending}
                    onClick={() => mutation.mutate({ action: "update", itemId: item.id, quantity: item.quantity - 1 })}
                    className="flex size-10 items-center justify-center disabled:opacity-35"
                  ><Minus className="size-4" /></button>
                  <span className="w-9 text-center text-sm font-semibold">{item.quantity}</span>
                  <button
                    type="button"
                    aria-label="Increase quantity"
                    disabled={item.quantity >= item.variant.available_quantity || mutation.isPending}
                    onClick={() => mutation.mutate({ action: "update", itemId: item.id, quantity: item.quantity + 1 })}
                    className="flex size-10 items-center justify-center disabled:opacity-35"
                  ><Plus className="size-4" /></button>
                </div>
              </div>
              <div className="col-span-2 flex items-center justify-between sm:col-span-1 sm:flex-col sm:items-end">
                <p className="font-bold">{formatNaira(item.subtotal)}</p>
                <button
                  type="button"
                  aria-label={`Remove ${item.variant.product_name}`}
                  disabled={mutation.isPending}
                  onClick={() => mutation.mutate({ action: "remove", itemId: item.id })}
                  className="flex size-10 items-center justify-center rounded-full text-neutral-500 hover:bg-red-50 hover:text-red-700"
                ><Trash2 className="size-5" /></button>
              </div>
            </article>
          ))}
        </div>

        <aside className="h-fit rounded-2xl bg-neutral-950 p-6 text-white lg:sticky lg:top-28">
          <h2 className="text-xl font-bold">Order summary</h2>
          <div className="mt-6 flex justify-between border-b border-white/15 pb-5 text-neutral-300">
            <span>Subtotal</span><span className="font-semibold text-white">{formatNaira(cart.total)}</span>
          </div>
          <p className="mt-5 text-sm leading-6 text-neutral-400">Shipping is calculated from your delivery location at checkout.</p>
          <Link to="/checkout" className="mt-6 flex min-h-12 items-center justify-center rounded-full bg-white px-5 font-bold text-black hover:bg-neutral-200">
            Continue to checkout
          </Link>
          <Link to="/products" className="mt-3 flex min-h-11 items-center justify-center text-sm font-semibold text-neutral-300 hover:text-white">
            Continue shopping
          </Link>
        </aside>
      </div>
    </section>
  );
}

export default CartPage;
