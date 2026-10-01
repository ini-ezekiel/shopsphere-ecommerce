import apiClient from "./client";

export async function getProducts(params = {}) {
    const response = await apiClient.get("/catalog/products/", {
        params,
    });

    return response.data;
}

export async function getProduct(slug) {
    const response = await apiClient.get(`/catalog/products/${slug}/`);

    return response.data;
}

export async function getCategories() {
    const response = await apiClient.get("/catalog/categories/");
    const data = response.data;

    return Array.isArray(data) ? data : (data.results ?? []);
}

export async function getBrands() {
    const response = await apiClient.get("/catalog/brands/");
    const data = response.data;

    return Array.isArray(data) ? data : (data.results ?? []);
}