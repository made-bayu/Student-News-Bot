import os
import sys
import argparse
from datetime import datetime, timezone, timedelta
import json
import urllib.request
import urllib.error

def get_current_date_str(tz_offset_hours=7):
    # Default to UTC+7 (WIB / Surabaya)
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

def clean_model_output(raw_text: str, date_display: str) -> str:
    """
    Strips out any Chain-of-Thought or reasoning scratchpad leaked by the LLM
    and ensures output starts directly with the standard header.
    """
    marker = f"📅 **{date_display} | Surabaya, WIB**"
    if marker in raw_text:
        return raw_text[raw_text.index(marker):].strip()
    
    alt_marker = f"{date_display} | Surabaya, WIB"
    if alt_marker in raw_text:
        start_idx = raw_text.index(alt_marker)
        line_start = raw_text.rfind("\n", 0, start_idx)
        return raw_text[line_start if line_start != -1 else 0:].strip()

    return raw_text.strip()

def generate_with_gemini(api_key: str, date_display: str) -> str:
    candidate_models = discover_active_models(api_key)
    if not candidate_models:
        return ""

    prompt = f"""You are an undergraduate Informatics (Computer Science) student living in Surabaya, East Java, Indonesia.
Your voice is analytical, practical, tech-savvy, and slightly informal yet sharp.

CRITICAL INSTRUCTIONS:
- You must output ONLY the final Markdown formatted digest.
- NEVER output internal reasoning, chain of thought, "Conflict Resolution", "Strategy", or meta-commentary.
- Start your response immediately with the header line below.

Search the web for the latest real-world developments in open-source AI and active Indonesian higher education/student opportunities. Present them formatted for: {date_display}.

Structure:
📅 **{date_display} | Surabaya, WIB**

---

### [**Headline 1 with bold technical keyword**]

* **Summary**: (3-4 sentences max: Real breakthrough, core mechanism, cite official GitHub/paper links using [Title](URL)).
* **Practical Student Takeaway**: (Concrete technical skills: system programming, memory optimization, Docker, or Tugas Akhir implementation).

---

### [**Headline 2 with bold opportunity keyword**]

* **Summary**: (3-4 sentences max: Real upcoming dates, criteria, official portal links for scholarships like IISMA/LPDP/DTS or hackathons like Gemastik).
* **Practical Student Takeaway**: (Actionable prep steps: GitHub portfolio enhancement, algorithm problem solving, or administrative verification).

Output only clean, raw Markdown without code fences or internal thought scratchpads.
"""

    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "tools": [{"googleSearch": {}}],
        "generationConfig": {
            "temperature": 0.2,
            "maxOutputTokens": 2048
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
                        sanitized = clean_model_output(content_text, date_display)
                        print(f"[Gemini API] Successfully generated grounded scan using: {model_name}", flush=True)
                        return sanitized
        except urllib.error.HTTPError as e:
            if e.code == 400:
                fallback_payload = {
                    "contents": [{"parts": [{"text": prompt}]}],
                    "generationConfig": {"temperature": 0.2, "maxOutputTokens": 1800}
                }
                req_fb = urllib.request.Request(
                    url,
                    data=json.dumps(fallback_payload).encode("utf-8"),
                    headers={"Content-Type": "application/json"}
                )
                try:
                    with urllib.request.urlopen(req_fb, timeout=30) as resp2:
                        d2 = json.loads(resp2.read().decode("utf-8"))
                        cand2 = d
