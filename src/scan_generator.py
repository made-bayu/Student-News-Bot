import os
import sys
import argparse
from datetime import datetime
import json
import urllib.request
import urllib.error

def get_current_date_str(tz_offset_hours=7):
    # Default to UTC+7 (WIB / Surabaya)
    from datetime import timezone, timedelta
    tz = timezone(timedelta(hours=tz_offset_hours))
    now = datetime.now(tz)
    return now.strftime("%A, %d %B %Y"), now.strftime("%Y-%m-%d")

def generate_digest_markdown(date_display: str) -> str:
    """
    Generates the daily scan markdown conforming to the strict persona & formatting constraints.
    """
    content = f"""📅 **{date_display} | Surabaya, WIB**

---

### [**llama.cpp** & GGUF Runtime: Low-Latency Local Model Serving for Consumer Hardware]

* **Summary**: 
The open-source inference ecosystem centered on [llama.cpp](https://github.com/ggml-org/llama.cpp) continues to refine lightweight execution by pairing GGUF quantization formats with hybrid CPU-GPU memory offloading, as highlighted in comparative benchmarks by [Developers Digest](https://www.developersdigest.tech/compare/vllm-vs-llama-cpp). The runtime allows developers to execute models down to sub-4-bit quantization without severe degradation in task reasoning, utilizing hardware backends like CUDA, Vulkan, and native CPU vector extensions. Furthermore, its built-in `llama-server` binary exposes an OpenAI-compatible REST API directly out of the box, eliminating the overhead of heavyweight Python web serving stacks for local pipelines.

* **Practical Student Takeaway**: 
If you are building RAG prototypes, coding assistants, or final project (Tugas Akhir) AI agents on a budget laptop without access to campus GPU clusters, this is essential. You can run compact models (like Phi-4-mini or Qwen) locally on 8GB to 16GB of system RAM, test prompts and tool-calling interfaces without burning through cloud API credits, and plug your local endpoint straight into existing agent frameworks with a simple base-URL swap.

---

### [**Komdigi Digital Talent Scholarship (DTS)**: AI Ethics & Machine Learning Upskilling Tracks]

* **Summary**: 
The Ministry of Communication and Digital affairs (Komdigi) has published upcoming training windows via the [Digital Talent Scholarship Portal](https://digitalent.komdigi.go.id/). Among the near-term cohorts is an intensive *Etika Kecerdasan Artifisial* module organized with Telkom University, which closes registration on **11 October 2026** for online training starting **15–16 October 2026**, as listed on the official [DTS Registration Schedule](https://digitalent.komdigi.go.id/jadwal-pendaftaran). In addition, long-term self-paced foundational tracks, including machine learning modules hosted with [DQLab on the DTS Platform](https://digitalent.komdigi.go.id/mitra/489?tahun=2026), remain open for enrollment throughout the semester.

* **Practical Student Takeaway**: 
Take an evening to verify your NIK and student credentials on the [Digital Talent Scholarship Dashboard](https://digitalent.komdigi.go.id/) before registration closes. Government-backed certifications and capstone projects from these programs serve as solid validation points on your CV and GitHub portfolio when applying for industry internships, Magang Merdeka, or upcoming academic awards like [Beasiswa Unggulan](https://beasiswaunggulan.kemendikdasmen.go.id/) and [LPDP](https://lpdp.kemenkeu.go.id/).
"""
    return content

def save_digest(markdown_content: str, output_dir: str, file_date: str) -> str:
    os.makedirs(output_dir, exist_ok=True)
    filepath = os.path.join(output_dir, f"{file_date}.md")
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(markdown_content)
    return filepath

def send_discord_notification(webhook_url: str, text: str):
    if not webhook_url:
        return
    payload = {"content": text[:2000]}
    req = urllib.request.Request(
        webhook_url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json", "User-Agent": "DailyTechScanBot/1.0"}
    )
    try:
        with urllib.request.urlopen(req) as resp:
            print(f"[Discord] Dispatched successfully: {resp.status}")
    except Exception as e:
        print(f"[Discord] Error sending webhook: {e}", file=sys.stderr)

def send_telegram_notification(bot_token: str, chat_id: str, text: str):
    if not bot_token or not chat_id:
        return
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "Markdown",
        "disable_web_page_preview": False
    }
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"}
    )
    try:
        with urllib.request.urlopen(req) as resp:
            print(f"[Telegram] Dispatched successfully: {resp.status}")
    except Exception as e:
        print(f"[Telegram] Error sending message: {e}", file=sys.stderr)

def main():
    parser = argparse.ArgumentParser(description="Generate daily tech scan digest and optionally notify chat channels.")
    parser.add_argument("--output-dir", default="digests", help="Directory where markdown digests are saved.")
    parser.add_argument("--notify", action="store_true", help="Send webhook notifications if credentials are present.")
    args = parser.parse_args()

    date_display, file_date = get_current_date_str()
    print(f"Generating scan for {date_display} ({file_date})...")

    digest_md = generate_digest_markdown(date_display)
    saved_path = save_digest(digest_md, args.output_dir, file_date)
    print(f"Digest successfully written to: {saved_path}")

    if args.notify:
        discord_webhook = os.getenv("DISCORD_WEBHOOK_URL")
        telegram_token = os.getenv("TELEGRAM_BOT_TOKEN")
        telegram_chat_id = os.getenv("TELEGRAM_CHAT_ID")

        if discord_webhook:
            send_discord_notification(discord_webhook, digest_md)
        if telegram_token and telegram_chat_id:
            send_telegram_notification(telegram_token, telegram_chat_id, digest_md)

if __name__ == "__main__":
    main()
