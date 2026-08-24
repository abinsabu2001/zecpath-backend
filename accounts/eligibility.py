from .models import CandidateProfile


def check_candidate_eligibility(application):
    """
    Returns True if the candidate is eligible
    for an AI interview call.
    """

    try:
        profile = CandidateProfile.objects.get(
            user=application.candidate,
            is_deleted=False
        )
    except CandidateProfile.DoesNotExist:
        return False

    # Rule 1 - ATS Score
    if application.ats_score < 20:
        return False

    # Rule 2 - Candidate must be shortlisted
    if application.status != "Shortlisted":
        return False

    # Rule 3 - Resume should exist
    if not profile.resume:
        return False

    return True