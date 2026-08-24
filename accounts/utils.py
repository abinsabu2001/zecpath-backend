import re
from .skills import SKILLS


def extract_skills(text):
    found = []

    for skill in SKILLS:
        if re.search(r"\b" + re.escape(skill) + r"\b", text, re.IGNORECASE):
            found.append(skill)

    return found


def extract_experience(text):
    match = re.search(r'(\d+)\+?\s*(years|year)', text, re.IGNORECASE)

    if match:
        return match.group()

    return "Not Found"


def extract_education(text):
    education_list = [
        "MCA",
        "B.Tech",
        "BCA",
        "M.Tech",
        "B.Sc",
        "M.Sc",
        "MBA",
        "Diploma",
        "ITI"
    ]

    for edu in education_list:
        if re.search(r"\b" + re.escape(edu) + r"\b", text, re.IGNORECASE):
            return edu

    return "Not Found"