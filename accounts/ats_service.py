def calculate_ats_score(candidate_profile, job):
    """
    Calculate the ATS score for a candidate against a job.

    Scoring:
    - Skills: 50 marks
    - Experience: 30 marks
    - Education: 20 marks
    """
    score = 0

    # Skills (50 marks)
    candidate_skills = [
        skill.strip().lower()
        for skill in candidate_profile.skills.split(",")
    ]

    job_skills = [
        skill.strip().lower()
        for skill in job.skills.split(",")
    ]

    matched_skills = len(
        set(candidate_skills).intersection(job_skills)
    )

    if job_skills:
        score += (matched_skills / len(job_skills)) * 50

    # Experience (30 marks)
    if candidate_profile.experience >= job.experience:
        score += 30
    elif job.experience > 0:
        score += (
            candidate_profile.experience / job.experience
        ) * 30

    # Education (20 marks)
    if candidate_profile.education:
        score += 20

    return round(score, 2)


def check_eligibility(application):
    """
    Check whether the application meets the ATS threshold.
    """
    application.is_eligible = application.ats_score >= 70
    application.save()

    return application.is_eligible


def auto_shortlist(application):
    """
    Automatically shortlist or reject an application
    based on ATS eligibility.
    """
    check_eligibility(application)

    if application.is_eligible:
        application.status = "Shortlisted"
    else:
        application.status = "Rejected"

    application.auto_processed = True
    application.save()

    return application