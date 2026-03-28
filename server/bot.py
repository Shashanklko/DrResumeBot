import os
import sys
import logging
import asyncio
import tempfile
import shutil
import threading
from pathlib import Path
from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup,
    InputFile
)
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    CallbackQueryHandler, ContextTypes, filters, ConversationHandler
)

# Import utilities
from utils.resume_analyzer import (
    analyze_resume, 
    generate_improved_resume, 
    answer_counter_question,
    generate_simple_resume  # Added for Fast Format
)
from utils.pdf_extractor import extract_resume_text
from utils.report_generator import build_review_report
from utils.pdf_generator import FORMATS
from utils.docx_generator import build_docx_cv

logger = logging.getLogger("BOT")

# Global configs
BENCHMARK = int(os.getenv("BENCHMARK_SCORE", 70))
MAX_FILE_MB = int(os.getenv("MAX_FILE_SIZE_MB", 5))

# Conversation states
WAITING_RESUME, WAITING_JD, ANALYZING, SHOWING_RESULTS = range(4)

# ── Helpers ──────────────────────────────────────────────────────────────────
def _cleanup(user_data):
    """Safely cleans up temporary files for a user."""
    tmp = user_data.get("tmp_dir")
    if tmp and os.path.exists(tmp):
        try:
            shutil.rmtree(tmp, ignore_errors=True)
            logger.info(f"📁 Cleaned up temp directory: {tmp}")
        except Exception as e:
            logger.error(f"❌ Error cleaning up {tmp}: {e}")
    user_data.clear()

# ── /start ───────────────────────────────────────────────────────────────────
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    logger.info(f"🆕 [USER: {user.id} (@{user.username})] Started the bot.")
    
    # Reset existing session if any
    _cleanup(context.user_data)
    
    text = (
        f"👋 Hello, {user.first_name}!\n\n"
        "I'm *Resumegoat* 🐐 — your AI resume expert.\n\n"
        "I can handle multiple users simultaneously. Here's how:\n"
        "✅ *Analyze*: Compare your CV with a Job Description.\n"
        "✅ *Fast Format*: Just reformat your CV with AI structure.\n"
        "✅ *Live QA*: Ask questions about your resume improvements.\n\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "📎 *Send me your resume* (PDF, DOCX, or TXT) to begin!"
    )
    
    await update.message.reply_text(text, parse_mode="Markdown")
    return WAITING_RESUME

