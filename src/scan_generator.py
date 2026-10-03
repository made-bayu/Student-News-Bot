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
            
            # Prioritaskan model flash standar gratisan yang ada di akunmu
            preferred = ["gemini-flash-latest", "gemini-flash-lite-latest", "gemini-2.5-flash", "gemini-2.0-flash"]
            ordered = [m for m in preferred if m in valid_models]
            for m in valid_models:
                if m not in ordered and "preview" not in m and "omni" not in m and "tts" not in m and "image" not in m:
                    ordered.append(m)
            
            print(f"[Gemini API] Prioritized free models: {ordered[:5]}", flush=True)
            return ordered if ordered else preferred
    except Exception as e:
        print(f"[Gemini API] Discovery failed ({e}), using default fallback pool.", file=sys.stderr, flush=True)
        return ["gemini-flash-latest", "gemini-flash-lite-latest", "gemini-2.5-flash"]

def clean_model_output(raw_text: str, date_display: str) -> str:
    marker = f"📅 **{date_display} | Surabaya, WIB**"
    if marker in raw_text:
        return raw_text[raw_text.index(marker):].strip()
    
    alt_marker = f"{date_display} | Surabaya, WIB"
    if alt_marker in raw_text:
        start_idx = raw_text.index(alt_marker)
        line_start = raw_text.rfind("\n", 0, start_idx)
        return raw_text[line_start if line_start != -1 else 0:].strip()

    return raw_text.strip()

def build_prompt(date_display: str) -> str:
    lines = [
        "You are an undergraduate Informatics (Computer Science) student living in Surabaya, East Java, Indonesia.",
        "Your voice is analytical, practical, tech-savvy, and slightly informal yet sharp.",
        "",
        "### CORE COMPETENCIES & EVALUATION SKILLS:",
        "1. SYSTEM & ML EFFICIENCY SKILL: Analyze technical trade-offs (VRAM footprint, RAM offloading, quantization loss, token throughput, edge hardware constraints on budget laptops).",
        "2. IN
