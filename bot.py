"""
bot.py — Telegram Resume Reviewer Bot
======================================
Flow:
1. /start → welcome
2. User sends resume (PDF/DOCX/TXT) → bot saves it
3. Bot asks for job description
4. User sends JD as text
5. Bot analyzes resume vs JD → shows score
6. If score < benchmark → shows suggestions
7. Bot generates improved resume in 5 formats + review report
8. User downloads any format they want
"""

import os
import sys
import logging
import asyncio
import tempfile
import shutil
import threading
from flask import Flask
from pathlib import Path
from dotenv import load_dotenv
import google.generativeai as genai

from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup,
    InputFile
)
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    CallbackQueryHandler, ContextTypes, filters, ConversationHandler
)

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from utils.resume_analyzer import analyze_resume, generate_improved_resume
from utils.pdf_generator import generate_all_formats, FORMATS
from utils.pdf_extractor import extract_resume_text
from utils.report_generator import build_review_report

load_dotenv()

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Conversation states
WAITING_RESUME, WAITING_JD, ANALYZING, SHOWING_RESULTS = range(4)

BENCHMARK = int(os.getenv("BENCHMARK_SCORE", 70))
MAX_FILE_MB = int(os.getenv("MAX_FILE_SIZE_MB", 5))

# Temp storage per user
USER_DATA = {}


# ── /start ─────────────────────────────────────────────────────────────────────
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    text = (
        f"👋 Hello, {user.first_name}!\n\n"
        "I'm your *AI Resume Reviewer Bot* 🤖\n\n"
        "Here's what I can do:\n"
        "✅ Score your resume against any job description\n"
        "✅ Identify missing keywords & ATS issues\n"
        "✅ Generate an improved resume in *5 professional formats*\n"
        "✅ Provide a detailed downloadable review report\n\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "📎 *Send me your resume* to get started!\n"
        "_(Supports PDF, DOCX, or TXT)_"
    )
    await update.message.reply_text(text, parse_mode="Markdown")
    return WAITING_RESUME


# ── /help ──────────────────────────────────────────────────────────────────────
async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "📖 *How to use this bot:*\n\n"
        "1️⃣ Send your resume (PDF, DOCX or TXT)\n"
        "2️⃣ Paste the job description text\n"
        "3️⃣ Get instant AI scoring & review\n"
        "4️⃣ Download improved CVs in 5 formats\n\n"
        "*Commands:*\n"
        "/start — restart the bot\n"
        "/help — show this message\n"
        "/cancel — cancel current session\n\n"
        f"*Benchmark score:* {BENCHMARK}/100\n"
        "Resumes scoring below this get improvement suggestions."
    )
    await update.message.reply_text(text, parse_mode="Markdown")


# ── /cancel ────────────────────────────────────────────────────────────────────
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if uid in USER_DATA:
        _cleanup(uid)
    await update.message.reply_text(
        "❌ Session cancelled. Send /start to begin again."
    )
    return ConversationHandler.END


def _cleanup(uid):
    data = USER_DATA.pop(uid, {})
    tmp = data.get("tmp_dir")
    if tmp and os.path.exists(tmp):
        shutil.rmtree(tmp, ignore_errors=True)


# ── Resume Upload Handler ─────────────────────────────────────────────────────
async def handle_resume_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    msg = update.message

    # Accept document uploads
    doc = msg.document
    if not doc:
        await msg.reply_text(
            "⚠️ Please upload your resume as a *file* (PDF, DOCX, or TXT).",
            parse_mode="Markdown"
        )
        return WAITING_RESUME

    # File size check
    if doc.file_size and doc.file_size > MAX_FILE_MB * 1024 * 1024:
        await msg.reply_text(f"⚠️ File too large. Max size: {MAX_FILE_MB}MB")
        return WAITING_RESUME

    # Extension check
    fname = doc.file_name or "resume.pdf"
    ext = Path(fname).suffix.lower()
    if ext not in (".pdf", ".docx", ".doc", ".txt"):
        await msg.reply_text(
            "⚠️ Unsupported format. Please send a *PDF*, *DOCX*, or *TXT* file.",
            parse_mode="Markdown"
        )
        return WAITING_RESUME

    status_msg = await msg.reply_text("⏳ Downloading your resume...")

    try:
        # Create temp dir for this user
        tmp_dir = tempfile.mkdtemp(prefix=f"resumebot_{uid}_")
        file_path = os.path.join(tmp_dir, f"resume{ext}")

        tg_file = await doc.get_file()
        await tg_file.download_to_drive(file_path)

        # Extract text
        resume_text = extract_resume_text(file_path)
        if len(resume_text.strip()) < 50:
            await status_msg.edit_text(
                "⚠️ Could not extract text from your resume. "
                "Please try a text-based PDF or DOCX file."
            )
            shutil.rmtree(tmp_dir, ignore_errors=True)
            return WAITING_RESUME

        USER_DATA[uid] = {
            "tmp_dir": tmp_dir,
            "resume_path": file_path,
            "resume_text": resume_text,
            "fname": fname
        }

        word_count = len(resume_text.split())
        await status_msg.edit_text(
            f"✅ Resume received! _{word_count} words extracted._\n\n"
            "📝 Now paste the *Job Description* you're applying for.\n"
            "_(You can paste the full JD text — the longer, the better!)_",
            parse_mode="Markdown"
        )
        return WAITING_JD

    except Exception as e:
        logger.error(f"Error processing resume: {e}", exc_info=True)
        await status_msg.edit_text(
            "❌ Error processing your file. Please try again."
        )
        return WAITING_RESUME


