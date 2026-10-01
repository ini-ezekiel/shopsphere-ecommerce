/* eslint-disable react-refresh/only-export-components */
import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from "react";

import {
  getNotifications,
  getUnreadNotificationCount,
  markAllNotificationsAsRead,
  markNotificationAsRead,
} from "../../api/notifications";
import { useAuth } from "../auth/AuthContext";

const NotificationContext = createContext(null);

export function NotificationProvider({ children }) {
  const { isAuthenticated, isAuthLoading } = useAuth();

  const [notifications, setNotifications] = useState([]);
  const [unreadCount, setUnreadCount] = useState(0);
  const [isNotificationLoading, setIsNotificationLoading] = useState(false);
  const [isMarkingAllRead, setIsMarkingAllRead] = useState(false);
  const [updatingNotificationIds, setUpdatingNotificationIds] = useState([]);

  const refreshNotifications = useCallback(async () => {
    if (!isAuthenticated) {
      setNotifications([]);
      setUnreadCount(0);
      return;
    }

    setIsNotificationLoading(true);

    try {
      const [notificationData, countData] = await Promise.all([
        getNotifications(),
        getUnreadNotificationCount(),
      ]);

      const notificationItems = Array.isArray(notificationData)
        ? notificationData
        : notificationData.results || [];

      setNotifications(notificationItems);
      setUnreadCount(countData.unread_count || 0);
    } finally {
      setIsNotificationLoading(false);
    }
  }, [isAuthenticated]);

  useEffect(() => {
    const timeoutId = window.setTimeout(() => {
      if (isAuthLoading) {
        return;
      }

      if (!isAuthenticated) {
        setNotifications([]);
        setUnreadCount(0);
        return;
      }

      refreshNotifications().catch(() => {
        setNotifications([]);
        setUnreadCount(0);
      });
    }, 0);

    return () => {
      window.clearTimeout(timeoutId);
    };
  }, [isAuthenticated, isAuthLoading, refreshNotifications]);

  const markAsRead = useCallback(async (notificationId) => {
    const id = Number(notificationId);

    setUpdatingNotificationIds((current) => [...current, id]);

    try {
      const updatedNotification = await markNotificationAsRead(id);

      setNotifications((current) =>
        current.map((notification) =>
          notification.id === id
            ? {
                ...notification,
                ...updatedNotification,
              }
            : notification,
        ),
      );

      if (updatedNotification.marked_read) {
        setUnreadCount((current) => Math.max(0, current - 1));
      }

      return updatedNotification;
    } finally {
      setUpdatingNotificationIds((current) =>
        current.filter((notificationIdValue) => notificationIdValue !== id),
      );
    }
  }, []);

  const markAllAsRead = useCallback(async () => {
    setIsMarkingAllRead(true);

    try {
      const result = await markAllNotificationsAsRead();

      setNotifications((current) =>
        current.map((notification) => ({
          ...notification,
          is_read: true,
          read_at: notification.read_at || new Date().toISOString(),
        })),
      );

      setUnreadCount(0);

      return result;
    } finally {
      setIsMarkingAllRead(false);
    }
  }, []);

  const isNotificationUpdating = useCallback(
    (notificationId) =>
      updatingNotificationIds.includes(Number(notificationId)),
    [updatingNotificationIds],
  );

  const value = useMemo(
    () => ({
      notifications,
      unreadCount,
      isNotificationLoading,
      isMarkingAllRead,
      isNotificationUpdating,
      refreshNotifications,
      markAsRead,
      markAllAsRead,
    }),
    [
      notifications,
      unreadCount,
      isNotificationLoading,
      isMarkingAllRead,
      isNotificationUpdating,
      refreshNotifications,
      markAsRead,
      markAllAsRead,
    ],
  );

  return (
    <NotificationContext.Provider value={value}>
      {children}
    </NotificationContext.Provider>
  );
}

export function useNotifications() {
  const context = useContext(NotificationContext);

  if (!context) {
    throw new Error(
      "useNotifications must be used inside NotificationProvider.",
    );
  }

  return context;
}
