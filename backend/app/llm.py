import os
import json
import re
import google.generativeai as genai
from dotenv import load_dotenv

# Ensure environment variables are loaded
load_dotenv()

# Configure the Gemini client
api_key = os.getenv("GEMINI_API_KEY")
if api_key and api_key != "your_gemini_api_key_here":
    try:
        genai.configure(api_key=api_key)
    except Exception as e:
        print(f"[LLM CONFIG WARNING] Failed to configure Gemini client: {e}")

def call_llm(prompt: str, system: str = "") -> str:
    """
    Calls the Gemini API with the given prompt and system instructions.
    If the API key is missing, placeholder, or the call fails, it automatically
    falls back to a rule-based mock response generator to allow offline sandbox testing.
    """
    # Check if we should use the real Gemini API
    if api_key and api_key != "your_gemini_api_key_here":
        try:
            model = genai.GenerativeModel(
                model_name="gemini-1.5-flash",
                system_instruction=system if system else None
            )
            response = model.generate_content(prompt)
            return response.text
        except Exception as e:
            print(f"[LLM API EXCEPTION] Falling back to Mock LLM. Error: {e}")

    # --- MOCK LLM FALLBACK GENERATOR ---
    prompt_lc = prompt.lower()
    system_lc = system.lower() if system else ""

    # 1. Classification Prompt routing
    if "classify it into one of three categories" in prompt_lc:
        if any(w in prompt_lc for w in ["loan", "card", "elite", "prime", "simplysave", "savings plus", "interest", "recommend", "eligible"]):
            return "adopt"
        elif any(w in prompt_lc for w in ["balance", "how much money", "pay", "transfer", "send", "flag", "suspect", "crypto"]):
            return "engage"
        return "acquire"

    # 2. Affirmation check
    elif "determine if the user's message is a 'yes' or affirmation" in prompt_lc:
        if any(w in prompt_lc for w in ["yes", "agree", "okay", "approve", "sure", "yep", "do it"]):
            return "YES"
        return "NO"

    # 3. Savings Goal JSON Extraction
    elif "expressing a specific savings goal" in prompt_lc:
        if any(w in prompt_lc for w in ["save", "buy", "car", "house", "education", "retirement"]):
            return json.dumps({
                "goal_description": "Wealth Accumulation",
                "target_amount": 500000,
                "target_years": 5
            })
        return "null"

    # 4. Onboarding Detail JSON Extraction
    elif "extract any new onboarding details" in prompt_lc:
        name = None
        dob = None
        aadhaar = None
        pan = None
        vkyc_slot = None

        # Look for names in the prompt
        if "priya" in prompt_lc:
            name = "Priya Patel"
        elif "rajesh" in prompt_lc:
            name = "Rajesh Kumar"
        elif "aarav" in prompt_lc:
            name = "Aarav Sharma"

        # Aadhaar: 12 digits
        aadhaar_match = re.search(r"\b\d{12}\b", prompt)
        if aadhaar_match:
            aadhaar = aadhaar_match.group(0)

        # PAN: 5 letters, 4 digits, 1 letter
        pan_match = re.search(r"\b[A-Za-z]{5}[0-9]{4}[A-Za-z]\b", prompt)
        if pan_match:
            pan = pan_match.group(0).upper()

        # Slot times
        if "tomorrow" in prompt_lc or "schedule" in prompt_lc or "at" in prompt_lc:
            vkyc_slot = "Tomorrow at 10 AM"

        return json.dumps({
            "name": name,
            "dob": dob or ("12/08/1990" if name else None),
            "aadhaar_number": aadhaar,
            "pan_number": pan,
            "vkyc_slot": vkyc_slot
        })

    # 5. Onboarding Agent Conversational Response
    elif "finsense onboarding agent" in system_lc:
        # Check what fields are missing in the prompt context
        has_name = "name: not provided" not in prompt_lc
        has_aadhaar = "aadhaar number: not provided" not in prompt_lc
        has_pan = "pan number: not provided" not in prompt_lc
        has_vkyc = "vkyc preferred slot: not provided" not in prompt_lc

        if not has_name:
            return "Welcome to State Bank of India! I can help you open a savings account today. Could you please start by providing your full name?"
        elif not has_aadhaar:
            return "Thank you! Could you please provide your 12-digit Aadhaar Card number for verification?"
        elif not has_pan:
            return "Got it. Next, please provide your 10-digit PAN Card number."
        elif not has_vkyc:
            return "Your CKYC documents are verified. To complete your account activation, please schedule a Video KYC slot. When are you free?"
        else:
            return "Your details are complete and KYC is verified. Your new SBI savings account is ready to be opened!"

    # 6. Product Advisor Conversational Response
    elif "finsense adopt agent" in system_lc or "credit and savings advisor" in prompt_lc:
        if "elite" in prompt_lc:
            return "The SBI Card ELITE is our premium lifestyle card with an annual fee of Rs. 4,999. It offers complimentary airport lounge access and 5x Reward Points on dining and groceries."
        elif "simplysave" in prompt_lc:
            return "The SimplySAVE SBI Card is a value-conscious card with an annual fee of Rs. 499. It offers 10 Reward Points per Rs. 150 spent on dining, movies, and department stores."
        return "I can help you explore premium card offerings, evaluate your credit eligibility, or set up Systematic Investment Plans (SIP) for your financial goals. What are you looking to do?"

    # Default fallback
    return "Hello! I am your FinSense assistant. I can help you guide through account openings, manage balances, and check credit recommendations. What can I do for you?"
