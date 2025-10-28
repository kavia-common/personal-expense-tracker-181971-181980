from rest_framework.permissions import BasePermission


# PUBLIC_INTERFACE
class IsOwner(BasePermission):
    """Object-level permission that allows access only to the object's owner (instance.user)."""

    def has_object_permission(self, request, view, obj) -> bool:
        # Safe methods still require ownership
        return getattr(obj, "user_id", None) == getattr(request.user, "id", None)

    def has_permission(self, request, view) -> bool:
        # Require authentication for all methods
        return request.user and request.user.is_authenticated
