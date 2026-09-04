"""
AI-Powered CV Analysis & Job Matching Service using OpenAI API.
Enforces strict fairness guidelines and structured JSON schema evaluation.
"""

import json
import logging
import re
from django.conf import settings
from openai import OpenAI

logger = logging.getLogger(__name__)

# Structured Prompt enforcing Fairness Rules & Job Matching
SYSTEM_PROMPT = """You are an expert HR recruitment intelligence assistant specializing in objective, fair, and unbiased resume analysis.

Your goal is to analyze a candidate's CV text against a specific Job Vacancy specification and produce a structured JSON evaluation.

CRITICAL FAIRNESS AND ETHICAL GUIDELINES:
1. Evaluate ONLY job-related technical qualifications, demonstrable skills, relevant work experience, and educational credentials against the Job Vacancy requirements.
2. Under NO circumstances should you evaluate, factor in, or comment on personal or protected characteristics:
   - Gender, age, date of birth
   - Religion, race, ethnicity, nationality, origin
   - Marital status, family situation, sexual orientation
   - Photographs, physical appearance, disability
   - Residential address, postal code, or personal affiliations
3. The evaluation is strictly an HR decision-support tool; HR managers retain all final hiring decisions.

OUTPUT FORMAT:
You MUST respond with valid, parseable JSON matching this exact structure:
{
  "match_score": 85,
  "recommendation": "Strong Match", // Options: "Strong Match", "Moderate Match", "Weak Match"
  "matched_skills": [
    {
      "skill": "Python",
      "level": "Strong" // Options: "Strong", "Moderate", "Weak"
    }
  ],
  "missing_skills": [
    "Docker",
    "AWS"
  ],
  "experience": {
    "relevant_years": 3,
    "meets_requirement": true,
    "analysis_summary": "3 years relevant experience in backend software engineering"
  },
  "education": {
    "qualification": "B.Sc. in Computer Science",
    "meets_requirement": true,
    "analysis_summary": "Holds relevant degree meeting technical requirement"
  },
  "strengths": [
    "Strong backend development experience with Django",
    "Relevant database and REST API design skills"
  ],
  "missing_requirements": [
    "AWS cloud deployment experience not demonstrated in CV"
  ]
}
"""


def _generate_simulation_analysis(job_vacancy, cv_text):
    """
    Fallback deterministic heuristic analyzer used when OPENAI_API_KEY is not configured
    or when running in offline development/testing environments.
    """
    cv_lower = cv_text.lower()
    
    # Parse required skills from vacancy
    req_skills_raw = [
        s.strip() for s in re.split(r'[,;\n•\-\*]+', job_vacancy.required_skills)
        if s.strip()
    ]
    pref_skills_raw = [
        s.strip() for s in re.split(r'[,;\n•\-\*]+', job_vacancy.preferred_skills)
        if s.strip()
    ]
    all_target_skills = list(dict.fromkeys(req_skills_raw + pref_skills_raw))

    matched_skills = []
    missing_skills = []

    for skill in all_target_skills:
        skill_clean = skill.lower()
        if skill_clean in cv_lower:
            # Estimate level based on occurrences
            occurrences = cv_lower.count(skill_clean)
            level = "Strong" if occurrences >= 3 else ("Moderate" if occurrences >= 1 else "Weak")
            matched_skills.append({"skill": skill, "level": level})
        else:
            missing_skills.append(skill)

    total_skills = len(all_target_skills) or 1
    skill_ratio = len(matched_skills) / total_skills

    # Estimate match score
    match_score = int(min(100, max(20, round(skill_ratio * 70 + 20))))

    if match_score >= 75:
        recommendation = "Strong Match"
    elif match_score >= 50:
        recommendation = "Moderate Match"
    else:
        recommendation = "Weak Match"

    # Experience heuristic
    req_years = job_vacancy.required_experience_years
    meets_exp = True if req_years <= 2 or skill_ratio >= 0.5 else False
    est_years = max(req_years, int(req_years * skill_ratio + 1)) if meets_exp else max(0, req_years - 1)

    # Education heuristic
    edu_req = job_vacancy.educational_requirements or "Bachelor's Degree"
    has_bachelor = any(term in cv_lower for term in ['bachelor', 'b.sc', 'bsc', 'b.tech', 'undergraduate', 'degree', 'computer science', 'engineering'])
    has_master = any(term in cv_lower for term in ['master', 'm.sc', 'msc', 'mba', 'postgraduate'])
    
    qualification = "Master's Degree" if has_master else ("Bachelor's Degree" if has_bachelor else "Higher Education")
    meets_edu = True if (has_bachelor or has_master or not job_vacancy.educational_requirements) else False

    strengths = []
    if matched_skills:
        top_skills = [m['skill'] for m in matched_skills[:3]]
        strengths.append(f"Demonstrated proficiency in core skills: {', '.join(top_skills)}.")
    if meets_exp:
        strengths.append(f"Candidate meets the required experience threshold ({req_years}+ years).")
    if meets_edu:
        strengths.append(f"Educational qualifications align with position requirements.")
    if not strengths:
        strengths.append("Foundational technical background demonstrated in CV.")

    missing_reqs = []
    if missing_skills:
        missing_reqs.append(f"Missing required or preferred skills: {', '.join(missing_skills[:3])}.")
    if not meets_exp:
        missing_reqs.append(f"Requires {req_years} years of relevant industry experience.")

    return {
        "match_score": match_score,
        "recommendation": recommendation,
        "matched_skills": matched_skills,
        "missing_skills": missing_skills,
        "experience": {
            "relevant_years": est_years,
            "meets_requirement": meets_exp,
            "analysis_summary": f"Estimated {est_years} years of relevant experience identified."
        },
        "education": {
            "qualification": qualification,
            "meets_requirement": meets_edu,
            "analysis_summary": f"Qualification matches the stated requirement: {edu_req}."
        },
        "strengths": strengths,
        "missing_requirements": missing_reqs,
        "is_simulation": True
    }


