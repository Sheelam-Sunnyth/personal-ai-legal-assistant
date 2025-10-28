import google.generativeai as genai

# Replace this with your actual API key
import os
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

genai.configure(api_key=API_KEY)
model = genai.GenerativeModel('gemini-2.5-flash')

try:
    response = model.generate_content("Say hello!")
    print("✅ API Key works!")
    print(f"Response: {response.text}")
except Exception as e:
    print(f"❌ API Key failed: {e}")