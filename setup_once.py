import streamlit as st
import chromadb
import google.generativeai as genai
from dotenv import load_dotenv
import os
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.enums import TA_JUSTIFY, TA_CENTER, TA_LEFT
from reportlab.lib import colors
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import io
import re
from datetime import datetime
import json
from streamlit_mic_recorder import mic_recorder


st.set_page_config(
    page_title="Personal AI Legal Assistant",
    page_icon="⚖️",
    layout="wide"
)
def apply_custom_styling():
    st.markdown("""
        <style>
            .stApp {
                background-color: #121212;
                color: #e0e0e0;
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            }
            h1 {
                animation: fadeIn 1s ease-out;
                color: #58a6ff;
            }
            @keyframes fadeIn {
                from { opacity: 0; transform: translateY(-20px); }
                to { opacity: 1; transform: translateY(0); }
            }
            .stButton>button {
                border-radius: 20px;
                border: 2px solid #3081f7;
                background-color: #238636;
                color: white;
                transition: all 0.3s ease-in-out !important;
                box-shadow: 0 4px 15px 0 rgba(45, 127, 247, 0.25);
            }
            .stButton>button:hover {
                transform: translateY(-3px);
                background-color: #2ea043;
                box-shadow: 0 6px 20px 0 rgba(45, 127, 247, 0.4);
            }
            .st-expander {
                border: 1px solid #30363d;
                border-radius: 10px;
                margin-top: 1rem;
                background-color: #222;
                color: #e0e0e0;
            }
            .st-expander header {
                font-size: 1.25rem;
                color: #58a6ff;
            }
            textarea, select, input {
                background-color: #222 !important;
                color: #ddd !important;
                border: 1px solid #555 !important;
            }
            .feature-container {
                position: relative;
                padding: 1rem 1rem 1.5rem;
                border: 1px solid #30363d;
                border-radius: 10px;
                background-color: #222;
                margin-bottom: 2rem;
            }
            .close-btn {
                position: absolute;
                top: 10px;
                right: 10px;
                font-weight: bold;
                cursor: pointer;
                font-size: 18px;
                color: #ff4b4b;
                user-select: none;
                z-index: 10;
                background: #222;
                border: none;
            }
        </style>
    """, unsafe_allow_html=True)

# --- Core Application Functions ---

load_dotenv()

@st.cache_resource
def configure_genai():
    api_key = os.getenv('GEMINI_API_KEY')
    if not api_key:
        st.error("⚠️ API Key not found in .env file!", icon="🚨")
        st.stop()
    genai.configure(api_key=api_key)
    return genai.GenerativeModel('gemini-2.5-flash')

@st.cache_resource
def load_chroma():
    client = chromadb.PersistentClient(path="./chroma_db")
    return client.get_collection(name="ipc_sections")

@st.cache_resource
def register_font():
    font_path = "DejaVuSans.ttf"
    if os.path.exists(font_path):
        pdfmetrics.registerFont(TTFont('DejaVu', font_path))
        return 'DejaVu'
    else:
        st.warning(f"Font file '{font_path}' not found. PDF export for non-English languages may fail.")
        return 'Helvetica'

def transcribe_audio_and_detect_language(audio_bytes):
    audio_file = {"mime_type": "audio/wav", "data": audio_bytes}
    prompt = """Analyze the audio. Provide a minified JSON with "transcription" and "language" keys. Example: {"transcription": "text", "language": "English"}"""
    try:
        response = model.generate_content([prompt, audio_file])
        json_str = response.text.strip().lstrip("``````")
        result = json.loads(json_str)
        return result.get("transcription"), result.get("language")
    except Exception as e:
        st.error(f"Audio processing error: {e}")
        return None, None

def detect_language_of_text(text):
    prompt = f"Identify the language of this text. Respond with only the language name.\nText: \"{text}\""
    try:
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception:
        return "English"

def translate_text(text, target_language, source_language="auto"):
    prompt = f"Translate the following text from {source_language} to {target_language}:\n\n{text}"
    try:
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception:
        return text

