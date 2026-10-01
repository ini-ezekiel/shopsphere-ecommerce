import apiClient from "./client";

export async function getRefunds(params = {}) {
  const { data } = await apiClient.get(
    "/refunds/me/",
    {
      params,
    },
  );

  return data;
}

export async function getRefund(reference) {
  const { data } = await apiClient.get(
    `/refunds/${reference}/`,
  );

  return data;
}