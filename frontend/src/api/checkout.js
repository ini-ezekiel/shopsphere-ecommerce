import apiClient from "./client";

export async function getDeliveryLocations() {
  const { data } = await apiClient.get("/delivery-locations/");
  return Array.isArray(data) ? data : (data.results ?? []);
}

export async function getAddresses() {
  const { data } = await apiClient.get("/shipping-addresses/");
  return Array.isArray(data) ? data : (data.results ?? []);
}

export async function createAddress(payload) {
  const { data } = await apiClient.post("/shipping-addresses/", payload);
  return data;
}

export async function createOrder(payload) {
  const { data } = await apiClient.post("/checkout/", payload);
  return data;
}

export async function initializePayment(orderNumber, idempotencyKey) {
  const { data } = await apiClient.post(
    `/orders/${orderNumber}/payments/initialize/`,
    { idempotency_key: idempotencyKey },
  );
  return data;
}

export async function verifyPayment(reference) {
  const { data } = await apiClient.post(`/payments/${reference}/verify/`);
  return data;
}
