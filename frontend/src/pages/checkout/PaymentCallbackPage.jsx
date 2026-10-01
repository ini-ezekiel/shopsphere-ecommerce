import { useQuery, useQueryClient } from "@tanstack/react-query";
import { CheckCircle2, Clock3, XCircle } from "lucide-react";
import { useEffect } from "react";
import { Link, useNavigate, useSearchParams } from "react-router";

import { verifyPayment } from "../../api/checkout";
import { getApiError } from "../../lib/errors";

function PaymentCallbackPage() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [searchParams] = useSearchParams();

  const reference =
    searchParams.get("reference") || searchParams.get("trxref") || "";

  const {
    data: payment,
    isPending,
    isError,
    error,
  } = useQuery({
    queryKey: ["payment-verification", reference],
    queryFn: () => verifyPayment(reference),
    enabled: Boolean(reference),
    retry: false,
    refetchOnWindowFocus: false,
  });

  const paymentSuccessful =
    payment?.status === "successful" || payment?.status === "success";

  const orderNumber = payment?.order_number;

  useEffect(() => {
    if (!paymentSuccessful || !orderNumber) {
      return undefined;
    }

    queryClient.invalidateQueries({
      queryKey: ["orders"],
    });

    queryClient.invalidateQueries({
      queryKey: ["order", orderNumber],
    });

    queryClient.invalidateQueries({
      queryKey: ["cart"],
    });

    const redirectTimer = window.setTimeout(() => {
      navigate(`/account/orders/${orderNumber}`, {
        replace: true,
      });
    }, 1200);

    return () => {
      window.clearTimeout(redirectTimer);
    };
  }, [navigate, orderNumber, paymentSuccessful, queryClient]);

  const missingReference = !reference;
  const isVerifying = Boolean(reference) && isPending;

  if (isVerifying) {
    return (
      <section className="page-container flex min-h-[65vh] items-center justify-center py-12 text-center">
        <div className="max-w-lg">
          <Clock3 className="mx-auto size-14 animate-pulse text-neutral-800" />

          <h1 className="mt-6 text-3xl font-bold">Verifying payment</h1>

          <p className="mt-3 text-neutral-600">
            Please keep this page open while we confirm your payment.
          </p>
        </div>
      </section>
    );
  }

  if (missingReference || isError) {
    return (
      <section className="page-container flex min-h-[65vh] items-center justify-center py-12 text-center">
        <div className="max-w-lg">
          <XCircle className="mx-auto size-14 text-red-700" />

          <h1 className="mt-6 text-3xl font-bold">
            Payment verification failed
          </h1>

          <p className="mt-3 text-neutral-600">
            {missingReference
              ? "The payment reference is missing from the callback URL."
              : getApiError(error, "We could not verify this payment.")}
          </p>

          <Link to="/account/orders" className="button-primary mt-7">
            View my orders
          </Link>
        </div>
      </section>
    );
  }

  if (paymentSuccessful) {
    return (
      <section className="page-container flex min-h-[65vh] items-center justify-center py-12 text-center">
        <div className="max-w-lg">
          <CheckCircle2 className="mx-auto size-14 text-green-700" />

          <h1 className="mt-6 text-3xl font-bold">Payment confirmed</h1>

          <p className="mt-3 text-neutral-600">
            Your payment was successful. Redirecting you to your order details…
          </p>

          {orderNumber && (
            <Link
              to={`/account/orders/${orderNumber}`}
              replace
              className="button-primary mt-7"
            >
              View order details
            </Link>
          )}
        </div>
      </section>
    );
  }

  return (
    <section className="page-container flex min-h-[65vh] items-center justify-center py-12 text-center">
      <div className="max-w-lg">
        <XCircle className="mx-auto size-14 text-amber-700" />

        <h1 className="mt-6 text-3xl font-bold">Payment not confirmed</h1>

        <p className="mt-3 text-neutral-600">
          Paystack has not confirmed this payment as successful. Check the order
          before trying again.
        </p>

        <Link
          to={
            orderNumber ? `/account/orders/${orderNumber}` : "/account/orders"
          }
          className="button-primary mt-7"
        >
          View order
        </Link>
      </div>
    </section>
  );
}

export default PaymentCallbackPage;