def generate_pdf(complaint_text):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=60, leftMargin=60, topMargin=50, bottomMargin=50)
    elements = []
    styles = getSampleStyleSheet()
    font_name = REGISTERED_FONT
    title_style = ParagraphStyle('CustomTitle', parent=styles['Heading1'], fontName=font_name, fontSize=18, textColor=colors.black, spaceAfter=20, alignment=TA_CENTER)
    heading_style = ParagraphStyle('CustomHeading', parent=styles['Heading2'], fontName=font_name, fontSize=13, textColor=colors.black, spaceAfter=10, spaceBefore=15)
    body_style = ParagraphStyle('CustomBody', parent=styles['BodyText'], fontName=font_name, fontSize=11, textColor=colors.black, alignment=TA_JUSTIFY, spaceAfter=8, leading=16)
    address_style = ParagraphStyle('AddressStyle', parent=styles['BodyText'], fontName=font_name, fontSize=11, textColor=colors.black, alignment=TA_LEFT, spaceAfter=6, leading=14)
    def create_blank_line(width_inches=3):
        return f'{"_" * int(width_inches * 20)}'
    def process_text_for_pdf(text):
        patterns = [
            (r'\[Police Station Name.*?\]', create_blank_line(3)), (r'\[City, State, India.*?\]', create_blank_line(3)),
            (r'\[Current Date.*?\]', datetime.now().strftime("%B %d, %Y")), (r'\[Date of incident.*?\]', create_blank_line(2)),
            (r'\[Time of incident.*?\]', create_blank_line(2)), (r'\[.*?Name.*?\]', create_blank_line(3)),
            (r'\[.*?Address.*?\]', create_blank_line(4)), (r'\[.*?Contact.*?\]', create_blank_line(2.5)),
            (r'\[User\'s Signature.*?\]', create_blank_line(2.5)), (r'\[Complainant\'s.*?\]', create_blank_line(3)),
            (r'\[User\'s.*?\]', create_blank_line(3)), (r'\[.*?description of the person.*?\]', create_blank_line(5)),
        ]
        for pattern, replacement in patterns:
            text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
        return text
    lines = complaint_text.split('\n')
    for line in lines:
        line = line.strip()
        if not line:
            elements.append(Spacer(1, 0.15 * inch))
            continue
        processed_line = process_text_for_pdf(line).replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
        if 'LEGAL COMPLAINT' in line.upper() and len(line) < 30:
            elements.append(Paragraph(line, title_style))
        elif any(keyword in line for keyword in ['Parties Involved', 'Factual Summary', 'Applicable Legal Sections', 'Demand or Request', 'Verification', 'Date:', 'Sender Details', 'Signature:']):
            elements.append(Paragraph(processed_line, heading_style))
        elif line.startswith('To,'):
            elements.append(Paragraph(processed_line, address_style))
        else:
            elements.append(Paragraph(processed_line, body_style))
    doc.build(elements)
    pdf_data = buffer.getvalue()
    buffer.close()
    return pdf_data

def is_legal_query(user_query):
    prompt = f"Is the following text a legal query related to Indian law? Answer ONLY 'Yes' or 'No'.\nText: \"{user_query}\""
    try:
        response = model.generate_content(prompt)
        return 'yes' in response.text.strip().lower()
    except Exception:
        return False

def search_relevant_sections(user_query, num_results=5):
    results = collection.query(query_texts=[user_query], n_results=num_results)
    relevant_sections = []
    if results and results.get('ids') and results['ids'][0]:
        for i in range(len(results['ids'][0])):
            metadata = results['metadatas'][0][i]
            document = results['documents'][0][i]
            relevant_sections.append({
                'section_number': metadata.get('section_number', 'N/A'),
                'title': metadata.get('title', 'N/A'),
                'description': document
            })
    return relevant_sections

def generate_legal_complaint(user_scenario, ipc_sections):
    sections_text = "\n".join([f"• Section {s['section_number']}: {s['title']}\n  Description: {s['description']}" for s in ipc_sections]) if ipc_sections else "Based on the user's description."
    prompt = f"""Generate a formal legal complaint for Indian law based on this scenario: '{user_scenario}'. 
    Relevant IPC sections found: 
    {sections_text}
    Structure the complaint professionally with the following sections:
    - LEGAL COMPLAINT (Title)
    - To, The Station House Officer, [Police Station Name], [City, State, India]
    - Date: [Current Date]
    - Parties Involved: (Complainant and Accused)
    - Factual Summary:
    - Applicable Legal Sections:
    - Demand or Request:
    - Sender Details:
    - Verification:
    - Signature:
    Fill in the details based on the user's scenario. Use placeholders like [Police Station Name] for information not provided."""
    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"Error: Could not generate complaint. {e}"

