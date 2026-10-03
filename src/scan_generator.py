import os
import sys
import argparse
from datetime import datetime, timezone, timedelta
import json
import urllib.request
import urllib.error

def get_current_date_str(tz_offset_hours=7):
    tz = timezone(timedelta(hours=tz_offset_hours))
    now = datetime.now(tz)
    return now.strftime("%A, %d %B %Y"), now.strftime("%Y-%m-%d")

def discover_active_models(api_key: str) -> list:
    url = f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}"
    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            valid_models = []
            for m in data.get("models", []):
                methods = m.get("supportedGenerationMethods", [])
                name = m.get("name", "").replace("models/", "")
                if "generateContent" in methods:
                    valid_models.append(name)
            
            stable_flash = [
                m for m in valid_models 
                if "flash" in m and "preview" not in m and "omni" not in m
            ]
            other_models = [
                m for m in valid_models 
                if m not in stable_flash and "omni" not in m
            ]
            
            ordered = stable_flash + other_models
            return ordered if ordered else valid_models
    except Exception as e:
        print(f"[Gemini API] Discovery failed ({e}), using fallback.", file=sys.stderr, flush=True)
        return ["gemini-2.5-flash", "gemini-2.0-flash", "gemini-1.5-flash-latest"]

def generate_with_gemini(api_key: str, date_display: str) -> str:
    candidate_models = discover_active_models(api_key)
    if not candidate_models:
        return ""

    prompt = f"""You are an undergraduate Informatics (Computer Science) student living in Surabaya, East Java, Indonesia.
Your voice is analytical, practical, tech-savvy, and slightly informal yet sharp.

Perform a daily scan for today: {date_display}.
Search and retrieve real, factual, up-to-date events. Do not invent or hallucinate news, models, or deadlines.

Generate exactly two (2) distinct, high-impact news summaries:

1. Item 1 (AI & Tech Development):
   - Focus on open-source LLMs, local AI agents, model efficiency, practical software engineering tools (e.g., llama.cpp, vLLM, GGUF/AWQ quantization, local RAG pipelines, CUDA/ROCm optimization).
   - Practical Student Takeaway: Detail specific Informatics/CS skills to acquire or apply (e.g. system programming, memory management on limited hardware, Docker containerization, REST API integration, final project / Tugas Akhir implementation).

2. Item 2 (Scholarship / Student Opportunities / Tech Policy):
   - Focus on verified scholarship openings (e.g., IISMA, Beasiswa Unggulan, LPDP, Kominfo DTS, exchange programs), national/university hackathons (e.g., Gemastik), or Indonesian tech ecosystem updates.
   - Practical Student Takeaway: Detail actionable preparation skills (e.g., GitHub portfolio projects, algorithm problem solving, English certification, administrative verification).

Format strictly as:
📅 **{date_display} | Surabaya, WIB**

---

### [**Headline 1 with bold technical keyword**]

* **Summary**: (3-4 sentences max: What happened and core technical mechanism. Cite real project/paper links using markdown [Title](URL)).
* **Practical Student Takeaway**: (Concrete technical skills, coursework relevance, and hardware workaround for local laptops).

---

### [**Headline 2 with bold opportunity keyword**]

* **Summary**: (3-4 sentences max: Real dates, eligibility criteria, and official registration portal links).
* **Practical Student Takeaway**: (Actionable preparation steps, portfolio enhancement, and CV skills).

Output only clean, raw Markdown without code block fences.
"""

    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "tools": [{"googleSearch": {}}],
        "generationConfig": {
            "temperature": 0.3,
            "maxOutputTokens": 1200
        }
    }

    for model_name in candidate_models:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={api_key}"
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"}
        )

        try:
            with urllib.request.urlopen(req, timeout=35) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                candidates = data.get("candidates", [])
                if candidates:
                    content_text = candidates[0].get("content", {}).get("parts", [])[0].get("text", "")
                    if content_text and content_text.strip():
                        print(f"[Gemini API] Successfully generated grounded scan using: {model_name}", flush=True)
                        return content_text.strip()
        except urllib.error.HTTPError as e:
            if e.code == 400:
                # Fallback if specific model tier disallows tool schema
                fallback_payload = {
                    "contents": [{"parts": [{"text": prompt}]}],
                    "generationConfig": {"temperature": 0.3, "maxOutputTokens": 1000}
                }
                req_fb = urllib.request.Request(
                    url,
                    data=json.dumps(fallback_payload).encode("utf-8"),
                    headers={"Content-Type": "application/json"}
                )
                try:
                    with urllib.request.urlopen(req_fb, timeout=30) as resp2:
                        d2 = json.loads(resp2.read().decode("utf-8"))
                        cand2 = d2.get("candidates", [])
                        if cand2:
                            c_text = cand2[0].get("content", {}).get("parts", [])[0].get("text", "")
                            if c_text and c_text.strip():
                                return c_text.strip()
                except Exception:
                    pass
            print(f"[Gemini API] Model '{model_name}' skipped: HTTP {e.code}", flush=True)
            continue
        except Exception as e:
            print(f"[Gemini API] Model '{model_name}' error: {e}", flush=True)
            continue

    return ""