# ── Job Description Handler ───────────────────────────────────────────────────
async def handle_job_description(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    msg = update.message

    if uid not in USER_DATA:
        await msg.reply_text("Session expired. Please send /start again.")
        return ConversationHandler.END

    jd_text = ""
    # Check if document was uploaded
    if msg.document:
        doc = msg.document
        if doc.file_size and doc.file_size > MAX_FILE_MB * 1024 * 1024:
            await msg.reply_text(f"⚠️ File too large. Max size: {MAX_FILE_MB}MB")
            return WAITING_JD
            
        fname = doc.file_name or "jd.pdf"
        ext = Path(fname).suffix.lower()
        if ext not in (".pdf", ".docx", ".doc", ".txt"):
            await msg.reply_text("⚠️ Please send JD as text or (PDF, DOCX, TXT).")
            return WAITING_JD

        status_msg = await msg.reply_text("⏳ Reading JD file...")
        try:
            tmp_dir = USER_DATA[uid]["tmp_dir"]
            file_path = os.path.join(tmp_dir, f"jd{ext}")
            tg_file = await doc.get_file()
            await tg_file.download_to_drive(file_path)
            
            jd_text = extract_resume_text(file_path)
            await status_msg.delete()
        except Exception as e:
            logger.error(f"Error reading JD: {e}")
            await status_msg.edit_text("❌ Error reading JD file. Please try pasting it as text instead.")
            return WAITING_JD
    elif msg.text:
        jd_text = msg.text.strip()

    if len(jd_text) < 30:
        await msg.reply_text(
            "⚠️ Job description is too short. Please paste the complete JD text or upload a valid file."
        )
        return WAITING_JD

    USER_DATA[uid]["jd_text"] = jd_text

    status = await msg.reply_text(
        "🔍 *Analyzing your resume...*\n\n"
        "▸ Checking skills match\n"
        "▸ Evaluating ATS keywords\n"
        "▸ Scoring experience relevance\n"
        "▸ Reviewing formatting\n\n"
        "_This takes about 15-30 seconds..._",
        parse_mode="Markdown"
    )

    try:
        data = USER_DATA[uid]
        analysis = analyze_resume(data["resume_text"], jd_text, BENCHMARK)
        USER_DATA[uid]["analysis"] = analysis

        await status.edit_text("✅ Analysis complete! Preparing results...")
        await send_analysis_results(update, context, uid)

    except Exception as e:
        logger.error(f"Analysis error: {e}", exc_info=True)
        await status.edit_text(
            "❌ Analysis failed. Please check your API key and try again.\n"
            f"Error: {str(e)[:100]}"
        )
        return ConversationHandler.END

    return SHOWING_RESULTS


async def send_analysis_results(update: Update, context: ContextTypes.DEFAULT_TYPE, uid: int):
    data = USER_DATA[uid]
    analysis = data["analysis"]
    score = analysis["overall_score"]
    benchmark = analysis["benchmark"]
    passed = analysis["passed"]
    sec = analysis.get("section_scores", {})

    # Score bar visual
    filled = int(score / 5)  # out of 20
    bar = "█" * filled + "░" * (20 - filled)
    score_emoji = "🟢" if score >= 80 else ("🟡" if score >= benchmark else "🔴")

    result_text = (
        f"{'✅' if passed else '❌'} *RESUME ANALYSIS RESULTS*\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"{score_emoji} *Overall Score: {score}/100*\n"
        f"`{bar}`\n"
        f"Benchmark: {benchmark}/100  |  {'PASSED ✅' if passed else 'NEEDS WORK ⚠️'}\n\n"
        f"*Section Scores:*\n"
        f"  🎯 Skills Match: {sec.get('skills_match', 0)}/100\n"
        f"  💼 Experience: {sec.get('experience_relevance', 0)}/100\n"
        f"  🎓 Education: {sec.get('education_fit', 0)}/100\n"
        f"  🤖 ATS Keywords: {sec.get('keywords_ats', 0)}/100\n"
        f"  📄 Formatting: {sec.get('formatting_clarity', 0)}/100\n\n"
        f"*Summary:*\n_{analysis.get('summary', '')}_\n"
    )

    # Strengths
    strengths = analysis.get("strengths", [])[:3]
    if strengths:
        result_text += "\n✅ *Strengths:*\n"
        for s in strengths:
            result_text += f"  ▸ {s}\n"

    # Weaknesses
    weaknesses = analysis.get("weaknesses", [])[:3]
    if weaknesses:
        result_text += "\n⚠️ *Weaknesses:*\n"
        for w in weaknesses:
            result_text += f"  ▸ {w}\n"

    # Missing keywords
    missing = analysis.get("missing_keywords", [])[:6]
    if missing:
        result_text += f"\n🔍 *Missing Keywords:* `{'`, `'.join(missing)}`\n"

    # Suggestions preview (if below benchmark)
    if not passed:
        result_text += f"\n\n💡 *Top Suggestions to reach {benchmark}+:*\n"
        for i, sug in enumerate(analysis.get("suggestions", [])[:3], 1):
            result_text += f"\n*{i}. [{sug.get('section', 'General')}]*\n"
            result_text += f"  ❌ {sug.get('issue', '')}\n"
            result_text += f"  ✅ {sug.get('fix', '')}\n"

    result_text += "\n━━━━━━━━━━━━━━━━━━━━"

    keyboard = [[
        InlineKeyboardButton("📥 Get Improved CVs (5 Formats)", callback_data=f"gen_cv_{uid}"),
    ], [
        InlineKeyboardButton("📋 Download Full Review Report", callback_data=f"gen_report_{uid}"),
    ]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        result_text, parse_mode="Markdown", reply_markup=reply_markup
    )


# ── Callback: Generate CVs ────────────────────────────────────────────────────
async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    uid = update.effective_user.id
    data_str = query.data

    if uid not in USER_DATA:
        await query.edit_message_text("⚠️ Session expired. Please send /start again.")
        return

    data = USER_DATA[uid]

    if data_str.startswith("gen_cv_"):
        await query.edit_message_text(
            "⚙️ *Generating your improved resume data...*\n\n"
            "▸ Rewriting with AI improvements\n"
            "▸ Adding missing keywords\n\n"
            "_This takes about 10-15 seconds..._",
            parse_mode="Markdown"
        )

        try:
            if "improved_data" not in data:
                improved_data = generate_improved_resume(
                    data["resume_text"],
                    data["analysis"],
                    data["jd_text"]
                )
                USER_DATA[uid]["improved_data"] = improved_data
            else:
                improved_data = data["improved_data"]

            keyboard = [
                [InlineKeyboardButton("📄 Classic 1-Page (ATS Friendly)", callback_data=f"dlcv_classic_1page_{uid}")],
                [InlineKeyboardButton("📄 Modern 2-Page", callback_data=f"dlcv_modern_2page_{uid}")],
                [InlineKeyboardButton("📄 Left Sidebar (Trendy)", callback_data=f"dlcv_sidebar_left_{uid}")],
                [InlineKeyboardButton("📄 Right Sidebar", callback_data=f"dlcv_sidebar_right_{uid}")],
                [InlineKeyboardButton("📄 Minimal Clean (ATS)", callback_data=f"dlcv_minimal_clean_{uid}")],
                [InlineKeyboardButton("📋 Download Full Review Report", callback_data=f"gen_report_{uid}")]
            ]

            changes = improved_data.get("changes_made", [])
            changes_text = ""
            if changes:
                changes_text = "\n\n✏️ *Changes made by AI:*\n"
                for c in changes[:3]:
                    changes_text += f"  ✅ {c}\n"

            await query.edit_message_text(
                "✅ *Improved CV Data Ready!*\n\n"
                "Choose which format you want to download below:"
                f"{changes_text}",
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )

        except Exception as e:
            logger.error(f"CV generation error: {e}", exc_info=True)
            await query.edit_message_text(
                f"❌ Error generating CV data: {str(e)[:150]}\n\nPlease try /start again."
            )

    elif data_str.startswith("dlcv_"):
        parts = data_str.split("_")
        format_key = "_".join(parts[1:-1])
        
        await query.edit_message_text("⏳ *Building your PDF document...*", parse_mode="Markdown")

        try:
            improved_data = data.get("improved_data")
            if not improved_data:
                await query.edit_message_text("⚠️ Session data lost. Please send /start again.")
                return

            if format_key not in FORMATS:
                await query.edit_message_text("❌ Unknown format.")
                return

            label, builder_func = FORMATS[format_key]
            pdf_bytes = builder_func(improved_data)
            
            output_dir = os.path.join(data["tmp_dir"], "cvs")
            os.makedirs(output_dir, exist_ok=True)
            
            fname = f"CV_{format_key}_{improved_data.get('name', 'improved').replace(' ', '_')}.pdf"
            path = os.path.join(output_dir, fname)
            with open(path, "wb") as f:
                f.write(pdf_bytes)

            chat_id = update.effective_chat.id
            with open(path, "rb") as f:
                await context.bot.send_document(
                    chat_id=chat_id,
                    document=InputFile(f, filename=fname),
                    caption=f"📄 *{label}*",
                    parse_mode="Markdown"
                )

            keyboard = [[InlineKeyboardButton("🔙 Back to Formats", callback_data=f"gen_cv_{uid}")]]
            await query.edit_message_text(
                f"✅ Sent **{label}** successfully! Want another format?",
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )

        except Exception as e:
            logger.error(f"Format generation error: {e}", exc_info=True)
            await query.edit_message_text(f"❌ Error building PDF: {str(e)[:150]}")

    elif data_str.startswith("gen_report_"):
        await query.edit_message_text("📊 *Generating your review report...*", parse_mode="Markdown")

        try:
            analysis = data["analysis"]
            improved = data.get("improved_data", {})
            name = improved.get("name") or "Candidate"

            report_bytes = build_review_report(analysis, name)
            report_path = os.path.join(data["tmp_dir"], "review_report.pdf")
            with open(report_path, "wb") as f:
                f.write(report_bytes)

            fname = f"Review_Report_{name.replace(' ', '_')}.pdf"
            chat_id = update.effective_chat.id
            with open(report_path, "rb") as f:
                await context.bot.send_document(
                    chat_id=chat_id,
                    document=InputFile(f, filename=fname),
                    caption=(
                        "📋 *Your Full Resume Review Report*\n\n"
                        "Includes:\n"
                        "• Overall & section scores\n"
                        "• Strengths & weaknesses\n"
                        "• Missing keywords\n"
                        "• Detailed improvement suggestions"
                    ),
                    parse_mode="Markdown"
                )

            keyboard = [[
                InlineKeyboardButton("📥 Get Improved CVs (5 Formats)", callback_data=f"gen_cv_{uid}"),
            ], [
                InlineKeyboardButton("🔄 Review Another Resume", callback_data=f"restart_{uid}"),
            ]]
            await query.edit_message_text(
                "✅ Report sent! Want improved CVs too?",
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )

        except Exception as e:
            logger.error(f"Report error: {e}", exc_info=True)
            await query.edit_message_text(f"❌ Error: {str(e)[:150]}")

    elif data_str.startswith("restart_"):
        _cleanup(uid)
        await query.edit_message_text(
            "🔄 Ready for a new review!\n\n"
            "📎 Send me your resume (PDF, DOCX, or TXT) to start."
        )
        return WAITING_RESUME


# ── Fallback text handler ─────────────────────────────────────────────────────
async def unexpected_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👆 Please upload your resume first (PDF, DOCX, or TXT file).\n"
        "Send /start to begin."
    )
    return WAITING_RESUME


