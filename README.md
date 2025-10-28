# ⚖️ Personal AI Legal Assistant

## 📘 Overview
The **Personal AI Legal Assistant** is a Streamlit-based AI web app designed to help people in India file **legal complaints** easily.  
Users can **speak or type** their legal issues, and the system automatically:

1. Understands the problem  
2. Finds relevant **Indian Penal Code (IPC)** sections  
3. Generates a **formal legal complaint**  
4. Translates it to the user’s preferred language  
5. Allows downloading as a **PDF or text file**

---

## 🧠 Features
- 🎤 **Voice & Text Input** — Speak or type your problem in any language  
- 🧾 **Automatic IPC Section Finder** — Uses **semantic search** via ChromaDB  
- ⚙️ **AI-Powered Complaint Generator** — Drafts formal legal complaints  
- 🌐 **Multilingual Support** — Supports English, Hindi, Telugu, Tamil  
- 📄 **PDF Export** — Generates professional legal complaint documents  
- 🔒 **Secure API Handling** — API keys stored safely in `.env` file  

---

## 🗂️ Project Structure
LEGAL_ASSISTANT/
│
├── app.py # Main Streamlit application
├── setup_once.py # One-time setup script for database
├── .env # API key storage (not uploaded to GitHub)
├── requirements.txt # Dependencies list
├── DejaVuSans.ttf # Font for multi-language PDF generation
├── chroma_db/ # Local ChromaDB database (auto-created)
│ ├── chroma.sqlite3
│ └── <vector_data_files>
└── ipc_data.json # Contains all Indian Penal Code sections
## ⚙️ Installation

### 1. Clone this repository
```bash
git clone https://github.com/<your-username>/<repo-name>.git
cd <repo-name>

2. Install dependencies
Make sure you have Python 3.10+ installed.
pip install -r requirements.txt

3. Set up your Google Gemini API key
Go to https://aistudio.google.com/apikey
Create an API key
Create a file named .env in your project folder and add:
GEMINI_API_KEY=your_api_key_here

4. Run database setup (only once)
python setup_once.py

5. Launch the application
streamlit run app.py
Then open the local URL (e.g., http://localhost:8501) in your browser.

🧠 How It Works
User inputs their issue (voice/text)
System detects the language
Converts it to English (if needed)
Validates if it’s a legal query
Finds relevant IPC sections using ChromaDB
Generates a formal complaint
Translates to chosen language
Provides download options (Text/PDF)

🚀 Future Enhancements
⚖️ Add case law search
👨‍⚖️ Include lawyer directory
📎 Enable document uploads
💬 Add chat interface for follow-ups
📶 Support offline AI models

🛡️ Security Notes
.env file is listed in .gitignore
API key is never hardcoded
Input validation & error handling prevent crashes

👨‍💻 Author
Sheelam Sunnyth 

## 📜 License
This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.