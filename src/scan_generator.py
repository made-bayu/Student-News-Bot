import os
import sys
import argparse
from datetime import datetime, timezone, timedelta, date
import re
import json
import urllib.request
import urllib.error

def get_current_date(tz_offset_hours=7):
    # Default to UTC+7 (WIB / Surabaya)
    tz = timezone(timedelta(hours=tz_offset_hours))
    now = datetime.now(tz)
    return now.strftime("%A, %d %B %Y"), now.strftime("%Y-%m-%d"), now.date()

def sync_digests_and_get_recent_topics(output_dir: str, today_date: date, retention_days: int = 7) -> list:
    """
    Prunes markdown files older than retention_days (1 week) and extracts
    headlines from recent digests to inject as an anti-repetition constraint.
    """
    if not os.path.exists(output_dir):
        return []

    recent_topics = []
    for fname in sorted(os.listdir(output_dir)):
        if not fname.endswith(".md"):
            continue

        fdate_str = fname[:-3]
        try:
            fdate = datetime.strptime(fdate_str, "%Y-%m-%d").date()
        except ValueError:
            continue

        fpath = os.path.join(output_dir, fname)
        age_days = (today_date - fdate).days

        # 1. Hapus digest yang umurnya lebih dari 1 minggu (7 hari)
        if age_days > retention_days:
            try:
                os.remove(fpath)
                print(f"[Prune] Removed old digest (> {retention_days} days): {fname}", flush=True)
            except Exception as e:
                print(f"[Prune] Error removing {fname}: {e}", file=sys.stderr, flush=True)
        
        # 2. Ambil topik dari digest 7 hari terakhir untuk memori anti-repetisi
        elif age_days >= 0:
            try:
                with open(fpath, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if line.startswith("### "):
                            m = re.search(r"###\s*\[(.*?)\]", line)
                            title = m.group(1) if m else line[4:]
                            clean_title = title.replace("**", "").strip()
                            if clean_title and clean_title not in recent_topics:
                                recent_topics.append(clean_title)
            except Exception as e:
                print(f"[History] Error reading {fname}: {e}", file=sys.stderr, flush=True)

    return recent_topics

def discover_active_models(api_key: str) -> list:
    url = f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}"
    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            valid = []
            for m in data.get("models", []):
                methods = m.get("supportedGenerationMethods", [])
                name = m.get("name", "").replace("models/", "")
                if "generateContent" in methods:
                    valid.append(name)
            
            preferred = [
                "gemini-flash-latest",
                "gemini-flash-lite-latest",
                "gemini-2.5-flash",
                "gemini-2.0-flash"
            ]
            ordered = [m for m in preferred if m in valid]
            for m in valid:
                if m not in ordered and "preview" not in m and "omni" not in m and "tts" not in m and "image" not in m:
                    ordered.append(m)
            
            print(f"[Gemini API] Models: {ordered[:4]}", flush=True)
            return ordered if ordered else preferred
    except Exception as e:
        print(f"[Gemini API] Fallback models used: {e}", file=sys.stderr, flush=True)
        return ["gemini-flash-latest", "gemini-flash-lite-latest", "gemini-2.5-flash"]

def clean_model_output(raw_text: str, date_display: str) -> str:
    marker = f"📅 **{date_display} | Surabaya, WIB**"
    if marker in raw_text:
        return raw_text[raw_text.index(marker):].strip()
    
    alt_marker = f"{date_display} | Surabaya, WIB"
    if alt_marker in raw_text:
        idx = raw_text.index(alt_marker)
        start = raw_text.rfind("\n", 0, idx)
        return raw_text[start if start != -1 else 0:].strip()

    return raw_text.strip()

def build_prompt(date_display: str, recent_topics: list) -> str:
    lines = [
        "Undergraduate Informatics (CS) student in Surabaya, Indonesia.",
        "Analytical, practical, tech-savvy, informal yet sharp voice.",
        "",
        "CORE SKILLS & EVALUATION:",
        "1. ML EFFICIENCY: VRAM/RAM limits, GGUF/AWQ, student laptops.",
        "2. CURRICULUM: Link to OS, Distributed Systems, AI Lab, or TA.",
        "3. PORTFOLIO: GitHub project ideas, algorithm practice, CV.",
        "",
        "STRICT CONTRACT:",
        "- Output ONLY final Markdown digest.",
        "- NO internal thoughts, conflict resolution, or meta notes.",
        "- Start immediately with the header.",
        "",
        f"Daily scan for: {date_display}"
    ]

    # Injeksi batas topik yang sudah pernah dibahas agar tidak berulang
    if recent_topics:
        lines.append("")
        lines.append("ANTI-REPETITION SKILL (DO NOT REPEAT RECENT NEWS):")
        lines.append("The following topics were already covered in the past 7 days. You MUST NOT repeat these topics or frameworks:")
        for t in recent_topics[:8]:
            lines.append(f"- {t}")
        lines.append("Select completely FRESH, NEW, and DIFFERENT open-source breakthroughs and opportunities!")

    lines.extend([
        "",
        "Structure:",
        f"📅 **{date_display} | Surabaya, WIB**",
        "",
        "---",
        "",
        "### [**Headline 1 with bold technical keyword**]",
        "",
        "* **Summary**: (3-4 sentences: Technical architecture, links).",
        "* **Practical Student Takeaway**: (VRAM/RAM limits, coursework).",
        "",
        "---",
        "",
        "### [**Headline 2 with bold opportunity keyword**]",
        "",
        "* **Summary**: (3-4 sentences: Real dates, criteria, portal links).",
        "* **Practical Student Takeaway**: (GitHub steps, CV, verification).",
        "",
        "Output clean raw Markdown without code fences."
    ])
    return "\n".join(lines)

