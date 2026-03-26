# 🤖 Telegram Resume Reviewer Bot

AI-powered resume analyzer and CV generator built with Gemini API + python-telegram-bot.

---

## ✨ Features

| Feature | Details |
|---------|---------|
| 📊 Smart Scoring | Scores resume 0-100 against any job description |
| 🤖 ATS Analysis | Checks for missing keywords, ATS pass/fail |
| 💡 Suggestions | Section-by-section improvement tips if score < benchmark |
| 📄 5 CV Formats | Classic 1-page, Modern 2-page, Left Sidebar, Right Sidebar, Minimal Clean |
| 📋 Review Report | Downloadable PDF report with full analysis |
| 🔄 Instant Delivery | All files sent directly in Telegram chat |

---

## ⚡ Setup (10 minutes)

### 1. Get Your Telegram Bot Token (FREE)
1. Open Telegram and search for **@BotFather**
2. Send `/newbot`
3. Choose a name (e.g., `Resume Reviewer`) and username (e.g., `myresumereviewbot`)
4. Copy the token — looks like: `7123456789:AAHdq...`

### 2. Get Google Gemini API Key (FREE)
1. Go to https://aistudio.google.com/
2. Sign up / log in
3. Go to **Get API key** → **Create API key**
4. Copy your key — looks like: `AIzaSy...`

### 3. Install Dependencies
```bash
cd resume_bot
pip install -r requirements.txt
```

### 4. Configure Environment
```bash
cp .env.example .env
# Edit .env and fill in your keys
nano .env   # or open in any text editor
```

Your `.env` should look like:
```
TELEGRAM_BOT_TOKEN=7123456789:AAHdq...your_token...
GEMINI_API_KEY=AIzaSy...your_key...
BENCHMARK_SCORE=70
MAX_FILE_SIZE_MB=5
```

### 5. Run the Bot
```bash
python bot.py
```

That's it! Your bot is live 🎉

---

## 📱 How to Use

1. Open Telegram → search for your bot → `/start`
2. Upload your resume (PDF, DOCX, or TXT)
3. Paste the job description
4. Get instant AI analysis with score
5. Tap buttons to download improved CVs or review report

---

## 📁 Project Structure

```
resume_bot/
├── bot.py                    ← Main Telegram bot
├── requirements.txt          ← Dependencies
├── .env.example              ← Config template
├── .env                      ← Your actual config (create this)
└── utils/
    ├── resume_analyzer.py    ← Claude API analysis + improvement
    ├── pdf_generator.py      ← 5 CV format generators
    ├── pdf_extractor.py      ← PDF/DOCX text extraction
    └── report_generator.py   ← Review report PDF generator
```

---

## 🎨 CV Formats Generated

| Format | Best For |
|--------|----------|
| **Classic 1-Page** | Traditional roles, conservative industries |
| **Modern 2-Page** | Experienced candidates with lots to show |
| **Left Sidebar** | Creative/tech roles, modern companies |
| **Right Sidebar** | Alternative trendy layout |
| **Minimal Clean** | Best ATS pass rate, stark/clean look |

---

## ⚙️ Configuration

Edit `.env` to customize:

- `BENCHMARK_SCORE` — Score threshold (default: 70). Below this, bot suggests improvements.
- `MAX_FILE_SIZE_MB` — Max resume upload size (default: 5MB)

---

## 💰 API Costs

- **Telegram Bot API**: Completely FREE forever
- **Google Gemini API**: FREE tier available (very generous)
  - After that: Pay-as-you-go (extremely cheap)
  - Model used: `gemini-1.5-flash` or `gemini-1.5-pro`

---

## 🚀 Deploy to Server (Optional)

To run 24/7 on a server (e.g., free Oracle Cloud, Railway, Fly.io):

```bash
# Using screen
screen -S resumebot
python bot.py
# Ctrl+A, D to detach

# Or using systemd service (Linux)
# Create /etc/systemd/system/resumebot.service with ExecStart=python /path/to/bot.py
```

---

## 🐛 Troubleshooting

| Error | Fix |
|-------|-----|
| `TELEGRAM_BOT_TOKEN not set` | Add token to `.env` file |
| `GEMINI_API_KEY not set` | Add API key to `.env` file |
| `Could not extract text` | Use a text-based PDF (not scanned) |
| `File too large` | Reduce `MAX_FILE_SIZE_MB` or compress PDF |

---

## 📬 Bot Commands

| Command | Action |
|---------|--------|
| `/start` | Start the bot / begin new review |
| `/help` | Show usage instructions |
| `/cancel` | Cancel current session |

---

Built with ❤️ using Python, python-telegram-bot, Google Gemini API, and ReportLab.
