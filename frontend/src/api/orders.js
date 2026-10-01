import apiClient from "./client";

export async function getOrders(params = {}) {
  const { data } = await apiClient.get("/orders/", { params });
  return data;
}

export async function getOrder(orderNumber) {
  const { data } = await apiClient.get(`/orders/${orderNumber}/`);
  return data;
}

export async function cancelOrder(orderNumber) {
  const { data } = await apiClient.post(`/orders/${orderNumber}/cancel/`);
  return data;
}
