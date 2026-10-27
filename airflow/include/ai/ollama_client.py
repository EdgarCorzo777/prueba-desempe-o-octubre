"""
ollama_client.py
Interface to Local LLM (Ollama) with timeouts, healthcheck, prompt sanitization,
and automatic docker vs host URL resolution.
"""

import requests
import time
import logging
import socket
from typing import Dict, Any, Optional
from airflow.include.config import settings

logger = logging.getLogger("sismowatch.ollama")

_WORKING_OLLAMA_URL = None

def resolve_ollama_base_url(url: Optional[str] = None) -> str:
    """
    Dynamically discovers and caches reachable Ollama base URL.
    Checks candidate endpoints across host and docker bridge environments.
    """
    global _WORKING_OLLAMA_URL
    if _WORKING_OLLAMA_URL:
        return _WORKING_OLLAMA_URL

    configured = url or settings.OLLAMA_BASE_URL
    candidates = [
        "http://host.docker.internal:11438",
        "http://localhost:11438",
        configured,
        "http://host.docker.internal:11436",
        "http://host.docker.internal:11434",
        "http://localhost:11436",
        "http://localhost:11434",
        "http://172.17.0.1:11436",
        "http://172.17.0.1:11434",
        "http://127.0.0.1:11436",
        "http://127.0.0.1:11434",
    ]

    seen = set()
    for c in candidates:
        if not c or c in seen:
            continue
        seen.add(c)
        try:
            res = requests.get(f"{c.rstrip('/')}/api/tags", timeout=1.0)
            if res.status_code == 200:
                logger.info(f"Ollama discovered and active at: {c}")
                _WORKING_OLLAMA_URL = c
                return c
        except Exception:
            continue

    return configured

def sanitize_user_input(text: str) -> str:
    """
    Sanitizes external text strings to mitigate prompt injection.
    Strips system prompt delimiter patterns and caps length.
    """
    if not text:
        return ""
    clean = text.replace("system:", "").replace("assistant:", "").replace("user:", "")
    clean = clean.replace("```", "").replace("<|im_start|>", "").replace("<|im_end|>", "")
    return clean[:200].strip()

def check_ollama_health() -> bool:
    """
    Verifies if Ollama server is running and reachable.
    """
    try:
        base_url = resolve_ollama_base_url(settings.OLLAMA_BASE_URL)
        url = f"{base_url.rstrip('/')}/api/tags"
        res = requests.get(url, timeout=3)
        return res.status_code == 200
    except Exception as e:
        logger.warning(f"Ollama health check failed: {e}")
        return False

