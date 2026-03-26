"""
resume_analyzer.py
Uses Gemini API to score resume against job description and suggest improvements.
"""

import google.generativeai as genai
import json
import re


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
    model = genai.GenerativeModel("gemini-flash-latest")

    prompt = f"""You are an expert ATS (Applicant Tracking System) and professional resume reviewer.

Analyze the following resume against the job description and provide a comprehensive evaluation.

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
    {{
      "section": "<section name>",
      "issue": "<what's wrong>",
      "fix": "<exactly how to fix it>"
    }}
  ],
  "ats_verdict": "<PASS or FAIL>",
  "summary": "<2-3 sentence overall assessment>"
}}"""

    response = model.generate_content(prompt)

    raw = response.text.strip()
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
    model = genai.GenerativeModel("gemini-flash-latest")
    
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

Provide a concise, helpful answer that directly addresses their question using the context above.
"""
    try:
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        return f"I'm sorry, I couldn't process your question at the moment. ({str(e)})"


def generate_improved_resume(resume_text: str, analysis: dict, job_description: str, chat_history: list = None) -> dict:
    """
    Generate improved resume content based on analysis.
    Returns structured resume data for PDF generation.
    """
    model = genai.GenerativeModel("gemini-flash-latest")

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

    response = model.generate_content(prompt)

    raw = response.text.strip()
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
