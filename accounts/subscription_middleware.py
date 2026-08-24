from django.http import JsonResponse

from .subscription_utils import get_active_subscription


class SubscriptionMiddleware:
    """
    Checks subscription access for selected premium API paths.
    """

    PREMIUM_PATHS = [
        "/api/jobs/create/",
        "/api/recruiter-role-analytics/",
    ]

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):

        # Only check authenticated users
        if request.user.is_authenticated:

            # Check only selected premium endpoints
            if request.path in self.PREMIUM_PATHS:

                subscription = get_active_subscription(request.user)

                if not subscription:
                    return JsonResponse(
                        {
                            "message": "An active subscription is required to access this feature."
                        },
                        status=403
                    )

        response = self.get_response(request)

        return response