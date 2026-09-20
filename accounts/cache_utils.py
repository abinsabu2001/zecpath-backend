from django.core.cache import cache

from .models import Job


def get_active_jobs():
    cache_key = "active_jobs"

    cached_jobs = cache.get(cache_key)

    if cached_jobs is not None:
        return cached_jobs

    jobs = list(
        Job.objects
        .filter(status=True)
        .values("id", "title", "created_at")
    )

    cache.set(cache_key, jobs, 300)

    return jobs