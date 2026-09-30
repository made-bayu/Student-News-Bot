# Daily Tech & Opportunity Scan (Surabaya Edition)

An automated daily digest engine for Informatics (Computer Science) students. Scans open-source AI frameworks, local model execution runtimes, and verified Indonesian student/higher-education opportunities (scholarships, DTS, competitions), formatting them cleanly for Telegram, Discord, and GitHub Markdown archives.

---

## Architecture Overview

```text
├── .github/workflows/
│   └── daily_scan.yml      # GitHub Actions automation (runs 00:00 UTC / 07:00 WIB daily)
├── digests/                # Historical markdown archive of all generated daily scans
├── src/
│   └── scan_generator.py   # Core CLI script to compile summaries and dispatch webhooks
├── .env.example            # Sample environment configuration
├── .gitignore              # Ignored files (virtualenvs, cache, local .env)
└── README.md               # Documentation and setup instructions
```

---

## Quickstart (Local Testing)

1. **Clone or navigate to the repository directory**:
   ```bash
   python3 --version  # Requires Python 3.9+
   ```

2. **Generate today's scan locally**:
   ```bash
   python3 src/scan_generator.py --output-dir digests
   ```
   This generates a Markdown file under `digests/YYYY-MM-DD.md`.

3. **Test with Webhook Notifications (Optional)**:
   Copy `.env.example` to `.env` and export your tokens:
   ```bash
   cp .env.example .env
   export DISCORD_WEBHOOK_URL="https://discord.com/api/webhooks/..."
   python3 src/scan_generator.py --output-dir digests --notify
   ```

---

## Deploying to Your GitHub Account

To connect this local repository to a remote repository on GitHub:

1. **Create a new empty repository** on [GitHub](https://github.com/new) (e.g., `daily-tech-scan`).
2. **Add your remote and push**:
   ```bash
   git remote add origin https://github.com/<your-username>/<your-repo-name>.git
   git branch -M main
   git push -u origin main
   ```
3. **Configure Repository Secrets (Optional)**:
   In your GitHub repository, navigate to **Settings** > **Secrets and variables** > **Actions** > **New repository secret**:
   - `DISCORD_WEBHOOK_URL`: Your Discord webhook endpoint.
   - `TELEGRAM_BOT_TOKEN`: Token from BotFather.
   - `TELEGRAM_CHAT_ID`: Destination Telegram chat or channel ID.
4. **Ensure Workflow Permissions**:
   Under **Settings** > **Actions** > **General** > **Workflow permissions**, select **Read and write permissions** so GitHub Actions can push new digest files back into your repository.

---

## Automation Schedule

The included GitHub Actions workflow is scheduled to trigger at `00:00 UTC` every day, which corresponds to `07:00 WIB` (Western Indonesia Time) in Surabaya. It will automatically compile the daily scan, commit it to `digests/`, and send rich text blocks to your configured notification channels.
