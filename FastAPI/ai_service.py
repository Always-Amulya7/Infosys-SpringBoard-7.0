import os


GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")


def _call_gemini(prompt: str) -> str:
    if not GEMINI_API_KEY:
        raise RuntimeError("GEMINI_API_KEY not configured")
    try:
        import google.generativeai as genai
    except ImportError:
        raise RuntimeError("google-generativeai package not installed")
    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel("gemini-2.0-flash")
    response = model.generate_content(prompt)
    return (response.text or "").strip()


def _call_openrouter(prompt: str) -> str:
    if not OPENROUTER_API_KEY:
        raise RuntimeError("OPENROUTER_API_KEY not configured")
    try:
        import openai
    except ImportError:
        raise RuntimeError("openai package not installed")
    client = openai.OpenAI(
        api_key=OPENROUTER_API_KEY,
        base_url="https://openrouter.ai/api/v1",
    )
    completion = client.chat.completions.create(
        model="google/gemini-2.0-flash-exp:free",
        messages=[
            {"role": "system", "content": "You are a helpful productivity analyst."},
            {"role": "user", "content": prompt},
        ],
    )
    text = completion.choices[0].message.content if completion.choices else ""
    return (text or "").strip()


def get_ai_summary(prompt: str) -> str:
    try:
        return _call_gemini(prompt)
    except Exception:
        try:
            return _call_openrouter(prompt)
        except Exception as exc:
            raise RuntimeError(f"Both Gemini and OpenRouter failed: {exc}")
