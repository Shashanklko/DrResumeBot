"""
resume_analyzer.py
Uses Gemini API to score resume against job description and suggest improvements.
"""

import google.generativeai as genai
import json
import re
from google.api_core import exceptions


def call_gemini_with_fallback(prompt: str) -> str:
    """
    Attempts to generate content with gemini-3.1-flash-lite-preview (High Quota: 500 RPD).
    Falls back to gemini-2.5-flash if needed.
    """
    try:
        # Try latest high-quota model first
        model = genai.GenerativeModel("gemini-3.1-flash-lite-preview")
        response = model.generate_content(prompt)
        return response.text.strip()
    except exceptions.ResourceExhausted:
        # Fallback to 2.5-flash if 3.1 hits quota
        print("ALERT: gemini-3.1-flash-lite quota reached. Falling back to gemini-2.5-flash.")
        model = genai.GenerativeModel("gemini-2.5-flash")
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        # Re-raise or handle other errors locally in functions
        raise e


def analyze_resume(resume_text: str, job_description: str, benchmark: int = 70) -> dict:
    """
    Analyze resume against job description using Gemini.
    Returns: {
        score: int,
        benchmark: int,
        passed: bool,
        strengths: list,
        weaknesses: list,
        suggestions: list,
        improved_resume: str,
        section_scores: dict
    }
    """
    prompt = f"""You are an expert ATS (Applicant Tracking System) and professional resume reviewer.

Analyze the following resume against the job description with maximum ATS rigor.

IMPORTANT LOGIC RULES:
1. **IGNORE ALL PROJECT DATES**: Do not flag future dates or missing dates as errors.
2. **CHECK EVERY PROJECT**: You must iterate over every single project in the resume and evaluate its technical depth and business impact.
3. **HARDER SCORING**: Be critical. An 'Average' score is 50-60. A 'Passed' score (70+) requires quantifiable metrics (e.g., %, $, hours) and high-impact action verbs.
4. **MANDATE 5 SUGGESTIONS**: You must provide exactly 5 high-impact suggestions across different sections.

=== JOB DESCRIPTION ===
{job_description}

=== RESUME ===
{resume_text}

Respond ONLY with a valid JSON object (no markdown, no explanation outside JSON) with this exact structure:
{{
  "overall_score": <integer 0-100>,
  "section_scores": {{
    "skills_match": <0-100>,
    "experience_relevance": <0-100>,
    "education_fit": <0-100>,
    "keywords_ats": <0-100>,
    "formatting_clarity": <0-100>
  }},
  "strengths": ["<list of 3-5 specific strengths>"],
  "weaknesses": ["<list of 3-5 specific weaknesses>"],
  "missing_keywords": ["<list of important keywords from JD missing in resume>"],
  "suggestions": [
    {{ "section": "<section 1>", "issue": "<issue 1>", "fix": "<fix 1>" }},
    {{ "section": "<section 2>", "issue": "<issue 2>", "fix": "<fix 2>" }},
    {{ "section": "<section 3>", "issue": "<issue 3>", "fix": "<fix 3>" }},
    {{ "section": "<section 4>", "issue": "<issue 4>", "fix": "<fix 4>" }},
    {{ "section": "<section 5>", "issue": "<issue 5>", "fix": "<fix 5>" }}
  ],
  "ats_verdict": "<PASS or FAIL>",
  "summary": "<2-3 sentence overall assessment>"
}}"""
    
    raw = call_gemini_with_fallback(prompt)
    # Strip any accidental markdown
    raw = re.sub(r"```json|```", "", raw).strip()
    try:
        result = json.loads(raw)
    except json.JSONDecodeError:
        result = {
            "overall_score": 0,
            "section_scores": {},
            "strengths": ["Could not parse response"],
            "weaknesses": ["Could not parse response"],
            "missing_keywords": [],
            "suggestions": [],
            "ats_verdict": "FAIL",
            "summary": "Error parsing JSON from API."
        }
        
    result["benchmark"] = benchmark
    result["passed"] = result.get("overall_score", 0) >= benchmark
    return result


def answer_counter_question(question: str, resume_text: str, jd_text: str, analysis: dict, chat_history: list = None) -> str:
    """
    Answer user's question about the resume analysis.
    """
    model = genai.GenerativeModel("gemini-2.0-flash")
    
    history_str = ""
    if chat_history:
        for msg in chat_history:
            role = "User" if msg["role"] == "user" else "AI"
            history_str += f"{role}: {msg['content']}\n"
            
    analysis_summary = (
        f"Score: {analysis.get('overall_score', 0)}\n"
        f"Strengths: {', '.join(analysis.get('strengths', []))}\n"
        f"Weaknesses: {', '.join(analysis.get('weaknesses', []))}\n"
        f"Missing Keywords: {', '.join(analysis.get('missing_keywords', []))}\n"
    )

    prompt = f"""You are an expert ATS and professional resume reviewer.
The user is asking a question regarding their resume analysis, job description, and your suggestions. You need to answer them in a helpful, conversational, and constructive tone.

=== BACKGROUND CONTEXT ===
Job Description:
{jd_text}

Original Resume:
{resume_text}

Analysis Review:
{analysis_summary}

=== PREVIOUS CONVERSATION ===
{history_str}

=== USER QUESTION ===
{question}

=== RESPONSE STRUCTURE ===
Provide a professional, highly structured answer using the following sections:
1. **Strategic Pivot**: How specifically to re-frame the existing experience for this JD.
2. **Key Action Points**: Detailed bullet points (bold headers) on Skills, Impact, and JD Alignment.
3. **Professional Verdict**: A clear summary of the candidate's standing.

Use bolding and bullet points for high readability. Ignore any future-dated project discrepancies.
"""
    try:
        return call_gemini_with_fallback(prompt)
    except Exception as e:
        return f"I'm sorry, I couldn't process your question at the moment. ({str(e)})"


