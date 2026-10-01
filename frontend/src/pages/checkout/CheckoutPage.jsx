import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { useNavigate } from "react-router";
import { toast } from "sonner";

import { getCart } from "../../api/cart";
import {
  createAddress,
  createOrder,
  getAddresses,
  getDeliveryLocations,
  initializePayment,
} from "../../api/checkout";
import { getApiError } from "../../lib/errors";
import { formatNaira } from "../../lib/format";

function CheckoutPage() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [selectedAddressId, setSelectedAddressId] = useState("");
  const [showAddressForm, setShowAddressForm] = useState(false);
  const [selectedState, setSelectedState] = useState("");
  const [selectedLocationId, setSelectedLocationId] = useState("");

  const { data: cart } = useQuery({ queryKey: ["cart"], queryFn: getCart });
  const { data: addresses = [], isPending: addressesPending } = useQuery({
    queryKey: ["addresses"],
    queryFn: getAddresses,
  });
  const { data: locations = [] } = useQuery({
    queryKey: ["delivery-locations"],
    queryFn: getDeliveryLocations,
  });

  const addressMutation = useMutation({
    mutationFn: createAddress,
    onSuccess: async (address) => {
      await queryClient.invalidateQueries({ queryKey: ["addresses"] });
      setSelectedAddressId(String(address.id));
      setShowAddressForm(false);
      setSelectedState("");
      setSelectedLocationId("");
      toast.success("Delivery address saved.");
    },
    onError: (error) =>
      toast.error(getApiError(error, "Unable to save this address.")),
  });

  const checkoutMutation = useMutation({
    mutationFn: async (addressId) => {
      const order = await createOrder({
        shipping_address_id: Number(addressId),
        idempotency_key: crypto.randomUUID(),
      });
      const payment = await initializePayment(
        order.order_number,
        crypto.randomUUID(),
      );
      return { order, payment };
    },
    onSuccess: ({ order, payment }) => {
      queryClient.invalidateQueries({ queryKey: ["cart"] });
      queryClient.invalidateQueries({ queryKey: ["orders"] });

      if (payment.authorization_url) {
        window.location.assign(payment.authorization_url);
      } else {
        navigate(`/account/orders/${order.order_number}`);
      }
    },
    onError: (error) =>
      toast.error(getApiError(error, "Unable to start checkout.")),
  });

  function submitAddress(event) {
    event.preventDefault();
    const formData = new FormData(event.currentTarget);

    if (!selectedState || !selectedLocationId) {
      toast.error("Select your delivery state and city.");
      return;
    }

    addressMutation.mutate({
      label: formData.get("label"),
      recipient_name: String(formData.get("recipient_name") || "").trim(),
      phone_number: String(formData.get("phone_number") || "").trim(),
      address_line_1: String(formData.get("address_line_1") || "").trim(),
      address_line_2: String(formData.get("address_line_2") || "").trim(),
      landmark: String(formData.get("landmark") || "").trim(),
      postal_code: String(formData.get("postal_code") || "").trim(),
      delivery_location_id: Number(selectedLocationId),
      is_default: formData.get("is_default") === "on",
    });
  }

  function toggleAddressForm() {
    setShowAddressForm((current) => {
      const nextValue = !current;

      if (nextValue) {
        setSelectedAddressId("");
        setSelectedState("");
        setSelectedLocationId("");
      }

      return nextValue;
    });
  }

  function selectSavedAddress(addressId) {
    setSelectedAddressId(addressId);
    setShowAddressForm(false);
    setSelectedState("");
    setSelectedLocationId("");
  }

  const states = [...new Set(locations.map((location) => location.state))];
  const cities = locations.filter(
    (location) => location.state === selectedState,
  );
  const selectedAddress = addresses.find(
    (address) => String(address.id) === selectedAddressId,
  );
  const shippingFee = Number(
    selectedAddress?.delivery_location?.shipping_fee || 0,
  );
  const subtotal = Number(cart?.total || 0);
  const total = subtotal + shippingFee;

  return (
    <section className="page-container py-10 lg:py-14">
      <p className="eyebrow">Secure checkout</p>
      <h1 className="mt-2 text-4xl font-bold tracking-tight">
        Delivery and payment
      </h1>

      <div className="mt-9 grid gap-10 lg:grid-cols-[1fr_380px]">
        <div>
          <div className="flex items-center justify-between gap-4">
            <h2 className="text-xl font-bold">Delivery address</h2>
            <button
              type="button"
              onClick={toggleAddressForm}
              className="button-secondary"
            >
              {showAddressForm ? "Cancel" : "Add address"}
            </button>
          </div>

          {showAddressForm && (
            <form
              onSubmit={submitAddress}
              className="mt-5 grid gap-4 rounded-2xl border border-neutral-200 p-5 sm:grid-cols-2"
            >
              <label className="form-label">
                Label
                <select name="label" className="field">
                  <option value="home">Home</option>
                  <option value="work">Work</option>
                  <option value="other">Other</option>
                </select>
              </label>
              <label className="form-label">
                State
                <select
                  name="state"
                  value={selectedState}
                  onChange={(event) => {
                    setSelectedState(event.target.value);
                    setSelectedLocationId("");
                  }}
                  required
                  className="field"
                >
                  <option value="">Select a state</option>
                  {states.map((state) => (
                    <option key={state} value={state}>
                      {state}
                    </option>
                  ))}
                </select>
              </label>
              <label className="form-label">
                City
                <select
                  name="delivery_location_id"
                  value={selectedLocationId}
                  onChange={(event) =>
                    setSelectedLocationId(event.target.value)
                  }
                  required
                  disabled={!selectedState}
                  className="field disabled:cursor-not-allowed disabled:bg-neutral-100 disabled:text-neutral-500"
                >
                  <option value="">
                    {selectedState ? "Select a city" : "Select a state first"}
                  </option>
                  {cities.map((location) => (
                    <option key={location.id} value={location.id}>
                      {location.city}
                    </option>
                  ))}
                </select>
              </label>
              <label className="form-label">
                Recipient name
                <input name="recipient_name" required className="field" />
              </label>
              <label className="form-label">
                Phone number
                <input
                  name="phone_number"
                  placeholder="08012345678"
                  required
                  className="field"
                />
              </label>
              <label className="form-label sm:col-span-2">
                Address
                <input name="address_line_1" required className="field" />
              </label>
              <label className="form-label">
                Additional address details
                <input name="address_line_2" className="field" />
              </label>
              <label className="form-label">
                Landmark
                <input name="landmark" className="field" />
              </label>
              <label className="form-label">
                Postal code
                <input name="postal_code" className="field" />
              </label>
              <label className="mt-7 flex items-center gap-2 text-sm">
                <input
                  name="is_default"
                  type="checkbox"
                  className="size-4 accent-black"
                />{" "}
                Use as default
              </label>
              <button
                disabled={addressMutation.isPending || !selectedLocationId}
                className="button-primary sm:col-span-2"
              >
                {addressMutation.isPending ? "Saving…" : "Save address"}
              </button>
            </form>
          )}

          <div className="mt-5 grid gap-3">
            {addressesPending && (
              <p className="text-neutral-600">Loading addresses…</p>
            )}
            {!addressesPending &&
              addresses.length === 0 &&
              !showAddressForm && (
                <p className="rounded-xl bg-neutral-100 p-5 text-neutral-600">
                  Add a delivery address to continue.
                </p>
              )}
            {addresses.map((address) => (
              <label
                key={address.id}
                className={`flex cursor-pointer gap-4 rounded-2xl border p-5 ${selectedAddressId === String(address.id) ? "border-black bg-neutral-50" : "border-neutral-200"}`}
              >
                <input
                  type="radio"
                  name="shipping_address"
                  value={address.id}
                  checked={selectedAddressId === String(address.id)}
                  onChange={(event) => selectSavedAddress(event.target.value)}
                  className="mt-1 size-4 accent-black"
                />
                <span>
                  <span className="font-bold">{address.recipient_name}</span>
                  <span className="mt-1 block text-sm leading-6 text-neutral-600">
                    {address.address_line_1}, {address.delivery_location.city},{" "}
                    {address.delivery_location.state}
                  </span>
                  <span className="mt-1 block text-sm text-neutral-500">
                    {address.phone_number}
                  </span>
                </span>
              </label>
            ))}
          </div>
        </div>

        <aside className="h-fit rounded-2xl bg-neutral-950 p-6 text-white lg:sticky lg:top-28">
          <h2 className="text-xl font-bold">Order summary</h2>
          <div className="mt-5 space-y-3 border-b border-white/15 pb-5 text-sm text-neutral-300">
            {cart?.items?.map((item) => (
              <div key={item.id} className="flex justify-between gap-4">
                <span>
                  {item.quantity} × {item.variant.product_name}
                </span>
                <span>{formatNaira(item.subtotal)}</span>
              </div>
            ))}
          </div>
          <div className="mt-5 space-y-3 text-sm">
            <div className="flex justify-between text-neutral-300">
              <span>Subtotal</span>
              <span>{formatNaira(subtotal)}</span>
            </div>

            {selectedAddress && (
              <div className="flex justify-between text-neutral-300">
                <span>Shipping</span>
                <span>{formatNaira(shippingFee)}</span>
              </div>
            )}

            <div className="flex justify-between border-t border-white/15 pt-4 text-lg font-bold text-white">
              <span>Total</span>
              <span>{formatNaira(selectedAddress ? total : subtotal)}</span>
            </div>
          </div>
          <button
            type="button"
            disabled={
              !selectedAddress ||
              !cart?.items?.length ||
              checkoutMutation.isPending ||
              showAddressForm
            }
            onClick={() => checkoutMutation.mutate(selectedAddress.id)}
            className="mt-6 min-h-12 w-full rounded-full bg-white px-5 font-bold text-black hover:bg-neutral-200 disabled:cursor-not-allowed disabled:opacity-50"
          >
            {checkoutMutation.isPending
              ? "Preparing payment…"
              : "Proceed to payment"}
          </button>
        </aside>
      </div>
    </section>
  );
}

export default CheckoutPage;
