from rest_framework.permissions import BasePermission


class IsActivePaymentStaff(BasePermission):
    message = "Only active staff members can manage refunds."

    def has_permission(self, request, view):
        user = request.user

        return bool(user and user.is_authenticated and user.is_active and user.is_staff)