def generate_chat_completion(
    prompt: str,
    system_prompt: str = "Eres SismoWatch AI, analista geofísico de datos sísmicos de Gold.",
    model: Optional[str] = None,
    timeout: Optional[int] = None,
    options: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Sends a generation request to Google Gemini (primary), or falls back to local LLM / OpenCode.
    """
    import os
    target_model = model or settings.OLLAMA_MODEL
    req_timeout = timeout or settings.OLLAMA_TIMEOUT_SECONDS
    start_time = time.time()

    # 0. Primary Route: Google Gemini AI Studio
    gemini_key = os.getenv("GEMINI_API_KEY") or getattr(settings, "GEMINI_API_KEY", None) or os.getenv("GOOGLE_API_KEY")
    if gemini_key:
        candidate_models = ["gemini-3.5-flash-lite", "gemini-3.1-flash-lite", "gemini-3-flash-preview"]
        preferred_model = os.getenv("GEMINI_MODEL") or getattr(settings, "GEMINI_MODEL", None)
        if preferred_model and preferred_model not in candidate_models:
            candidate_models.insert(0, preferred_model)

        for g_model in candidate_models:
            gemini_url = f"https://generativelanguage.googleapis.com/v1beta/models/{g_model}:generateContent?key={gemini_key}"
            gemini_payload = {
                "systemInstruction": {"parts": [{"text": system_prompt}]},
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {"temperature": 0.2, "maxOutputTokens": 1024}
            }
            try:
                # Tope de 25s para el proveedor cloud: si no responde rápido,
                # el enrutador desciende al siguiente proveedor o al fallback determinista.
                gemini_timeout = req_timeout if req_timeout and req_timeout <= 25 else 25
                g_res = requests.post(gemini_url, json=gemini_payload, timeout=gemini_timeout)
                if g_res.status_code == 200:
                    g_data = g_res.json()
                    candidates = g_data.get("candidates", [])
                    if candidates and "content" in candidates[0]:
                        parts = candidates[0]["content"].get("parts", [])
                        text = "".join(p.get("text", "") for p in parts).strip()
                        latency_ms = (time.time() - start_time) * 1000.0
                        tokens = g_data.get("usageMetadata", {}).get("totalTokenCount", 0)
                        return {
                            "content": text,
                            "model": f"gemini:{g_model}",
                            "latency_ms": latency_ms,
                            "tokens": tokens,
                            "status": "SUCCESS",
                            "error": None
                        }
                else:
                    logger.warning(f"Gemini model {g_model} returned {g_res.status_code}: {g_res.text[:100]}")
            except Exception as e:
                logger.warning(f"Gemini call with {g_model} failed: {e}")

    # 1. Optional OpenCode / OpenAI-compatible endpoint route
    opencode_url = os.getenv("OPENCODE_API_URL") or os.getenv("OPENAI_BASE_URL")
    openai_key = os.getenv("OPENAI_API_KEY") or os.getenv("OPENCODE_API_KEY")

    if opencode_url or openai_key:
        endpoint = opencode_url.rstrip("/") if opencode_url else "https://api.openai.com/v1"
        if not endpoint.endswith("/chat/completions"):
            endpoint = f"{endpoint}/chat/completions"
        headers = {"Content-Type": "application/json"}
        if openai_key:
            headers["Authorization"] = f"Bearer {openai_key}"
        
        chat_model = os.getenv("OPENCODE_MODEL") or os.getenv("OPENAI_MODEL") or "opencode"
        payload = {
            "model": chat_model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.2
        }
        try:
            res = requests.post(endpoint, json=payload, headers=headers, timeout=req_timeout)
            latency_ms = (time.time() - start_time) * 1000.0
            if res.status_code == 200:
                data = res.json()
                content = data["choices"][0]["message"]["content"].strip()
                tokens = data.get("usage", {}).get("total_tokens", 0)
                return {
                    "content": content,
                    "model": f"opencode:{chat_model}",
                    "latency_ms": latency_ms,
                    "tokens": tokens,
                    "status": "SUCCESS",
                    "error": None
                }
        except Exception as e:
            logger.warning(f"OpenCode endpoint call failed: {e}. Falling back to Ollama.")

    # 2. Local Ollama route
    base_url = resolve_ollama_base_url(settings.OLLAMA_BASE_URL)
    url = f"{base_url.rstrip('/')}/api/generate"
    
    start_time = time.time()
    generation_opts = {
        "temperature": 0.2, # low temperature to prevent creative hallucinations
        "top_p": 0.9,
        "num_predict": 300
    }
    if options:
        generation_opts.update(options)

    payload = {
        "model": target_model,
        "prompt": prompt,
        "system": system_prompt,
        "stream": False,
        "options": generation_opts
    }
    
    try:
        res = requests.post(url, json=payload, timeout=req_timeout)
        latency_ms = (time.time() - start_time) * 1000.0
        
        if res.status_code == 200:
            data = res.json()
            content = data.get("response", "").strip()
            eval_count = data.get("eval_count", 0)
            returned_model = data.get("model") or target_model
            return {
                "content": content,
                "model": returned_model,
                "latency_ms": latency_ms,
                "tokens": eval_count,
                "status": "SUCCESS",
                "error": None
            }
        else:
            return {
                "content": "",
                "model": target_model,
                "latency_ms": (time.time() - start_time) * 1000.0,
                "tokens": 0,
                "status": "ERROR",
                "error": f"Ollama HTTP {res.status_code}: {res.text[:200]}"
            }
    except Exception as e:
        latency_ms = (time.time() - start_time) * 1000.0
        logger.warning(f"Ollama generation failed or timed out: {e}")
        return {
            "content": "",
            "model": target_model,
            "latency_ms": latency_ms,
            "tokens": 0,
            "status": "ERROR",
            "error": str(e)
        }
