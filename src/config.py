import os
from dotenv import load_dotenv
import google.generativeai as genai

# Load environment variables (API keys)
load_dotenv(dotenv_path=os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '.env')) # Corrected path for .env

GOOGLE_API_KEY = os.getenv("GEMINI_API_KEY")
PERPLEXITY_API_KEY = os.getenv("PERPLEXITY_API_KEY")

# --- Configure Google AI ---
GEMINI_CLIENT_INITIALIZED = False
if not GOOGLE_API_KEY:
    print("🔴 WARNING: GEMINI_API_KEY not found. Gemini calls will fail.")
else:
    try:
        genai.configure(api_key=GOOGLE_API_KEY)
        print("✅ Google AI SDK Configured successfully.")
        GEMINI_CLIENT_INITIALIZED = True
    except Exception as e:
        print(f"🔴 ERROR configuring Google AI SDK: {e}")
        GOOGLE_API_KEY = None # Ensure it's None if config failed

# --- Configure Perplexity ---
if not PERPLEXITY_API_KEY:
    print("🟡 WARNING: PERPLEXITY_API_KEY not found. Perplexity calls will fail.")
else:
    print("✅ Perplexity API Key loaded.") 