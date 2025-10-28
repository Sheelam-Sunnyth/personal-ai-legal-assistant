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

# --- Page configuration ---
st.set_page_config(
    page_title="Personal AI Legal Assistant",
    page_icon="⚖️",
    layout="wide"
)

# --- Core Application Functions ---

@st.cache_resource
def configure_genai():
    """Loads API key and configures the Generative AI model."""
    load_dotenv()
    api_key = os.getenv('GEMINI_API_KEY')
    if not api_key:
        st.error("⚠️ API Key not found in .env file!", icon="🚨")
        st.stop()
    genai.configure(api_key=api_key)
    return genai.GenerativeModel('gemini-2.5-pro')

@st.cache_resource
def load_chroma():
    """Loads the ChromaDB collection."""
    client = chromadb.PersistentClient(path="./chroma_db")
    return client.get_collection(name="ipc_sections")

@st.cache_resource
def register_font():
    """Registers the DejaVu font for PDF generation."""
    font_path = "DejaVuSans.ttf"
    if os.path.exists(font_path):
        pdfmetrics.registerFont(TTFont('DejaVu', font_path))
        return 'DejaVu'
    else:
        st.warning(f"Font file '{font_path}' not found. PDF export for non-English languages may fail.")
        return 'Helvetica'

def transcribe_audio_and_detect_language(model, audio_bytes):
    """Transcribes audio and detects the language using the AI model."""
    audio_file = {"mime_type": "audio/wav", "data": audio_bytes}
    prompt = """Analyze the audio. Provide a minified JSON with "transcription" and "language" keys. Example: {"transcription": "text", "language": "English"}"""
    try:
        response = model.generate_content([prompt, audio_file])
        json_str = response.text.strip().lstrip("```json").rstrip("```")
        result = json.loads(json_str)
        return result.get("transcription"), result.get("language")
    except Exception as e:
        st.error(f"Audio processing error: {e}")
        return None, None

def detect_language_of_text(model, text):
    """Detects the language of a given text."""
    prompt = f"Identify the language of this text. Respond with only the language name.\nText: \"{text}\""
    try:
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception:
        return "English"

def translate_text(model, text, target_language, source_language="auto"):
    """Translates text from a source to a target language."""
    prompt = f"Translate the following text from {source_language} to {target_language}:\n\n{text}"
    try:
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception:
        return text

def generate_pdf(complaint_text, font_name):
    """Generates a professionally formatted PDF from the complaint text."""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=60, leftMargin=60, topMargin=50, bottomMargin=50)
    elements = []
    styles = getSampleStyleSheet()

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


def is_legal_query(model, user_query):
    """Checks if the user's query is legal in nature."""
    prompt = f"Is the following text a legal query related to Indian law? Answer ONLY 'Yes' or 'No'.\nText: \"{user_query}\""
    try:
        response = model.generate_content(prompt)
        return 'yes' in response.text.strip().lower()
    except Exception:
        return False

def search_relevant_sections(collection, user_query, num_results=5):
    """Searches ChromaDB for relevant IPC sections."""
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

def generate_legal_complaint(model, user_scenario, ipc_sections):
    """Generates the legal complaint text using the AI model."""
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

def process_and_display_results(original_text, detected_language, output_language):
    """The main logic to process input and display the full output."""
    
    text_for_processing = original_text
    if detected_language and detected_language.lower() != "english":
        with st.spinner(f"Translating from {detected_language} to English..."):
            text_for_processing = translate_text(model, original_text, "English", source_language=detected_language)

    with st.spinner("🕵️ Validating query..."):
        is_legal = is_legal_query(model, text_for_processing)

    if is_legal:
        st.success("✅ Valid legal query detected!")
        
        with st.spinner("🔍 Searching IPC database..."):
            ipc_sections = search_relevant_sections(collection, text_for_processing)
        
        st.subheader("📋 Found Relevant IPC Sections")
        if not ipc_sections:
            st.write("No specific IPC sections found.")
        else:
            for section in ipc_sections:
                st.markdown(f"**Section {section['section_number']}: {section['title']}**")
                st.write(section['description'])
                st.divider()
        
        with st.spinner("📝 Generating complaint..."):
            english_complaint = generate_legal_complaint(model, text_for_processing, ipc_sections)
        
        final_output_language = detected_language if output_language == "Auto-Detect" else output_language
        
        final_complaint = english_complaint
        if final_output_language and final_output_language.lower() != "english":
            with st.spinner(f"Translating to {final_output_language}..."):
                final_complaint = translate_text(model, english_complaint, final_output_language, "English")
            st.success(f"✅ Document translated to {final_output_language}!")
        else:
            st.success("✅ Complaint generated successfully!")
            
        st.subheader("📄 Generated Legal Document")
        st.markdown(final_complaint)
        
        col1, col2 = st.columns(2)
        with col1:
            st.download_button("📥 Download as Text", final_complaint, "legal_complaint.txt", use_container_width=True)
        with col2:
            try:
                pdf_data = generate_pdf(final_complaint, REGISTERED_FONT)
                st.download_button("📄 Download as PDF", pdf_data, "legal_complaint.pdf", "application/pdf", use_container_width=True)
            except Exception as e:
                st.error(f"PDF Error: {e}")
    else:
        st.warning("⚠️ This tool is for Indian legal queries only.", icon="⚠️")


# --- Main UI ---
st.title("⚖️ Personal AI Legal Assistant")
st.markdown("Describe your legal issue using your voice or by typing. The assistant will analyze it, find relevant IPC sections, and generate a formal complaint.")

# --- Load shared resources ---
model = configure_genai()
collection = load_chroma()
REGISTERED_FONT = register_font()


# --- Voice Input Section ---
st.subheader("🎤 Record Your Issue")
output_lang_voice = st.selectbox("Select Output Language (for Voice):", ("Auto-Detect", "English", "Hindi", "Telugu", "Tamil"), key='lang_voice')
audio_info = mic_recorder(start_prompt="Click to Record 🎙️", stop_prompt="Stop Recording ⏹️", key='recorder')

if st.button("Analyze Voice Input", use_container_width=True, type="primary", key="voice_button"):
    if audio_info and audio_info['bytes']:
        with st.spinner("Transcribing audio..."):
            original_text, detected_lang = transcribe_audio_and_detect_language(model, audio_info['bytes'])
        
        if original_text:
            st.info(f"Transcribed (Detected {detected_lang}): \"{original_text}\"")
            process_and_display_results(original_text, detected_lang, output_lang_voice)
    else:
        st.warning("Please record your voice first!")


st.divider()


# --- Text Input Section ---
st.subheader("📝 Or Type Your Issue")
output_lang_text = st.selectbox("Select Output Language (for Text):", ("Auto-Detect", "English", "Hindi", "Telugu", "Tamil"), key='lang_text')
user_input_text = st.text_area("Describe your legal issue here:", height=150, placeholder="e.g., A man broke into my house...")

if st.button("Analyze Text Input", use_container_width=True, type="primary", key="text_button"):
    if user_input_text.strip():
        with st.spinner("Detecting language..."):
            detected_lang = detect_language_of_text(model, user_input_text)
        
        st.info(f"Language Detected: {detected_lang}")
        process_and_display_results(user_input_text, detected_lang, output_lang_text)
    else:
        st.warning("Please type your legal issue first!")

