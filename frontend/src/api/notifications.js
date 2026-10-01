import apiClient from "./client";

export async function getNotifications(params = {}) {
    const { data } = await apiClient.get(
        "/notifications/",
        {
            params,
        },
    );

    return data;
}

export async function getUnreadNotificationCount() {
    const { data } = await apiClient.get(
        "/notifications/unread-count/",
    );

    return data;
}

export async function markNotificationAsRead(
    notificationId,
) {
    const { data } = await apiClient.patch(
        `/notifications/${notificationId}/read/`,
    );

    return data;
}

export async function markAllNotificationsAsRead() {
    const { data } = await apiClient.post(
        "/notifications/read-all/",
    );

    return data;
}