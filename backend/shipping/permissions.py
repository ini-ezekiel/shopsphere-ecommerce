from rest_framework.permissions import (
    BasePermission,
)


class IsActiveStaff(BasePermission):
    message = "Only active staff members can manage " "order fulfilment."

    def has_permission(self, request, view):
        user = request.user

        return bool(user and user.is_authenticated and user.is_active and user.is_staff)
