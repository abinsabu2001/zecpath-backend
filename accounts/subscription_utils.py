from datetime import timedelta
from django.utils import timezone

from .models import UserSubscription


GRACE_PERIOD_DAYS = 3


def get_active_subscription(user):
    """
    Get the user's valid subscription.
    """

    subscription = (
        UserSubscription.objects
        .filter(
            user=user,
            status="ACTIVE"
        )
        .select_related("plan")
        .order_by("-created_at")
        .first()
    )

    if not subscription:
        return None

    if subscription.end_date:
        now = timezone.now()

        # Subscription is still active
        if now <= subscription.end_date:
            return subscription

        # Subscription is inside grace period
        grace_end = subscription.end_date + timedelta(
            days=GRACE_PERIOD_DAYS
        )

        if now <= grace_end:
            return subscription

        # Grace period is over
        subscription.status = "EXPIRED"
        subscription.save(update_fields=["status"])

        return None

    return subscription