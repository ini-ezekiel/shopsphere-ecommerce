import { Bell, Check, CheckCheck } from "lucide-react";
import { Link } from "react-router";
import { toast } from "sonner";

import { useNotifications } from "../../features/notifications/NotificationContext";
import { getApiError } from "../../lib/errors";

function formatNotificationDate(value) {
  return new Intl.DateTimeFormat("en-NG", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

function NotificationsPage() {
  const {
    notifications,
    unreadCount,
    isNotificationLoading,
    isMarkingAllRead,
    isNotificationUpdating,
    markAsRead,
    markAllAsRead,
  } = useNotifications();

  async function handleMarkAsRead(notification) {
    if (notification.is_read) {
      return;
    }

    try {
      await markAsRead(notification.id);
    } catch (error) {
      toast.error(getApiError(error, "Unable to update the notification."));
    }
  }

  async function handleMarkAllAsRead() {
    try {
      const result = await markAllAsRead();

      toast.success(
        result.marked_read_count
          ? `${result.marked_read_count} notifications marked as read.`
          : "All notifications are already read.",
      );
    } catch (error) {
      toast.error(getApiError(error, "Unable to mark notifications as read."));
    }
  }

  if (isNotificationLoading) {
    return (
      <div>
        <h2 className="text-2xl font-bold">Notifications</h2>

        <p className="mt-4 text-neutral-600">Loading your notifications…</p>
      </div>
    );
  }

  return (
    <div>
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h2 className="text-2xl font-bold">Notifications</h2>

          <p className="mt-2 text-sm text-neutral-600">
            {unreadCount === 0
              ? "You have no unread notifications."
              : unreadCount === 1
                ? "You have 1 unread notification."
                : `You have ${unreadCount} unread notifications.`}
          </p>
        </div>

        {notifications.length > 0 && (
          <button
            type="button"
            onClick={handleMarkAllAsRead}
            disabled={unreadCount === 0 || isMarkingAllRead}
            className="button-secondary inline-flex items-center gap-2"
          >
            <CheckCheck className="size-4" />

            {isMarkingAllRead ? "Updating…" : "Mark all as read"}
          </button>
        )}
      </div>

      {notifications.length === 0 ? (
        <section className="mt-6 rounded-2xl border border-dashed border-neutral-300 px-6 py-14 text-center">
          <Bell className="mx-auto size-10 text-neutral-400" />

          <h3 className="mt-4 text-lg font-bold text-neutral-950">
            No notifications yet
          </h3>

          <p className="mx-auto mt-2 max-w-md text-sm leading-6 text-neutral-600">
            Updates about your payments, orders, shipping, delivery and refunds
            will appear here.
          </p>
        </section>
      ) : (
        <div className="mt-6 space-y-3">
          {notifications.map((notification) => {
            const content = (
              <>
                <div
                  className={`mt-1 flex size-10 shrink-0 items-center justify-center rounded-full ${
                    notification.is_read
                      ? "bg-neutral-100 text-neutral-500"
                      : "bg-black text-white"
                  }`}
                >
                  {notification.is_read ? (
                    <Check className="size-5" />
                  ) : (
                    <Bell className="size-5" />
                  )}
                </div>

                <div className="min-w-0 flex-1">
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <h3 className="font-bold text-neutral-950">
                      {notification.title}
                    </h3>

                    {!notification.is_read && (
                      <span className="rounded-full bg-red-100 px-2.5 py-1 text-xs font-bold text-red-700">
                        New
                      </span>
                    )}
                  </div>

                  <p className="mt-2 text-sm leading-6 text-neutral-600">
                    {notification.message}
                  </p>

                  <p className="mt-3 text-xs font-medium text-neutral-500">
                    {formatNotificationDate(notification.created_at)}
                  </p>
                </div>
              </>
            );

            const className = `flex gap-4 rounded-2xl border p-5 transition ${
              notification.is_read
                ? "border-neutral-200 bg-white"
                : "border-neutral-950 bg-neutral-50"
            }`;

            if (notification.link) {
              return (
                <Link
                  key={notification.id}
                  to={notification.link}
                  onClick={() => handleMarkAsRead(notification)}
                  className={`${className} hover:border-black`}
                >
                  {content}
                </Link>
              );
            }

            return (
              <button
                key={notification.id}
                type="button"
                onClick={() => handleMarkAsRead(notification)}
                disabled={
                  notification.is_read ||
                  isNotificationUpdating(notification.id)
                }
                className={`${className} w-full text-left disabled:cursor-default`}
              >
                {content}
              </button>
            );
          })}
        </div>
      )}
    </div>
  );
}

export default NotificationsPage;
