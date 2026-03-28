"""
web_app.py — Flask Application Module
=====================================
Provides the API and static file serving for the React frontend.
Shared initialization (env/genai) is handled by main.py.
"""

import os
import sys
import uuid
import shutil
import tempfile
import logging
import io
from io import BytesIO
from pathlib import Path
from flask import Flask, request, jsonify, send_file, send_from_directory
from flask_cors import CORS
import google.generativeai as genai

# Import utilities from the current package
from utils.resume_analyzer import analyze_resume, generate_improved_resume, generate_simple_resume, answer_counter_question
from utils.pdf_generator import FORMATS as PDF_FORMATS
from utils.docx_generator import build_docx_cv
from utils.pdf_extractor import extract_resume_text
from utils.report_generator import build_review_report

logger = logging.getLogger("WEB")

app = Flask(__name__)
# Enable CORS for the frontend (Vercel/Local)
CORS(app, resources={r"/api/*": {"origins": "*"}})
# Optional: Serve from disk is disabled for split Vercel/Render deployment
# app.static_folder = '../frontend/dist'
# app.static_url_path = '/'

# Session-based storage for the web interface
WEB_DATA = {}
BENCHMARK = int(os.getenv("BENCHMARK_SCORE", 70))
MAX_FILE_MB = int(os.getenv("MAX_FILE_SIZE_MB", 5))

def _cleanup_session(sid):
    data = WEB_DATA.pop(sid, {})
    tmp = data.get("tmp_dir")
    if tmp and os.path.exists(tmp):
        shutil.rmtree(tmp, ignore_errors=True)

@app.route('/api/analyze', methods=['POST', 'OPTIONS'], strict_slashes=False)
def analyze():
    print(">>> [Web API] Received analysis request", flush=True)
    if 'resume' not in request.files:
        return jsonify({"error": "No resume file provided"}), 400
    
    resume_file = request.files['resume']
    jd_text = request.form.get('jd_text', '').strip()
    
    if len(jd_text) < 30:
        return jsonify({"error": "Job description is too short"}), 400

    # Create session ID
    sid = str(uuid.uuid4())
    tmp_dir = tempfile.mkdtemp(prefix=f"resumeweb_{sid}_")
    
    ext = Path(resume_file.filename).suffix.lower()
    if ext not in (".pdf", ".docx", ".doc", ".txt"):
        shutil.rmtree(tmp_dir, ignore_errors=True)
        return jsonify({"error": "Unsupported file format"}), 400
        
    resume_path = os.path.join(tmp_dir, f"resume{ext}")
    resume_file.save(resume_path)
    
    try:
        resume_text = extract_resume_text(resume_path)
        if len(resume_text.strip()) < 50:
            shutil.rmtree(tmp_dir, ignore_errors=True)
            return jsonify({"error": "Could not extract text from resume"}), 400
            
        print(f">>> [Web API] Analyzing with Gemini...", flush=True)
        analysis = analyze_resume(resume_text, jd_text, BENCHMARK)
        
        WEB_DATA[sid] = {
            "tmp_dir": tmp_dir,
            "resume_path": resume_path,
            "resume_text": resume_text,
            "jd_text": jd_text,
            "analysis": analysis,
            "chat_history": []
        }
        
        print(f">>> [Web API] Analysis success for {sid}", flush=True)
        return jsonify({
            "sid": sid,
            "analysis": analysis
        })
        
    except Exception as e:
        logger.error(f"!!! WEB ANALYZE ERROR: {e}", exc_info=True)
        print(f"!!! WEB ANALYZE ERROR: {e}", flush=True)
        shutil.rmtree(tmp_dir, ignore_errors=True)
        return jsonify({"error": str(e)}), 500

@app.route('/api/simple_generate', methods=['POST', 'OPTIONS'], strict_slashes=False)
def simple_generate():
    print(">>> [Web API] Received simple generation request", flush=True)
    if 'resume' not in request.files:
        return jsonify({"error": "No resume file provided"}), 400
    
    resume_file = request.files['resume']
    sid = str(uuid.uuid4())
    tmp_dir = tempfile.mkdtemp(prefix=f"resumesimple_{sid}_")
    
    ext = Path(resume_file.filename).suffix.lower()
    if ext not in (".pdf", ".docx", ".doc", ".txt"):
        shutil.rmtree(tmp_dir, ignore_errors=True)
        return jsonify({"error": "Unsupported file format"}), 400
        
    resume_path = os.path.join(tmp_dir, f"resume{ext}")
    resume_file.save(resume_path)
    
    try:
        resume_text = extract_resume_text(resume_path)
        if len(resume_text.strip()) < 50:
             shutil.rmtree(tmp_dir, ignore_errors=True)
             return jsonify({"error": "Could not extract text from resume"}), 400
            
        print(f">>> [Web API] Structuring with Gemini...", flush=True)
        improved_data = generate_simple_resume(resume_text)
        
        WEB_DATA[sid] = {
            "tmp_dir": tmp_dir,
            "resume_path": resume_path,
            "resume_text": resume_text,
            "jd_text": "None (Simple Mode)",
            "analysis": {
                "overall_score": 0,
                "section_scores": {},
                "strengths": [],
                "weaknesses": [],
                "suggestions": [],
                "passed": True,
                "summary": "Generated using Simple Mode (No JD Analysis)."
            },
            "improved_data": improved_data,
            "chat_history": [],
            "mode": "simple"
        }
        
        print(f">>> [Web API] Simple generation success for {sid}", flush=True)
        return jsonify({
            "sid": sid,
            "improved_data": improved_data
        })
        
    except Exception as e:
        logger.error(f"!!! WEB SIMPLE ERROR: {e}", exc_info=True)
        if sid not in WEB_DATA:
            shutil.rmtree(tmp_dir, ignore_errors=True)
        return jsonify({"error": str(e)}), 500

