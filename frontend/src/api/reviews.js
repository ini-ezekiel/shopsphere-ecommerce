import apiClient from "./client";

export async function getProductReviews(productSlug, params = {}) {
  const { data } = await apiClient.get(
    `/catalog/products/${productSlug}/reviews/`,
    { params },
  );
  return data;
}

export async function createProductReview(productSlug, payload) {
  const { data } = await apiClient.post(
    `/catalog/products/${productSlug}/reviews/`,
    payload,
  );
  return data;
}