def call_gemini_api(api_key: str, model_name: str, prompt: str) -> str:
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={api_key}"
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.4,
            "maxOutputTokens": 2048
        }
    }

    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = json.loads(resp.read().decode("utf-8"))
        candidates = data.get("candidates", [])
        if candidates:
            parts = candidates[0].get("content", {}).get("parts", [])
            if parts:
                return parts[0].get("text", "").strip()
    return ""

def generate_with_gemini(api_key: str, date_display: str, recent_topics: list) -> str:
    candidate_models = discover_active_models(api_key)
    prompt = build_prompt(date_display, recent_topics)

    for model_name in candidate_models:
        try:
            text = call_gemini_api(api_key, model_name, prompt)
            if text:
                sanitized = clean_model_output(text, date_display)
                print(f"[Gemini API] Generated using: {model_name}", flush=True)
                return sanitized
        except urllib.error.HTTPError as e:
            print(f"[Gemini API] {model_name} HTTP {e.code}", flush=True)
            continue
        except Exception as e:
            print(f"[Gemini API] {model_name} error: {e}", flush=True)
            continue

    return ""

def fallback_template(date_display: str, recent_topics: list) -> str:
    is_llama_recent = any("llama.cpp" in t.lower() for t in recent_topics)
    
    if not is_llama_recent:
        lines = [
            f"📅 **{date_display} | Surabaya, WIB**",
            "",
            "---",
            "",
            "### [**llama.cpp** & GGUF Runtime: Low-Latency Local Model Serving for Consumer Hardware]",
            "",
            "* **Summary**: The open-source inference ecosystem centered on [llama.cpp](https://github.com/ggml-org/llama.cpp) continues to refine lightweight execution by pairing GGUF quantization formats with hybrid CPU-GPU memory offloading. The runtime allows developers to execute models down to sub-4-bit quantization without severe degradation in task reasoning, utilizing hardware backends like CUDA, Vulkan, and native CPU vector extensions. Furthermore, its built-in llama-server binary exposes an OpenAI-compatible REST API directly out of the box, eliminating the overhead of heavyweight Python web serving stacks for local pipelines.",
            "",
            "* **Practical Student Takeaway**: If you are building RAG prototypes, coding assistants, or final project (Tugas Akhir) AI agents on a budget laptop without access to campus GPU clusters, this is essential. You can run compact models (like Phi-4-mini or Qwen) locally on 8GB to 16GB of system RAM, test prompts and tool-calling interfaces without burning through cloud API credits, and plug your local endpoint straight into existing agent frameworks with a simple base-URL swap.",
            "",
            "---",
            "",
            "### [**Komdigi Digital Talent Scholarship (DTS)**: AI Ethics & Machine Learning Upskilling Tracks]",
            "",
            "* **Summary**: The Ministry of Communication and Digital affairs (Komdigi) has published upcoming training windows via the [Digital Talent Scholarship Portal](https://digitalent.komdigi.go.id/). Among the near-term cohorts is an intensive Etika Kecerdasan Artifisial module organized with Telkom University, which closes registration on 11 October 2026 for online training starting 15–16 October 2026, as listed on the official [DTS Registration Schedule](https://digitalent.komdigi.go.id/jadwal-pendaftaran). In addition, long-term self-paced foundational tracks, including machine learning modules hosted with [DQLab on the DTS Platform](https://digitalent.komdigi.go.id/mitra/489?tahun=2026), remain open for enrollment throughout the semester.",
            "",
            "* **Practical Student Takeaway**: Take an evening to verify your NIK and student credentials on the [Digital Talent Scholarship Dashboard](https://digitalent.komdigi.go.id/) before registration closes. Government-backed certifications and capstone projects from these programs serve as solid validation points on your CV and GitHub portfolio when applying for industry internships, Magang Merdeka, or upcoming academic awards like [Beasiswa Unggulan](https://beasiswaunggulan.kemendikdasmen.go.id/) and [LPDP](https://lpdp.kemenkeu.go.id/)."
        ]
    else:
        # Fallback alternatif jika llama.cpp sudah pernah dibahas dalam seminggu terakhir
        lines = [
            f"📅 **{date_display} | Surabaya, WIB**",
            "",
            "---",
            "",
            "### [**vLLM PagedAttention**: High-Throughput Serving & Memory Defragmentation for Local Clusters]",
            "",
            "* **Summary**: The [vLLM Project](https://github.com/vllm-project/vllm) provides high-throughput serving by implementing PagedAttention, which treats the KV-cache similarly to virtual memory paging in operating systems. By reducing internal memory fragmentation to near zero, vLLM allows higher concurrent batch sizes and continuous batching on shared GPU servers. It exposes an OpenAI-compatible API out of the box, making it the industry standard for hosting open-weights models like Llama 3 and Mistral.",
            "",
            "* **Practical Student Takeaway**: Essential for teams working on final project deployments or campus research servers where multiple clients query a single GPU simultaneously. Connecting vLLM behind a FastAPI or Nginx proxy lets you simulate production-grade AI infrastructure right on lab workstations without wasting VRAM on unallocated cache slots.",
            "",
            "---",
            "",
            "### [**Puspresnas Gemastik & Beasiswa Unggulan**: Competitive Tech Portfolios & Research Grants]",
            "",
            "* **Summary**: The National Achievement Center (Puspresnas) and Kemendikdasmen maintain active submission windows for student innovation tracks, national competitive programming, and the upcoming [Beasiswa Unggulan](https://beasiswaunggulan.kemendikdasmen.go.id/) cycles. Qualifying teams gain access to national research recognition, institutional sponsorship, and prioritized master's scholarship tracks through [LPDP](https://lpdp.kemenkeu.go.id/).",
            "",
            "* **Practical Student Takeaway**: Start structuring your coursework projects into clean, reproducible GitHub repositories with Dockerfiles and clear README docs. Judges and reviewers heavily prioritize working system demos and containerized prototypes over slide decks alone."
        ]
    return "\n".join(lines)

