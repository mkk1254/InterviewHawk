import streamlit as st
import os
import tempfile
from pypdf import PdfReader
from fpdf import FPDF
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import SystemMessage, HumanMessage
from dotenv import load_dotenv

# --- 1. LOAD ENV VARIABLES ---
load_dotenv()  # This loads the .env file

# --- PAGE SETUP ---
st.set_page_config(page_title="InterviewHawk", page_icon="🦅")

# --- FUNCTIONS ---

def get_gemini_response(api_key, system_role, user_text):
    if not api_key:
        return "Error: API Key is missing."
    
    try:
        llm = ChatGoogleGenerativeAI(
            model="gemini-1.5-flash",
            temperature=0.3,
            google_api_key=api_key,
            convert_system_message_to_human=True
        )
        messages = [
            SystemMessage(content=system_role),
            HumanMessage(content=user_text)
        ]
        return llm.invoke(messages).content
    except Exception as e:
        return f"Error connecting to AI: {str(e)}"

def extract_text(uploaded_file):
    try:
        reader = PdfReader(uploaded_file)
        text = "\n".join([page.extract_text() for page in reader.pages if page.extract_text()])
        return text
    except Exception as e:
        st.error(f"Error reading PDF: {e}")
        return ""

def create_pdf(text_content):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    clean_text = text_content.encode('latin-1', 'replace').decode('latin-1')
    pdf.multi_cell(0, 10, clean_text)
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
    pdf.output(temp_file.name)
    return temp_file.name

# --- MAIN UI ---

st.title("🦅 InterviewHawk")
st.caption("AI-Powered Resume Screening & Mock Interview Agent")

# Sidebar
with st.sidebar:
    st.header("⚙️ Setup")
    
    # 2. AUTO-DETECT KEY
    # It tries to find the key in the environment first
    env_key = os.getenv("GOOGLE_API_KEY", "")
    
    # If found, it pre-fills the box (masked). If not, it's empty.
    api_key = st.text_input("Gemini API Key", value=env_key, type="password")
    
    if not api_key:
        st.warning("⚠️ No API Key found in .env or input.")
    else:
        st.success("✅ API Key Loaded")

    uploaded_file = st.file_uploader("Upload Resume (PDF)", type=["pdf"])
    job_desc = st.text_area("Job Description", "Software Engineer - Python")
    start_btn = st.button("Start Interview", type="primary")

# Session State
if "questions" not in st.session_state:
    st.session_state.questions = []
if "answers" not in st.session_state:
    st.session_state.answers = {}
if "analysis_done" not in st.session_state:
    st.session_state.analysis_done = False

# --- LOGIC FLOW ---

if start_btn and uploaded_file and api_key:
    with st.spinner("🦅 Hawk is analyzing your resume..."):
        resume_text = extract_text(uploaded_file)
        
        if resume_text:
            # Agent 1: Screener
            screener_prompt = f"Resume:\n{resume_text}\n\nJob Description:\n{job_desc}\n\nFind 3 weak areas or missing skills. Return ONLY a python list of strings."
            weaknesses = get_gemini_response(api_key, "You are a ruthless tech recruiter.", screener_prompt)
            
            # Agent 2: Interviewer
            question_prompt = f"Weaknesses found:\n{weaknesses}\n\nGenerate 3 hard technical interview questions to test these weaknesses. Return ONLY a numbered list."
            questions_raw = get_gemini_response(api_key, "You are a Senior Engineer.", question_prompt)
            
            # Formatting
            q_list = [q for q in questions_raw.split('\n') if '?' in q]
            if len(q_list) < 3:
                q_list = ["Describe a difficult bug you fixed.", "Explain a project from your resume.", "What is your biggest weakness?"]
                
            st.session_state.questions = q_list[:3]
            st.session_state.analysis_done = True
            st.rerun()

# --- CHAT INTERFACE ---

if st.session_state.analysis_done:
    st.success("Resume Analyzed! Answer these questions:")
    
    with st.form("interview_form"):
        for i, q in enumerate(st.session_state.questions):
            st.markdown(f"**Question {i+1}:** {q}")
            st.session_state.answers[f"q{i}"] = st.text_area(f"Your Answer {i+1}", key=f"ans_{i}")
        
        submit = st.form_submit_button("Submit Answers & Get Report")

    if submit:
        with st.spinner("🦅 Grading your answers..."):
            full_text = ""
            for i, q in enumerate(st.session_state.questions):
                ans = st.session_state.answers.get(f"q{i}", "No Answer")
                full_text += f"Q: {q}\nA: {ans}\n\n"
            
            feedback_prompt = f"Grade these interview answers. Provide a Pass/Fail decision, a score (0-100), and feedback.\n\n{full_text}"
            report = get_gemini_response(api_key, "You are a Hiring Manager.", feedback_prompt)
            
            st.markdown("### 📝 Interview Report")
            st.write(report)
            
            pdf_path = create_pdf(f"INTERVIEWHAWK REPORT\n\n{report}")
            with open(pdf_path, "rb") as f:
                st.download_button("Download Official PDF", f, file_name="InterviewHawk_Report.pdf")

elif not uploaded_file:
    st.info("👈 Please upload a resume in the sidebar to begin.")