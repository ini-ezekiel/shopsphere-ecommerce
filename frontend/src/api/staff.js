import apiClient from "./client";

export async function getStaffDashboard(
    period = "30d",
) {
    const { data } = await apiClient.get(
        "/staff/dashboard/summary/",
        {
            params: {
                period,
            },
        },
    );

    return data;
}

// Orders and fulfilment

export async function getStaffOrders(params = {}) {
    const { data } = await apiClient.get(
        "/staff/orders/",
        {
            params,
        },
    );

    return data;
}

export async function getStaffOrder(orderNumber) {
    const { data } = await apiClient.get(
        `/staff/orders/${orderNumber}/`,
    );

    return data;
}

export async function updateStaffOrderStatus(
    orderNumber,
    payload,
) {
    const { data } = await apiClient.patch(
        `/staff/orders/${orderNumber}/status/`,
        payload,
    );

    return data;
}

// Refunds

export async function initiateStaffRefund(
    paymentReference,
    reason,
) {
    const { data } = await apiClient.post(
        `/staff/payments/${paymentReference}/refund/`,
        {
            reason,
        },
    );

    return data;
}

// Products

export async function getStaffProducts(params = {}) {
    const { data } = await apiClient.get(
        "/staff/products/",
        {
            params,
        },
    );

    return data;
}

export async function getStaffProduct(productId) {
    const { data } = await apiClient.get(
        `/staff/products/${productId}/`,
    );

    return data;
}

export async function createStaffProduct(payload) {
    const { data } = await apiClient.post(
        "/staff/products/",
        payload,
    );

    return data;
}

export async function updateStaffProduct(
    productId,
    payload,
) {
    const { data } = await apiClient.patch(
        `/staff/products/${productId}/`,
        payload,
    );

    return data;
}

// Variants

export async function getStaffVariants(
    productId,
    params = {},
) {
    const { data } = await apiClient.get(
        `/staff/products/${productId}/variants/`,
        {
            params,
        },
    );

    return data;
}

export async function createStaffVariant(
    productId,
    payload,
) {
    const { data } = await apiClient.post(
        `/staff/products/${productId}/variants/`,
        payload,
    );

    return data;
}

export async function updateStaffVariant(
    variantId,
    payload,
) {
    const { data } = await apiClient.patch(
        `/staff/variants/${variantId}/`,
        payload,
    );

    return data;
}

// Inventory

export async function getStaffInventory(
    params = {},
) {
    const { data } = await apiClient.get(
        "/staff/inventory/",
        {
            params,
        },
    );

    return data;
}

export async function updateStaffInventory(
    inventoryId,
    payload,
) {
    const { data } = await apiClient.patch(
        `/staff/inventory/${inventoryId}/`,
        payload,
    );

    return data;
}

// Product images

export async function getStaffProductImages(
    productId,
) {
    const { data } = await apiClient.get(
        `/staff/products/${productId}/images/`,
    );

    return data;
}

export async function createStaffProductImage(
    productId,
    formData,
) {
    const { data } = await apiClient.post(
        `/staff/products/${productId}/images/`,
        formData,
    );

    return data;
}

export async function updateStaffProductImage(
    imageId,
    formData,
) {
    const { data } = await apiClient.patch(
        `/staff/product-images/${imageId}/`,
        formData,
    );

    return data;
}

export async function deleteStaffProductImage(
    imageId,
) {
    await apiClient.delete(
        `/staff/product-images/${imageId}/`,
    );
}

// Categories

export async function getStaffCategories(
    params = {},
) {
    const { data } = await apiClient.get(
        "/staff/categories/",
        {
            params,
        },
    );

    return data;
}

export async function createStaffCategory(payload) {
    const { data } = await apiClient.post(
        "/staff/categories/",
        payload,
    );

    return data;
}

export async function updateStaffCategory(
    categoryId,
    payload,
) {
    const { data } = await apiClient.patch(
        `/staff/categories/${categoryId}/`,
        payload,
    );

    return data;
}

// Brands

export async function getStaffBrands(params = {}) {
    const { data } = await apiClient.get(
        "/staff/brands/",
        {
            params,
        },
    );

    return data;
}

export async function createStaffBrand(payload) {
    const { data } = await apiClient.post(
        "/staff/brands/",
        payload,
    );

    return data;
}

export async function updateStaffBrand(
    brandId,
    payload,
) {
    const { data } = await apiClient.patch(
        `/staff/brands/${brandId}/`,
        payload,
    );

    return data;
}

// Reviews

export async function getStaffReviews(params = {}) {
    const { data } = await apiClient.get(
        "/staff/reviews/",
        {
            params,
        },
    );

    return data;
}

export async function getStaffReview(reviewId) {
    const { data } = await apiClient.get(
        `/staff/reviews/${reviewId}/`,
    );

    return data;
}

export async function updateStaffReview(
    reviewId,
    payload,
) {
    const { data } = await apiClient.patch(
        `/staff/reviews/${reviewId}/`,
        payload,
    );

    return data;
}

export async function getStaffRefunds(params = {}) {
    const response = await apiClient.get("/staff/refunds/", {
        params,
    });

    return response.data;
}


export async function getStaffProductVariants(
    productId,
    params = {},
) {
    const response = await apiClient.get(
        `/staff/products/${productId}/variants/`,
        { params },
    );

    return response.data;
}

export async function createStaffProductVariant(
    productId,
    payload,
) {
    const response = await apiClient.post(
        `/staff/products/${productId}/variants/`,
        payload,
    );

    return response.data;
}

export async function updateStaffProductVariant(
    variantId,
    payload,
) {
    const response = await apiClient.patch(
        `/staff/variants/${variantId}/`,
        payload,
    );

    return response.data;
}