def analyze_cv_with_ai(job_vacancy, cv_text):
    """
    Analyzes CV text against a JobVacancy using the OpenAI API.
    Returns: parsed dictionary matching the structured output format.
    """
    api_key = getattr(settings, 'OPENAI_API_KEY', '') or ''
    model_name = getattr(settings, 'OPENAI_MODEL', 'gpt-4o-mini') or 'gpt-4o-mini'

    # Check if API key is valid / configured
    if not api_key or api_key in ('your_openai_api_key_here', 'your_api_key_here', ''):
        logger.warning("OPENAI_API_KEY is not configured or is a placeholder. Using fallback heuristic simulation.")
        return _generate_simulation_analysis(job_vacancy, cv_text)

    # Prepare job vacancy information for AI
    job_prompt = f"""
JOB VACANCY DETAILS:
- Job Title: {job_vacancy.title}
- Department: {job_vacancy.department.name if job_vacancy.department else 'Not specified'}
- Job Description: {job_vacancy.description}
- Required Skills: {job_vacancy.required_skills}
- Preferred Skills: {job_vacancy.preferred_skills or 'None specified'}
- Required Experience: {job_vacancy.required_experience_years} years
- Educational Requirements: {job_vacancy.educational_requirements or 'None specified'}

CANDIDATE CV TEXT:
{cv_text}
"""

    try:
        client = OpenAI(api_key=api_key)
        response = client.chat.completions.create(
            model=model_name,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": job_prompt}
            ],
            response_format={"type": "json_object"},
            temperature=0.2,
        )

        content = response.choices[0].message.content
        data = json.loads(content)

        # Normalize and validate keys
        score = int(data.get("match_score", 50))
        score = max(0, min(100, score))
        data["match_score"] = score

        rec = data.get("recommendation", "Moderate Match")
        if rec not in ["Strong Match", "Moderate Match", "Weak Match"]:
            if score >= 75:
                rec = "Strong Match"
            elif score >= 50:
                rec = "Moderate Match"
            else:
                rec = "Weak Match"
        data["recommendation"] = rec

        if not isinstance(data.get("matched_skills"), list):
            data["matched_skills"] = []
        if not isinstance(data.get("missing_skills"), list):
            data["missing_skills"] = []
        if not isinstance(data.get("strengths"), list):
            data["strengths"] = []
        if not isinstance(data.get("missing_requirements"), list):
            data["missing_requirements"] = []

        if not isinstance(data.get("experience"), dict):
            data["experience"] = {
                "relevant_years": 0,
                "meets_requirement": False,
                "analysis_summary": "Experience information not clearly detailed."
            }

        if not isinstance(data.get("education"), dict):
            data["education"] = {
                "qualification": "Not Specified",
                "meets_requirement": False,
                "analysis_summary": "Education details not clearly stated."
            }

        data["is_simulation"] = False
        return data

    except Exception as e:
        logger.error(f"OpenAI API error during CV analysis: {str(e)}", exc_info=True)
        # Fallback to local heuristic analyzer if OpenAI API fails or encounters network/rate limits
        fallback_data = _generate_simulation_analysis(job_vacancy, cv_text)
        fallback_data["api_error_note"] = f"AI API encountered a temporary error: {str(e)}. Fallback analysis generated."
        return fallback_data