# ── Health Check Server ────────────────────────────────────────────────────────
web_app = Flask(__name__)

@web_app.route('/')
def health_check():
    return "Bot is running!", 200

def run_health_check():
    # Render uses port 10000 by default for Web Services
    port = int(os.environ.get("PORT", 10000))
    web_app.run(host='0.0.0.0', port=port)

# ── Main ───────────────────────────────────────────────────────────────────────
def main():
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        raise ValueError("TELEGRAM_BOT_TOKEN not set in .env file!")

    gemini_key = os.getenv("GEMINI_API_KEY")
    if not gemini_key:
        raise ValueError("GEMINI_API_KEY not set in .env file!")

    os.environ["GEMINI_API_KEY"] = gemini_key
    genai.configure(api_key=gemini_key)

    app = Application.builder().token(token).build()

    conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler("start", start),
            MessageHandler(filters.Document.ALL, handle_resume_file),
        ],
        states={
            WAITING_RESUME: [
                MessageHandler(filters.Document.ALL, handle_resume_file),
                MessageHandler(filters.TEXT & ~filters.COMMAND, unexpected_text),
            ],
            WAITING_JD: [
                MessageHandler((filters.TEXT | filters.Document.ALL) & ~filters.COMMAND, handle_job_description),
            ],
            SHOWING_RESULTS: [
                CallbackQueryHandler(callback_handler),
            ],
        },
        fallbacks=[
            CommandHandler("cancel", cancel),
            CommandHandler("start", start),
        ],
        allow_reentry=True,
        per_message=False,
    )

    app.add_handler(conv_handler)
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CallbackQueryHandler(callback_handler))

    logger.info("🤖 Resume Reviewer Bot started!")
    logger.info(f"📊 Benchmark score: {BENCHMARK}/100")

    # Start health check server in a background thread for Render
    threading.Thread(target=run_health_check, daemon=True).start()

    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
