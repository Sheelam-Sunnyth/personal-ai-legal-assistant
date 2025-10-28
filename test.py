import google.generativeai as genai

# Replace this with your actual API key
API_KEY = "AIzaSyCTBw3o0F6bWIGptsmPk9nkNblUih86CDQ"

genai.configure(api_key=API_KEY)
model = genai.GenerativeModel('gemini-2.5-flash')

try:
    response = model.generate_content("Say hello!")
    print("✅ API Key works!")
    print(f"Response: {response.text}")
except Exception as e:
    print(f"❌ API Key failed: {e}")