# ── /reset & /cancel ──────────────────────────────────────────────────────────
async def reset_session(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    logger.info(f"🔄 [USER: {user.id}] Session reset requested.")
    _cleanup(context.user_data)
    await update.message.reply_text("✨ All chat data and temporary files have been cleared. Send your resume to begin a fresh review!")
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    logger.info(f"🛑 [USER: {user.id}] Session stopped and cancelled.")
    _cleanup(context.user_data)
    await update.message.reply_text("🛑 Task stopped. Memory cleared. Send /start to begin a fresh session.")
    return ConversationHandler.END

# ── /contribute ─────────────────────────────────────────────────────────────
async def handle_contribute(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    logger.info(f"💖 [USER: {user.id}] Requested contribute info.")
    
    if update.callback_query:
        await update.callback_query.answer()
        message = update.callback_query.message
    else:
        message = update.message
    
    text = (
        "🤝 *Support Resumegoat*\n\n"
        "This project is maintained by contributors like @Shashanklko to provide a premium AI resume experience for free.\n\n"
        "If you found this tool helpful, consider supporting the developers:\n\n"
        "💎 *Crypto Donations:*\n"
        "• *USDT (TRC20):* `TQdsoT57Dsm5mSkXvJJVu2VsnEtjTm2w8N`\n"
        "• *USDT (BEP20):* `0x211e210c6541d6e3ed9330153ce70819a59c5c5d`\n"
        "• *ETH (ERC20):* `0x211e210c6541d6e3ed9330153ce70819a59c5c5d`\n"
        "• *BTC (BTC):* `16Jzr9AX3rX4ody2bSUCR8nuDD23dGrdja`\n\n"
        "You can also use *Binance Pay* via our integrated Web App.\n\n"
        "☕ *Buy Me a Coffee:*\n"
        "https://buymeacoffee.com/shashanklko\n\n"
        "Thank you for keeping the AI engine running! ❤️"
    )
    
    # Try sending photo if it exists locally
    try:
        qr_path = os.path.join(str(Path(__file__).parent.parent), "binance-qr.png")
        if os.path.exists(qr_path):
            await message.reply_photo(photo=open(qr_path, "rb"), caption=text, parse_mode="Markdown")
            return
    except Exception as e:
        logger.error(f"❌ Failed to attach QR Code: {e}")
        
    await message.reply_text(text, parse_mode="Markdown")

# ── Resume Upload Handler ─────────────────────────────────────────────────────
async def handle_resume_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    msg = update.message
    doc = msg.document
    
    if not doc:
        await msg.reply_text("⚠️ Please upload your resume as a *file* (not a photo).")
        return WAITING_RESUME

    if doc.file_size and doc.file_size > MAX_FILE_MB * 1024 * 1024:
        await msg.reply_text(f"⚠️ File too large. Max allowed: {MAX_FILE_MB}MB")
        return WAITING_RESUME

    fname = doc.file_name or "resume.pdf"
    ext = Path(fname).suffix.lower()
    if ext not in (".pdf", ".docx", ".doc", ".txt"):
        await msg.reply_text("⚠️ Supported formats: PDF, DOCX, TXT.")
        return WAITING_RESUME

    status_msg = await msg.reply_text("⏳ Downloading & Reading...")
    try:
        tmp_dir = tempfile.mkdtemp(prefix=f"resumegoat_{user.id}_")
        file_path = os.path.join(tmp_dir, f"resume{ext}")
        tg_file = await doc.get_file()
        await tg_file.download_to_drive(file_path)
        
        resume_text = extract_resume_text(file_path)
        if len(resume_text.strip()) < 50:
            await status_msg.edit_text("⚠️ Your resume seems empty or unreadable.")
            shutil.rmtree(tmp_dir, ignore_errors=True)
            return WAITING_RESUME

        context.user_data.update({
            "tmp_dir": tmp_dir, 
            "resume_path": file_path, 
            "resume_text": resume_text, 
            "fname": fname, 
            "chat_history": []
        })
        
        keyboard = [[InlineKeyboardButton("⚡ Skip JD (Fast Format)", callback_data="skip_jd")]]
        await status_msg.edit_text(
            "✅ Resume received!\n\n"
            "Now, either **paste the Job Description** below for a full analysis, "
            "or click the button for a quick professional reformatting.",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return WAITING_JD
    except Exception as e:
        logger.error(f"❌ Error for user {user.id}: {e}")
        await msg.reply_text("Something went wrong. Please try again.")
        return WAITING_RESUME

# ── Job Description / Fast Format ─────────────────────────────────────────────
async def handle_job_description(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    msg = update.message
    if not context.user_data.get("resume_text"): return ConversationHandler.END
    
    jd_text = msg.text or ""
    if len(jd_text) < 30:
        await msg.reply_text("⚠️ Job description is too short for a meaningful analysis.")
        return WAITING_JD

    context.user_data["jd_text"] = jd_text
    logger.info(f"🔍 [USER: {user.id}] Starting full analysis.")
    status = await msg.reply_text("🔍 Analyzing against JD...")

    try:
        analysis = analyze_resume(context.user_data["resume_text"], jd_text, BENCHMARK)
        context.user_data["analysis"] = analysis
        await status.edit_text("✅ Analysis complete!")
        await send_results(update, context)
    except Exception as e:
        logger.error(f"❌ Analysis error for {user.id}: {e}")
        await status.edit_text("❌ Analysis failed. Please try again later.")
        return ConversationHandler.END
    return SHOWING_RESULTS

# ── Results & Generator ───────────────────────────────────────────────────────
async def send_results(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    data = context.user_data
    analysis = data.get("analysis", {})
    score = analysis.get("overall_score", "N/A")
    
    if analysis:
        # Build detailed analysis text
        strengths = "\n".join([f"✅ {s}" for s in analysis.get("strengths", [])[:3]])
        weaknesses = "\n".join([f"⚠️ {w}" for w in analysis.get("weaknesses", [])[:3]])
        keywords = ", ".join(analysis.get("missing_keywords", []))[:200]
        
        suggestions_list = []
        for sug in analysis.get("suggestions", [])[:3]:
            suggestions_list.append(f"💡 *{sug.get('section')}*: {sug.get('fix')}")
        suggestions = "\n".join(suggestions_list)

        txt = (
            f"📊 *ATS Compatibility Score: {score}/100*\n"
            f"📝 *Verdict*: {analysis.get('ats_verdict', 'N/A')}\n\n"
            f"✨ *Overall Summary*:\n{analysis.get('summary', 'Analyzing...')}\n\n"
            f"💪 *Top Strengths*:\n{strengths}\n\n"
            f"🚫 *Critical Weaknesses*:\n{weaknesses}\n\n"
            f"🔍 *Missing Keywords*:\n_{keywords or 'None found' }_\n\n"
            f"🚀 *Actionable Suggestions*:\n{suggestions}\n\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "📥 *Ready to level up?* Click below to generate your 5 professional CV formats and full report!"
        )
    else:
        txt = "✅ Your resume has been parsed! Click below to generate your professional CV formats with AI-optimized structure."

    keyboard = [
        [InlineKeyboardButton("📥 Generate High-Fidelity CVs", callback_data="gen_cv")],
        [InlineKeyboardButton("✨ New/Restart", callback_data="reset_session")]
    ]
    
    if update.callback_query:
        await update.callback_query.message.reply_text(txt, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))
    else:
        await update.message.reply_text(txt, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))

async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user = update.effective_user
    data = context.user_data
    
    if not data.get("resume_text"):
        await query.message.reply_text("⚠️ Session expired. Please /start again.")
        return

    if query.data == "skip_jd":
        logger.info(f"⚡ [USER: {user.id}] Requested Fast Format.")
        await query.edit_message_text("⚙️ Structuring your resume with AI (Fast Format)...")
        try:
            improved = generate_simple_resume(data["resume_text"])
            context.user_data["improved_data"] = improved
            await send_results(update, context)
            return SHOWING_RESULTS
        except Exception as e:
            logger.error(f"❌ Fast Format error: {e}")
            await query.edit_message_text("❌ Generation failed.")

    elif query.data == "gen_cv":
        logger.info(f"⚙️ [USER: {user.id}] Starting full document generation & delivery.")
        # Instead of editing the message and destroying the analysis, we reply down below
        status_msg = await query.message.reply_text("⚙️ Generating 5 PDF formats and 1 Word format... This may take up to 20 seconds. ⏳")
        
        try:
            if not data.get("improved_data"):
                logger.info(f"✨ [USER: {user.id}] Improved data missing. Choosing optimal generator...")
                if data.get("analysis"):
                    improved = generate_improved_resume(data["resume_text"], data.get("analysis", {}), data.get("jd_text", ""))
                else:
                    improved = generate_simple_resume(data["resume_text"])
                context.user_data["improved_data"] = improved
            
            improved_data = context.user_data["improved_data"]
            uid = user.id
            tmp_dir = data.get("tmp_dir")
            
            # 1. Generate & Send Review Report (if analysis exists)
            if data.get("analysis"):
                report_bytes = build_review_report(data["analysis"], user.first_name)
                report_path = os.path.join(tmp_dir, "ATS_Analysis_Report.pdf")
                with open(report_path, "wb") as f: f.write(report_bytes)
                await context.bot.send_document(chat_id=uid, document=open(report_path, "rb"), caption="📄 ATS Analysis & Suggestions Report")

            # 2. Generate & Send PDFs (5 formats)
            for fmt_id, (name, builder, palette) in FORMATS.items():
                logger.info(f"📄 [USER: {uid}] Building PDF: {name}")
                pdf_bytes = builder(improved_data, palette)
                pdf_path = os.path.join(tmp_dir, f"{uid}_{fmt_id}.pdf")
                with open(pdf_path, "wb") as f: f.write(pdf_bytes)
                await context.bot.send_document(chat_id=uid, document=open(pdf_path, "rb"), caption=f"📑 {name}")

            # 3. Generate & Send DOCX (High-Fidelity)
            logger.info(f"📝 [USER: {uid}] Building DOCX...")
            docx_bytes = build_docx_cv(improved_data, style="classic_1page")
            docx_path = os.path.join(tmp_dir, f"{uid}_professional.docx")
            with open(docx_path, "wb") as f: f.write(docx_bytes)
            await context.bot.send_document(chat_id=uid, document=open(docx_path, "rb"), caption="📝 Word Editable CV (Classic ATS Style)")

            await status_msg.edit_text("✅ All documents delivered! Check your messages above. 🐐")
            
            # Send Final Options
            keyboard = [
                [InlineKeyboardButton("💖 Support the Project", callback_data="show_donate")],
                [InlineKeyboardButton("✨ Start New Review", callback_data="reset_session")]
            ]
            await query.message.reply_text(
                "Hope these help you land the job! 🚀\n"
                "If you found this free tool useful, please consider supporting its development! ❤️", 
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            
        except Exception as e:
            logger.error(f"❌ Document delivery failed for {user.id}: {e}")
            await status_msg.edit_text(f"❌ Delivery failed: {str(e)}")

    elif query.data == "reset_session":
        _cleanup(context.user_data)
        await query.edit_message_text("👋 Session terminated. Data wiped. Send /start to begin fresh!")

# ── Q&A Handler ───────────────────────────────────────────────────────────────
async def handle_question(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    msg = update.message
    data = context.user_data
    if not data.get("resume_text"): return ConversationHandler.END
    
    question = msg.text
    logger.info(f"❓ [USER: {user.id}] Question: {question[:30]}...")
    
    answer = answer_counter_question(
        question, 
        data["resume_text"], 
        data.get("jd_text", "N/A"), 
        data.get("analysis", {})
    )
    await msg.reply_text(f"🐐 *Resumegoat:* {answer}", parse_mode="Markdown")
    return SHOWING_RESULTS

# ── Bot Factory & Runner ──────────────────────────────────────────────────────
def init_bot():
    """Builds and returns the Application object (without starting it)."""
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token: 
        logger.error("❌ No TELEGRAM_BOT_TOKEN found in .env")
        return None
    
    application = Application.builder().token(token).build()
    
    # Initialize conversation handler
    conv = ConversationHandler(
        entry_points=[
            CommandHandler("start", start), 
            CommandHandler("clear", reset_session),
            CommandHandler("stop", cancel),
            CommandHandler("contribute", handle_contribute),
            CallbackQueryHandler(handle_contribute, pattern="^show_donate$"),
            MessageHandler(filters.Document.ALL, handle_resume_file)
        ],
        states={
            WAITING_RESUME: [
                MessageHandler(filters.Document.ALL, handle_resume_file),
                CallbackQueryHandler(handle_contribute, pattern="^show_donate$"),
                MessageHandler(filters.TEXT & ~filters.COMMAND, lambda u, c: u.message.reply_text("📎 Send your resume first."))
            ],
            WAITING_JD: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_job_description),
                CallbackQueryHandler(callback_handler, pattern="^skip_jd$"),
                CallbackQueryHandler(handle_contribute, pattern="^show_donate$")
            ],
            SHOWING_RESULTS: [
                CallbackQueryHandler(handle_contribute, pattern="^show_donate$"),
                CallbackQueryHandler(callback_handler),
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_question)
            ],
        },
        fallbacks=[
            CommandHandler("cancel", cancel), 
            CommandHandler("stop", cancel),
            CommandHandler("reset", reset_session),
            CommandHandler("clear", reset_session),
            CommandHandler("contribute", handle_contribute),
            CallbackQueryHandler(handle_contribute, pattern="^show_donate$")
        ],
        allow_reentry=True
    )
    
    application.add_handler(conv)
    return application

def run_bot():
    """Starts the bot in Polling mode (used for local development)."""
    application = init_bot()
    if not application: return
    
    logger.info(f"🤖 @resumegoatbot is now listening for updates (Polling mode)...")
    application.run_polling(drop_pending_updates=True)

async def process_webhook_update(application, update_json):
    """Processes a single update received via webhook."""
    try:
        update = Update.de_json(data=update_json, bot=application.bot)
        await application.process_update(update)
    except Exception as e:
        logger.error(f"❌ Error processing webhook update: {e}")

if __name__ == "__main__":
    run_bot()
