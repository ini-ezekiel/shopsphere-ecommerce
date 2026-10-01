import apiClient from "./client";

export async function getWishlist(params = {}) {
  const { data } = await apiClient.get("/wishlist/", {
    params,
  });

  return data;
}

export async function addToWishlist(productId) {
  const { data } = await apiClient.post("/wishlist/", {
    product_id: productId,
  });

  return data;
}

export async function removeFromWishlist(wishlistItemId) {
  await apiClient.delete(
    `/wishlist/items/${wishlistItemId}/`,
  );
}