def generate_digest_markdown(date_display: str, recent_topics: list) -> str:
    gemini_key = os.getenv("GEMINI_API_KEY")
    if gemini_key and gemini_key.strip():
        print("[Gemini API] Requesting dynamic daily scan...", flush=True)
        dynamic_content = generate_with_gemini(gemini_key.strip(), date_display, recent_topics)
        if dynamic_content:
            return dynamic_content
        else:
            print("[Gemini API] Fallback triggered.", flush=True)
    else:
        print("[Digest] Using curated template.", flush=True)
        
    return fallback_template(date_display, recent_topics)

def save_digest(markdown_content: str, output_dir: str, file_date: str) -> str:
    os.makedirs(output_dir, exist_ok=True)
    filepath = os.path.join(output_dir, f"{file_date}.md")
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(markdown_content)
    return filepath

def send_discord_notification(webhook_url: str, text: str):
    if not webhook_url:
        print("[Discord] Error: Webhook URL is empty.", file=sys.stderr, flush=True)
        return
    payload = {"content": text[:2000]}
    req = urllib.request.Request(
        webhook_url.strip(),
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json", "User-Agent": "DailyTechScanBot/1.0"}
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            print(f"[Discord] Dispatched successfully: {resp.status}", flush=True)
    except Exception as e:
        print(f"[Discord] Error sending webhook: {e}", file=sys.stderr, flush=True)

def main():
    parser = argparse.ArgumentParser(description="Generate daily tech scan digest and notify chat channels.")
    parser.add_argument("--output-dir", default="digests", help="Directory where markdown digests are saved.")
    parser.add_argument("--notify", action="store_true", help="Flag preserved for compatibility.")
    args = parser.parse_args()

    date_display, file_date, today_date = get_current_date()
    print(f"Daily Scan for {date_display} ({file_date})...", flush=True)

    # 1. Hapus digest > 7 hari dan ekstrak riwayat topik seminggu terakhir
    recent_topics = sync_digests_and_get_recent_topics(args.output_dir, today_date, retention_days=7)
    if recent_topics:
        print(f"[Deduplication] Scanned {len(recent_topics)} recent topics from the past 7 days:", flush=True)
        for t in recent_topics[:4]:
            print(f"  - {t}", flush=True)
        if len(recent_topics) > 4:
            print(f"  ... and {len(recent_topics) - 4} more.", flush=True)
    else:
        print("[Deduplication] No recent topics found. Clean slate.", flush=True)

    # 2. Buat digest dinamis dengan memori anti-repetisi
    digest_md = generate_digest_markdown(date_display, recent_topics)
    saved_path = save_digest(digest_md, args.output_dir, file_date)
    print(f"Digest written to: {saved_path}", flush=True)

    # 3. Kirim ke Discord secara otomatis
    print("Checking Discord webhook...", flush=True)
    discord_webhook = os.getenv("DISCORD_WEBHOOK_URL") or os.getenv("DISCORD_WEBHOOK")
    if discord_webhook and discord_webhook.strip():
        url_preview = discord_webhook.strip()[:35] + "..."
        print(f"[Discord] Webhook URL detected ({url_preview}). Sending payload...", flush=True)
        send_discord_notification(discord_webhook, digest_md)
    else:
        print("[Discord] Warning: DISCORD_WEBHOOK_URL environment variable is empty or not set.", flush=True)

if __name__ == "__main__":
    main()
