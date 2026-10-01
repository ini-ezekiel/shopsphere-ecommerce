import apiClient from "./client";

export async function getCart() {
  const { data } = await apiClient.get("/cart/");
  return data;
}

export async function addCartItem(payload) {
  const { data } = await apiClient.post("/cart/items/", payload);
  return data;
}

export async function updateCartItem(itemId, quantity) {
  const { data } = await apiClient.patch(`/cart/items/${itemId}/`, {
    quantity,
  });
  return data;
}

export async function removeCartItem(itemId) {
  await apiClient.delete(`/cart/items/${itemId}/`);
}

export async function clearCart() {
  await apiClient.delete("/cart/clear/");
}
