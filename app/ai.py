import os
from anthropic import Anthropic
from dotenv import load_dotenv

load_dotenv()

client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

def score_job(cv_text: str, job_title: str, job_description: str) -> dict:
    prompt = f"""You are a career advisor. Score how well this CV matches the job.

CV:
{cv_text}

Job Title: {job_title}
Job Description: {job_description}

Respond in this exact format:
SCORE: (number 0-100)
REASON: (one sentence why)
MISSING: (one skill the CV lacks for this job)"""

    message = client.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=200,
        messages=[{"role": "user", "content": prompt}]
    )

    response = message.content[0].text
    lines = response.strip().split("\n")
    
    result = {"score": 0, "reason": "", "missing": ""}
    for line in lines:
        if line.startswith("SCORE:"):
            result["score"] = int(line.replace("SCORE:", "").strip())
        elif line.startswith("REASON:"):
            result["reason"] = line.replace("REASON:", "").strip()
        elif line.startswith("MISSING:"):
            result["missing"] = line.replace("MISSING:", "").strip()
    
    return result

def generate_cover_letter(cv_text: str, job_title: str, company: str, job_description: str) -> str:
    prompt = f"""Write a concise, professional cover letter for this job application.

CV:
{cv_text}

Job Title: {job_title}
Company: {company}
Job Description: {job_description}

Write a 3 paragraph cover letter. Be specific, not generic."""

    message = client.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=500,
        messages=[{"role": "user", "content": prompt}]
    )

    return message.content[0].text