def fallback_template(date_display: str) -> str:
    return f"""📅 **{date_display} | Surabaya, WIB**

---

### [**llama.cpp** & GGUF Runtime: Low-Latency Local Model Serving for Consumer Hardware]

* **Summary**: 
The open-source inference ecosystem centered on [llama.cpp](https://github.com/ggml-org/llama.cpp) continues to refine lightweight execution by pairing GGUF quantization formats with hybrid CPU-GPU memory offloading. The runtime allows developers to execute models down to sub-4-bit quantization without severe degradation in task reasoning, utilizing hardware backends like CUDA, Vulkan, and native CPU vector extensions. Furthermore, its built-in `llama-server` binary exposes an OpenAI-compatible REST API directly out of the box, eliminating the overhead of heavyweight Python web serving stacks for local pipelines.

* **Practical Student Takeaway**: 
If you are building RAG prototypes, coding assistants, or final project (Tugas Akhir) AI agents on a budget laptop without access to campus GPU clusters, this is essential. You can run compact models (like Phi-4-mini or Qwen) locally on 8GB to 16GB of system RAM, test prompts and tool-calling interfaces without burning through cloud API credits, and plug your local endpoint straight into existing agent frameworks with a simple base-URL swap.

---

### [**Komdigi Digital Talent Scholarship (DTS)**: AI Ethics & Machine Learning Upskilling Tracks]

* **Summary**: 
The Ministry of Communication and Digital affairs (Komdigi) has published upcoming training windows via the [Digital Talent Scholarship Portal](https://digitalent.komdigi.go.id/). Among the near-term cohorts is an intensive *Etika Kecerdasan Artifisial* module organized with Telkom University, which closes registration on **11 October 2026** for online training starting **15–16 October 2026**, as listed on the official [DTS Registration Schedule](https://digitalent.komdigi.go.id/jadwal-pendaftaran). In addition, long-term self-paced foundational tracks, including machine learning modules hosted with [DQLab on the DTS Platform](https://digitalent.komdigi.go.id/mitra/489?tahun=2026), remain open for enrollment throughout the semester.

* **Practical Student Takeaway**: 
Take an evening to verify your NIK and student credentials on the [Digital Talent Scholarship Dashboard](https://digitalent.komdigi.go.id/) before registration closes. Government-backed certifications and capstone projects from these programs serve as solid validation points on your CV dan GitHub portfolio when applying for industry internships, Magang Merdeka, or upcoming academic awards like [Beasiswa Unggulan](https://beasiswaunggulan.kemendikdasmen.go.id/) and [LPDP](https://lpdp.kemenkeu.go.id/).
"""

def generate_digest_markdown(date_display: str) -> str:
    gemini_key = os.getenv("GEMINI_API_KEY")
    if gemini_key and gemini_key.strip():
        print("[Gemini API] API key detected. Initiating grounded daily scan...", flush=True)
        dynamic_content = generate_with_gemini(gemini_key.strip(), date_display)
        if dynamic_content:
            return dynamic_content
        else:
            print("[Gemini API] Warning: Dynamic generation returned empty. Using fallback template.", flush=True)
    else:
        print("[Digest] Notice: GEMINI_API_KEY not found in environment. Using curated template.", flush=True)
        
    return fallback_template(date_display)

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
    parser = argparse.ArgumentParser(description="Generate daily tech scan digest and optionally notify chat channels.")
    parser.add_argument("--output-dir", default="digests", help="Directory where markdown digests are saved.")
    parser.add_argument("--notify", action="store_true", help="Send webhook notifications if credentials are present.")
    args = parser.parse_args()

    date_display, file_date = get_current_date_str()
    print(f"Generating scan for {date_display} ({file_date})...", flush=True)

    digest_md = generate_digest_markdown(date_display)
    saved_path = save_digest(digest_md, args.output_dir, file_date)
    print(f"Digest successfully written to: {saved_path}", flush=True)

    if args.notify:
        print("Checking notification channels...", flush=True)
        discord_webhook = os.getenv("DISCORD_WEBHOOK_URL") or os.getenv("DISCORD_WEBHOOK")
        if discord_webhook and discord_webhook.strip():
            print("[Discord] Webhook detected. Sending payload...", flush=True)
            send_discord_notification(discord_webhook, digest_md)
        else:
            print("[Discord] Status: No Discord webhook configured. (DISCORD_WEBHOOK_URL is empty).", flush=True)

if __name__ == "__main__":
    main()
