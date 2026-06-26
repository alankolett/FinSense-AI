import os
import google.generativeai as genai
from dotenv import load_dotenv

# Ensure environment variables are loaded
load_dotenv()

# Configure the Gemini client
api_key = os.getenv("GEMINI_API_KEY")
if api_key:
    genai.configure(api_key=api_key)

def call_llm(prompt: str, system: str = "") -> str:
    """
    Calls the Gemini API with the given prompt and system instructions.
    
    To swap to another provider (e.g., Claude or Kimi) later, you only need to change
    this file. For example:
    
    # --- SWAPPING TO CLAUDE (Anthropic) ---
    # import anthropic
    # client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
    # message = client.messages.create(
    #     model="claude-3-5-sonnet-20241022",
    #     max_tokens=1000,
    #     temperature=0,
    #     system=system,
    #     messages=[{"role": "user", "content": prompt}]
    # )
    # return message.content[0].text
    
    # --- SWAPPING TO KIMI (Moonshot) / OpenAI ---
    # from openai import OpenAI
    # client = OpenAI(
    #     api_key=os.getenv("MOONSHOT_API_KEY"),
    #     base_url="https://api.moonshot.cn/v1",
    # )
    # completion = client.chat.completions.create(
    #     model="moonshot-v1-8k",
    #     messages=[
    #         {"role": "system", "content": system},
    #         {"role": "user", "content": prompt}
    #     ]
    # )
    # return completion.choices[0].message.content
    """
    if not api_key:
        raise ValueError("GEMINI_API_KEY environment variable is not set. Please set it in backend/.env.")
        
    model = genai.GenerativeModel(
        model_name="gemini-1.5-flash",
        system_instruction=system if system else None
    )
    
    response = model.generate_content(prompt)
    return response.text
