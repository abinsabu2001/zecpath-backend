def calculate_ats_score(candidate_profile, job):
    score = 0

    # ---------- Skills (50 Marks) ----------
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

    if len(job_skills) > 0:
        score += (matched_skills / len(job_skills)) * 50

    # ---------- Experience (30 Marks) ----------
    if candidate_profile.experience >= job.experience:
        score += 30
    elif job.experience > 0:
        score += (
            candidate_profile.experience /
            job.experience
        ) * 30

    # ---------- Education (20 Marks) ----------
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

    # Check eligibility first
    check_eligibility(application)

    if application.is_eligible:
        application.status = "Shortlisted"
    else:
        application.status = "Rejected"

    application.auto_processed = True
    application.save()

    return application    

from decouple import config
import time


class AIBridgeService:
    """
    Central service for AI and Voice integrations.
    """

    def get_api_key(self):
        return config("OPENAI_API_KEY")

    def text_to_speech(self, text):
        return {
            "status": "success",
            "message": f"Text converted to speech: {text}"
        }

    def speech_to_text(self, audio_file):
        return {
            "status": "success",
            "message": "Speech converted to text",
            "text": "Sample converted text"
        }

    def trigger_voice_call(self, phone_number):
        """
        Simulates a voice call with retry and error handling.
        """

        retries = 3

        for attempt in range(retries):
            try:

                api_key = self.get_api_key()

                if not api_key:
                    raise Exception("OpenAI API key not found")

                return {
                    "status": "success",
                    "message": f"Voice call triggered to {phone_number}",
                    "attempt": attempt + 1
                }

            except Exception as e:

                if attempt < retries - 1:
                    time.sleep(1)
                    continue

                return {
                    "status": "failed",
                    "message": str(e)
                }