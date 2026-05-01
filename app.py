import streamlit as st
import json
import os
from dotenv import load_dotenv
from fpdf import FPDF
from graph import app_graph
from state import MailMindState

# Load environment variables
load_dotenv()

st.set_page_config(page_title="MailMind", page_icon="📧", layout="wide")

st.title("📧 MailMind - Your Agentic Email Assistant")
st.markdown("Automate context-aware, tone-aligned, personalized email creation.")

# Load profiles
@st.cache_data
def load_profiles():
    profiles_path = os.path.join(os.path.dirname(__file__), "profiles.json")
    try:
        with open(profiles_path, "r") as f:
            return json.load(f)
    except:
        return {"senders": {}, "recipients": {}}

profiles = load_profiles()
senders = list(profiles.get("senders", {}).keys())
recipients = list(profiles.get("recipients", {}).keys())

# Sidebar settings
with st.sidebar:
    st.header("Settings")
    sender_id = st.selectbox("Sender Profile", options=senders)
    recipient_type = st.selectbox("Recipient Type", options=recipients)
    tone = st.selectbox("Tone", options=["Formal", "Friendly", "Assertive", "Empathetic", "Concise"])
    
    st.markdown("---")
    
    with st.expander("➕ Add New Sender Profile"):
        with st.form("new_profile_form"):
            new_id = st.text_input("Profile ID (e.g., user_3)")
            new_name = st.text_input("Name*")
            new_role = st.text_input("Role")
            new_company = st.text_input("Company")
            new_style = st.text_area("Style Preferences")
            new_sign_off = st.text_area("Sign Off")
            
            if st.form_submit_button("Save Profile"):
                if new_id and new_name:
                    profiles["senders"][new_id] = {
                        "name": new_name,
                        "role": new_role,
                        "company": new_company,
                        "style_preferences": new_style,
                        "sign_off": new_sign_off
                    }
                    profiles_path = os.path.join(os.path.dirname(__file__), "profiles.json")
                    with open(profiles_path, "w") as f:
                        json.dump(profiles, f, indent=4)
                    load_profiles.clear()
                    st.success("Profile added!")
                    st.rerun()
                else:
                    st.error("Profile ID and Name are required.")

    st.markdown("---")
    st.markdown("**How it works:**")
    st.markdown("1. Enter your prompt below.\n2. 7 specialized agents collaborate to write your email.\n3. Review, edit, and export.")

# Main input
raw_prompt = st.text_area("What do you want to write an email about?", height=150, placeholder="e.g., Ask John for a quick sync on the Q3 roadmap tomorrow. Be polite but clear that it's important.")

if st.button("Generate Email 🚀", type="primary"):
    if not os.getenv("OPENAI_API_KEY"):
        st.error("Please set your OPENAI_API_KEY in the .env file.")
        st.stop()
        
    if not raw_prompt:
        st.warning("Please enter a prompt.")
        st.stop()

    initial_state = MailMindState(
        raw_prompt=raw_prompt,
        tone=tone,
        recipient_type=recipient_type,
        sender_id=sender_id,
        retry_count=0
    )

    st.markdown("### 🤖 Agents at Work...")
    
    # Run the graph and stream updates
    with st.status("Processing your request...", expanded=True) as status:
        try:
            for step in app_graph.stream(initial_state):
                node_name = list(step.keys())[0]
                state = step[node_name]
                
                if node_name == "routing":
                    if state.get("routing_decision") == "reject":
                        st.error(f"Input rejected: {state.get('error')}")
                        status.update(label="Failed at Routing", state="error")
                        st.stop()
                    else:
                        st.write("✅ Routing Agent validated prompt.")
                
                elif node_name == "parser":
                    st.write("✅ Input Parser extracted key points.")
                elif node_name == "intent":
                    st.write(f"✅ Intent Detector identified: **{state.get('intent')}**")
                elif node_name == "personalization":
                    st.write("✅ Personalization Agent applied profile context.")
                elif node_name == "draft":
                    st.write("✅ Draft Writer generated baseline draft.")
                elif node_name == "tone":
                    st.write(f"✅ Tone Stylist applied **{tone}** tone.")
                elif node_name == "review":
                    if state.get("final_email"):
                        st.write("✅ Review Validator approved the email.")
                    else:
                        st.warning(f"⚠️ Review Validator feedback: {state.get('validation_feedback')}. Retrying...")
            
            status.update(label="Email Generation Complete!", state="complete")
            st.session_state["final_email"] = state.get("final_email")
            
        except Exception as e:
            status.update(label="An error occurred", state="error")
            st.error(str(e))

# Show editor if email is generated
if "final_email" in st.session_state:
    st.markdown("### 📝 Edit & Review")
    edited_email = st.text_area("Final Draft", value=st.session_state["final_email"], height=300)
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("📤 Simulate Send"):
            st.success("Simulated sending email successfully!")
            
    with col2:
        # PDF Export
        def create_pdf(text):
            pdf = FPDF()
            pdf.add_page()
            pdf.set_font("Arial", size=12)
            # handle unicode
            text = text.encode('latin-1', 'replace').decode('latin-1')
            pdf.multi_cell(0, 10, txt=text)
            return bytes(pdf.output())
            
        pdf_bytes = create_pdf(edited_email)
        st.download_button(
            label="📄 Export to PDF",
            data=pdf_bytes,
            file_name="email_draft.pdf",
            mime="application/pdf"
        )
        
    with col3:
        if st.button("💾 Save to Memory Log"):
            log_path = os.path.join(os.path.dirname(__file__), "memory_log.jsonl")
            log_entry = {
                "prompt": raw_prompt,
                "tone": tone,
                "recipient": recipient_type,
                "final_email": edited_email
            }
            with open(log_path, "a") as f:
                f.write(json.dumps(log_entry) + "\n")
            st.success("Saved to memory log!")
