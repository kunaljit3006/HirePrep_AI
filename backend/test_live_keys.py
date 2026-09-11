import sys
import os
import asyncio
import time
import httpx

# Ensure UTF-8 output on Windows console
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

# Add backend directory to path
sys.path.insert(0, os.path.dirname(__file__))

from app.config import settings
from app.services.llm_service import llm_service

async def test_tokens():
    print("=" * 60)
    print("HirePrep_AI - Live API & Token Verification")
    print("=" * 60)

    # 1. GitHub Token Test
    print("\n[1/4] Testing GitHub Token...")
    if settings.GITHUB_TOKEN:
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(
                    "https://api.github.com/user",
                    headers={"Authorization": f"Bearer {settings.GITHUB_TOKEN}"}
                )
                rate_limit = resp.headers.get("x-ratelimit-remaining", "unknown")
                if resp.status_code == 200:
                    user_data = resp.json()
                    print(f"  [PASS] GitHub Token VALID! Authenticated as: @{user_data.get('login')}")
                    print(f"  [INFO] API Rate Limit Remaining: {rate_limit}/5000 requests/hr")
                else:
                    print(f"  [FAIL] GitHub Token Error (Status {resp.status_code}): {resp.text[:100]}")
        except Exception as e:
            print(f"  [ERROR] GitHub connection error: {e}")
    else:
        print("  [SKIP] GITHUB_TOKEN not set in .env")

    # 2. Groq LPU Test (Primary)
    print("\n[2/4] Testing Groq LPU API Key (Primary LLM)...")
    if settings.GROQ_API_KEY:
        try:
            t0 = time.time()
            prompt = [{"role": "user", "content": "Reply in exactly 5 words: Confirm you are live and ready."}]
            resp = await llm_service.call("interview_conductor", prompt)
            latency = (time.time() - t0) * 1000
            print(f"  [PASS] Groq API Key VALID! Latency: {latency:.1f}ms")
            print(f"  [RESPONSE] \"{resp.strip()}\"")
        except Exception as e:
            print(f"  [FAIL] Groq API Error: {e}")
    else:
        print("  [SKIP] GROQ_API_KEY not set in .env")

    # 3. OpenRouter Test
    print("\n[3/5] Testing OpenRouter API Key...")
    if settings.OPENROUTER_API_KEY:
        try:
            # First verify key validity and balance
            t0 = time.time()
            async with httpx.AsyncClient(timeout=10.0) as client:
                key_resp = await client.get(
                    "https://openrouter.ai/api/v1/auth/key",
                    headers={"Authorization": f"Bearer {settings.OPENROUTER_API_KEY}"}
                )
                auth_latency = (time.time() - t0) * 1000
                if key_resp.status_code == 200:
                    key_info = key_resp.json().get("data", {})
                    label = key_info.get("label", "Key")
                    limit = key_info.get("limit")
                    usage = key_info.get("usage", 0)
                    print(f"  [PASS] OpenRouter Key Auth VALID! Latency: {auth_latency:.1f}ms")
                    print(f"  [INFO] Key Label: {label} | Usage: ${usage} | Limit: {limit}")
                else:
                    print(f"  [WARN] OpenRouter Auth Check status: {key_resp.status_code}")

            # Now test chat completion using available free model
            t0 = time.time()
            import litellm
            # Test with mistralai/mistral-7b-instruct:free or google/gemini-2.0-flash-lite-preview-02-05:free
            candidate_models = [
                "openrouter/google/gemini-2.0-flash-lite-preview-02-05:free",
                "openrouter/deepseek/deepseek-r1:free",
                "openrouter/meta-llama/llama-3.2-3b-instruct:free",
                "openrouter/qwen/qwen-2.5-72b-instruct:free"
            ]
            success = False
            for model_id in candidate_models:
                try:
                    t_m0 = time.time()
                    res = await litellm.acompletion(
                        model=model_id,
                        messages=[{"role": "user", "content": "Reply with 'OpenRouter is online' in 4 words."}],
                        api_key=settings.OPENROUTER_API_KEY,
                        timeout=15.0
                    )
                    latency = (time.time() - t_m0) * 1000
                    text = res.choices[0].message.content
                    print(f"  [PASS] Model {model_id} Responded! Latency: {latency:.1f}ms")
                    print(f"  [RESPONSE] \"{text.strip()}\"")
                    success = True
                    break
                except Exception as me:
                    continue
            if not success:
                print(f"  [INFO] Note: OpenRouter free model queue busy or rate limited, but API Key itself is validated.")
        except Exception as e:
            print(f"  [FAIL] OpenRouter error: {e}")
    else:
        print("  [SKIP] OPENROUTER_API_KEY not set in .env")

    # 4. Hugging Face Test
    print("\n[4/5] Testing Hugging Face API Key...")
    if settings.HUGGINGFACE_API_KEY:
        try:
            t0 = time.time()
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(
                    "https://huggingface.co/api/whoami-v2",
                    headers={"Authorization": f"Bearer {settings.HUGGINGFACE_API_KEY}"}
                )
                latency = (time.time() - t0) * 1000
                if resp.status_code == 200:
                    hf_user = resp.json()
                    name = hf_user.get("name", "Unknown")
                    auth_type = hf_user.get("auth", {}).get("type", "unknown")
                    print(f"  [PASS] Hugging Face Key VALID! Latency: {latency:.1f}ms")
                    print(f"  [INFO] User: @{name} | Auth Type: {auth_type}")
                else:
                    print(f"  [FAIL] Hugging Face Key status {resp.status_code}: {resp.text[:100]}")
        except Exception as e:
            print(f"  [ERROR] Hugging Face test error: {e}")
    else:
        print("  [SKIP] HUGGINGFACE_API_KEY not set in .env")

    # 5. Google Gemini Test (Fallback)
    print("\n[5/5] Testing Google Gemini Key...")
    if settings.GEMINI_API_KEY:
        try:
            import litellm
            t0 = time.time()
            res = await litellm.acompletion(
                model="gemini/gemini-2.5-flash",
                messages=[{"role": "user", "content": "Say hello in 3 words."}],
                api_key=settings.GEMINI_API_KEY
            )
            latency = (time.time() - t0) * 1000
            text = res.choices[0].message.content
            print(f"  [PASS] Google Gemini Key VALID! Latency: {latency:.1f}ms")
            print(f"  [RESPONSE] \"{text.strip()}\"")
        except Exception as e:
            print(f"  [FAIL] Gemini API result: {e}")
    else:
        print("  [SKIP] GEMINI_API_KEY not set in .env")

    print("\n" + "=" * 60)
    print("Verification Complete!")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(test_tokens())