def process_input(container, original_text, detected_language, output_language):
    with container:
        if not original_text:
            st.error("Could not get text from input. Please try again.")
            st.stop()
        text_for_processing = original_text
        if detected_language and detected_language.lower() != "english":
            with st.spinner(f"Translating from {detected_language} to English..."):
                text_for_processing = translate_text(original_text, "English", source_language=detected_language)
        with st.spinner("🕵️ Validating query..."):
            is_legal = is_legal_query(text_for_processing)
        if is_legal:
            st.success("✅ Valid legal query detected!")
            with st.spinner("🔍 Searching IPC database..."):
                ipc_sections = search_relevant_sections(text_for_processing)
            with st.expander("Show/Hide Found IPC Sections", expanded=True):
                if not ipc_sections:
                    st.write("No specific IPC sections found.")
                else:
                    for section in ipc_sections:
                        st.markdown(f"**Section {section['section_number']}: {section['title']}**")
                        st.write(section['description'])
                        st.divider()
            with st.spinner("📝 Generating complaint..."):
                english_complaint = generate_legal_complaint(text_for_processing, ipc_sections)
            final_output_language = detected_language if output_language == "Auto-Detect" else output_language
            final_complaint = english_complaint
            if final_output_language and final_output_language.lower() != "english":
                with st.spinner(f"Translating to {final_output_language}..."):
                    final_complaint = translate_text(english_complaint, final_output_language, "English")
                st.success(f"✅ Document translated to {final_output_language}!")
            else:
                st.success("✅ Complaint generated successfully!")
            st.subheader("📄 Generated Legal Document")
            st.markdown(final_complaint)
            b_col1, b_col2 = st.columns(2)
            b_col1.download_button("📥 Download as Text", final_complaint, "legal_complaint.txt", use_container_width=True)
            try:
                pdf_data = generate_pdf(final_complaint)
                b_col2.download_button("📄 Download as PDF", pdf_data, "legal_complaint.pdf", "application/pdf", use_container_width=True)
            except Exception as e:
                b_col2.error(f"PDF Error: {e}")
        else:
            st.warning("⚠️ This tool is for Indian legal queries only.", icon="⚠️")
            st.stop()

# --- Main UI ---
apply_custom_styling()
model = configure_genai()
collection = load_chroma()
REGISTERED_FONT = register_font()

st.title("⚖️ Personal AI Legal Assistant")
st.markdown("Describe your legal issue using your voice or by typing. The assistant will analyze it, find relevant IPC sections, and generate a formal complaint.")

if 'show_voice' not in st.session_state:
    st.session_state.show_voice = True
if 'show_text' not in st.session_state:
    st.session_state.show_text = True
def hide_voice_content():
    st.session_state.show_voice = False
    st.session_state.show_text = True
def hide_text_content():
    st.session_state.show_text = False
    st.session_state.show_voice = True

if st.session_state.show_voice:
    with st.container():
        st.markdown('<div class="feature-container">', unsafe_allow_html=True)
        close_button = st.button('✕ Close Voice Input', key='close_voice_btn')
        if close_button:
            hide_voice_content()
            st.experimental_rerun()
        st.subheader("🎤 Record Your Issue")
        output_lang_voice = st.selectbox("Select Output Language:", ("Auto-Detect", "English", "Hindi", "Telugu", "Tamil"), key='lang_voice')
        audio_info = mic_recorder(start_prompt="Click to Record 🎙️", stop_prompt="Stop Recording ⏹️", key='recorder')
        if st.button("Analyze Voice Input", use_container_width=True, type="primary", key='voice_button'):
            if audio_info and audio_info['bytes']:
                with st.spinner("Transcribing audio..."):
                    original_text, detected_lang = transcribe_audio_and_detect_language(audio_info['bytes'])
                if original_text:
                    st.info(f"Transcribed (Detected {detected_lang}): \"{original_text}\"")
                    process_input(st.container(), original_text, detected_lang, output_lang_voice)
            else:
                st.warning("Please record your voice first!")
        st.markdown('</div>', unsafe_allow_html=True)
else:
    st.markdown('<br><br>', unsafe_allow_html=True)

if st.session_state.show_text:
    with st.container():
        st.markdown('<div class="feature-container">', unsafe_allow_html=True)
        close_button_2 = st.button('✕ Close Text Input', key='close_text_btn')
        if close_button_2:
            hide_text_content()
            st.experimental_rerun()
        st.subheader("📝 Or Type Your Issue")
        output_lang_text = st.selectbox("Select Output Language:", ("Auto-Detect", "English", "Hindi", "Telugu", "Tamil"), key='lang_text')
        user_input_text = st.text_area("Describe your legal issue here:", height=150, placeholder="e.g., A man broke into my house...")
        if st.button("Analyze Text Input", use_container_width=True, type="primary", key='text_button'):
            if user_input_text.strip():
                with st.spinner("Detecting language..."):
                    detected_lang = detect_language_of_text(user_input_text)
                st.info(f"Language Detected: {detected_lang}")
                process_input(st.container(), user_input_text, detected_lang, output_lang_text)
            else:
                st.warning("Please type your legal issue first!")
        st.markdown('</div>', unsafe_allow_html=True)
else:
    st.markdown('<br><br>', unsafe_allow_html=True)