def generate_improved_resume(resume_text: str, analysis: dict, job_description: str, chat_history: list = None, user_instruction: str = "") -> dict:
    """
    Generate improved resume content based on analysis and optional user instructions.
    Returns structured resume data for PDF generation.
    """

    suggestions_text = "\n".join([
        f"- [{s.get('section', 'General')}] {s.get('fix', '')}" for s in analysis.get("suggestions", [])
    ])
    missing_kw = ", ".join(analysis.get("missing_keywords", []))
    
    chat_str = "None"
    if chat_history:
        chat_str_lines = []
        for msg in chat_history:
            role = "User" if msg["role"] == "user" else "AI"
            chat_str_lines.append(f"{role}: {msg['content']}")
        chat_str = "\n".join(chat_str_lines)

    prompt = f"""You are an expert resume writer. Rewrite and improve the following resume based on the analysis feedback.

=== ORIGINAL RESUME ===
{resume_text}

=== JOB DESCRIPTION ===
{job_description}

=== IMPROVEMENTS TO MAKE ===
{suggestions_text}

=== MISSING KEYWORDS TO ADD ===
{missing_kw}

=== USER REQUESTS (FROM CHAT INSTRUCTIONS) ===
Incorporate these specific requests from the user's chat, overrides any previous suggestions if they conflict:
{chat_str}

Respond ONLY with a valid JSON object (no markdown) with this structure:
{{
  "name": "<full name>",
  "email": "<email>",
  "phone": "<phone>",
  "linkedin": "<linkedin url or empty>",
  "location": "<city, country>",
  "tagline": "<1 line professional tagline matching the JD>",
  "summary": "<3-4 sentence professional summary with keywords>",
  "experience": [
    {{
      "title": "<job title>",
      "company": "<company>",
      "duration": "<dates>",
      "bullets": ["<achievement 1>", "<achievement 2>", "<achievement 3>"]
    }}
  ],
  "education": [
    {{
      "degree": "<degree>",
      "institution": "<school>",
      "year": "<year>",
      "details": "<optional: GPA, honors, etc>"
    }}
  ],
  "skills": {{
    "technical": ["<skill1>", "<skill2>"],
    "soft": ["<skill1>", "<skill2>"],
    "tools": ["<tool1>", "<tool2>"]
  }},
  "certifications": ["<cert 1>", "<cert 2>"],
  "projects": [
    {{
      "name": "<project>",
      "description": "<1-2 lines impact>",
      "tech": "<technologies used>"
    }}
  ],
  "changes_made": ["<change 1>", "<change 2>", "<change 3>"]
}}"""

    raw = call_gemini_with_fallback(prompt)
    raw = re.sub(r"```json|```", "", raw).strip()
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {
            "name": "Error Generating Improvement",
            "experience": [],
            "education": [],
            "skills": {},
            "changes_made": ["Error parsing output"]
        }


def generate_simple_resume(resume_text: str) -> dict:
    """
    Cleaner and structures resume data into the standard JSON schema without JD analysis.
    Focus: Professional tone and structure only.
    """
    prompt = f"""You are an expert resume writer. Structure the following resume text into a professional, high-impact JSON format.
    
    === RESUME TEXT ===
    {resume_text}
    
    STRICT RULES:
    1. Organize the data into the JSON schema provided below.
    2. Professionalize the language: use strong action verbs (e.g., 'Spearheaded', 'Optimized', 'Engineered').
    3. If content is missing, leave the field empty or use professional placeholders.
    4. Respond ONLY with the JSON object.

    JSON STRUCTURE:
    {{
      "name": "<full name>",
      "email": "<email>",
      "phone": "<phone>",
      "linkedin": "<linkedin url or empty>",
      "location": "<city, country>",
      "tagline": "<1 line professional tagline (e.g. Senior Software Engineer)>",
      "summary": "<3-4 sentence professional summary>",
      "experience": [
        {{
          "title": "<job title>",
          "company": "<company>",
          "duration": "<dates>",
          "bullets": ["<achievement 1>", "<achievement 2>", "<achievement 3>"]
        }}
      ],
      "education": [
        {{
          "degree": "<degree>",
          "institution": "<school>",
          "year": "<year>",
          "details": "<optional: GPA, honors, etc>"
        }}
      ],
      "skills": {{
        "technical": ["<skill1>", "<skill2>"],
        "soft": ["<skill1>", "<skill2>"],
        "tools": ["<tool1>", "<tool2>"]
      }},
      "certifications": ["<cert 1>", "<cert 2>"],
      "projects": [
        {{
          "name": "<project name>",
          "description": "<1-2 lines impact>",
          "tech": "<tech stack>"
        }}
      ],
      "changes_made": ["Formatted for professional design", "Optimized action verbs", "Structured for ATS compliance"]
    }}"""

    raw = call_gemini_with_fallback(prompt)
    raw = re.sub(r"```json|```", "", raw).strip()
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {"name": "Error during formatting", "experience": [], "education": [], "skills": {}}