@app.route('/api/chat', methods=['POST'])
def chat():
    data = request.json
    sid = data.get('sid')
    question = data.get('question')
    
    if not sid or sid not in WEB_DATA:
        return jsonify({"error": "Session expired or invalid"}), 401
    
    session = WEB_DATA[sid]
    try:
        answer = answer_counter_question(
            question,
            session["resume_text"],
            session["jd_text"],
            session["analysis"],
            session.get("chat_history", [])
        )
        
        session.setdefault("chat_history", []).append({"role": "user", "content": question})
        session["chat_history"].append({"role": "model", "content": answer})
        
        # Invalidate improved_data if it exists (user might want changes)
        if "improved_data" in session:
            del session["improved_data"]
            
        return jsonify({"answer": answer})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/generate_improved', methods=['POST'])
def generate_improved():
    data = request.json
    sid = data.get('sid')
    
    if not sid or sid not in WEB_DATA:
        return jsonify({"error": "Session expired"}), 401
        
    session = WEB_DATA[sid]
    user_instruction = data.get('user_instruction', '').strip()
    
    try:
        # If user provides instructions, always re-generate to reflect changes
        if user_instruction or "improved_data" not in session:
            improved_data = generate_improved_resume(
                session["resume_text"],
                session["analysis"],
                session["jd_text"],
                session.get("chat_history", []),
                user_instruction=user_instruction
            )
            session["improved_data"] = improved_data
        
        return jsonify({"improved_data": session["improved_data"]})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/download_cv/<format_key>', methods=['GET'])
def download_cv(format_key):
    sid = request.args.get('sid')
    if not sid or sid not in WEB_DATA:
        return "Session expired", 401
        
    session = WEB_DATA[sid]
    if format_key not in PDF_FORMATS:
        return "Unknown format", 400
        
    try:
        # SELF-HEALING: If improved data is missing, generate it automatically
        if "improved_data" not in session:
            print(f">>> [Web API] Improved data missing for {sid}, auto-generating now...", flush=True)
            session["improved_data"] = generate_improved_resume(
                session["resume_text"],
                session["analysis"],
                session["jd_text"]
            )
            
        print(f">>> [Web API] Serving PDF: {format_key} for SID: {sid}", flush=True)
        label, builder_func, default_palette = PDF_FORMATS[format_key]
        improved_data = session["improved_data"]
        pdf_bytes = builder_func(improved_data, palette=default_palette)
        
        fname = f"CV_{format_key}.pdf"
        output_path = os.path.join(session["tmp_dir"], fname)
        with open(output_path, "wb") as f:
            f.write(pdf_bytes)
            
        return send_file(output_path, as_attachment=True, download_name=fname)
    except Exception as e:
        logger.error(f"DOWNLOAD PDF ERROR: {e}")
        return str(e), 500

@app.route('/api/download_cv_docx/<format_key>', methods=['GET'])
def download_cv_docx(format_key):
    sid = request.args.get('sid')
    if not sid or sid not in WEB_DATA:
        return "Session expired", 401
        
    session = WEB_DATA[sid]
    try:
        # SELF-HEALING: If improved data is missing, generate it automatically
        if "improved_data" not in session:
            print(f">>> [Web API] Improved data missing for {sid}, auto-generating now...", flush=True)
            session["improved_data"] = generate_improved_resume(
                session["resume_text"],
                session["analysis"],
                session["jd_text"]
            )
            
        print(f">>> [Web API] Serving DOCX: {format_key} for SID: {sid}", flush=True)
        # Pass the format key to the docx builder for style mapping (future proof)
        docx_bytes = build_docx_cv(session["improved_data"], style=format_key)
        fname = f"CV_{format_key}.docx"
        output_path = os.path.join(session["tmp_dir"], fname)
        with open(output_path, "wb") as f:
            f.write(docx_bytes)
            
        return send_file(output_path, as_attachment=True, download_name=fname)
    except Exception as e:
        logger.error(f"DOWNLOAD DOCX ERROR: {e}")
        return str(e), 500

@app.route('/api/download_report', methods=['GET'])
def download_report():
    sid = request.args.get('sid')
    if not sid or sid not in WEB_DATA:
        return "Session expired", 401
        
    session = WEB_DATA[sid]
    try:
        analysis = session["analysis"]
        name = session.get("improved_data", {}).get("name") or "Candidate"
        
        report_bytes = build_review_report(analysis, name)
        fname = f"Review_Report_{name.replace(' ', '_')}.pdf"
        report_path = os.path.join(session["tmp_dir"], fname)
        with open(report_path, "wb") as f:
            f.write(report_bytes)
            
        return send_file(report_path, as_attachment=True, download_name=fname)
    except Exception as e:
        return str(e), 500

# Serve React App
@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve(path):
    # CRITICAL: Prevent API routes from being caught by the static server
    if path.startswith("api/"):
        return "API Route Not Found", 404

    if path != "" and os.path.exists(app.static_folder + '/' + path):
        return send_from_directory(app.static_folder, path)
    else:
        return send_from_directory(app.static_folder, 'index.html')

def start_web_server():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

if __name__ == "__main__":
    start_web_server()
