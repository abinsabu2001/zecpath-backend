from rest_framework.permissions import BasePermission
from .subscription_utils import get_active_subscription


class IsAdminUser(BasePermission):
    def has_permission(self, request, view):
        return (
            request.user.is_authenticated
            and request.user.role == "Admin"
        )


class IsEmployerUser(BasePermission):
    def has_permission(self, request, view):
        return (
            request.user.is_authenticated
            and request.user.role == "Employer"
        )


class IsCandidateUser(BasePermission):
    def has_permission(self, request, view):
        return (
            request.user.is_authenticated
            and request.user.role == "Candidate"
        )


class HasActiveSubscription(BasePermission):
    """
    Allows access only to users with an active subscription.
    """

    message = "An active subscription is required to access this feature."

    def has_permission(self, request, view):

        if not request.user.is_authenticated:
            return False

        subscription = get_active_subscription(request.user)

        return subscription is not None        


class HasAIAnalyticsAccess(BasePermission):
    """
    Allows access only to users whose subscription
    includes AI analytics.
    """

    message = "AI analytics are not available on your current plan."

    def has_permission(self, request, view):

        if not request.user.is_authenticated:
            return False

        subscription = get_active_subscription(request.user)

        if not subscription:
            return False

        return subscription.plan.ai_analytics        


class IsPremiumEmployer(BasePermission):
    """
    Allows access only to employers with an active
    subscription that includes AI analytics.
    """

    message = "Premium recruiter subscription is required."

    def has_permission(self, request, view):

        if not request.user.is_authenticated:
            return False

        if request.user.role != "Employer":
            return False

        subscription = get_active_subscription(request.user)

        if not subscription:
            return False

        return subscription.plan.ai_analytics        