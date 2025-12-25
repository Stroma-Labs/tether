# ------------------------------------------------------------------
# APP.PY V6.7.5 (Logging Schema Fix)
# ------------------------------------------------------------------
# Changelog:
# 1. Logging: Rewrote log_to_gsheets to match the EXACT columns in your Google Sheet.
# 2. Logic: Added Session ID generation (UUID) to track user sessions.
# 3. Data: Now logging the full AI Output Report ("Output_Report") and Gap Delta.
# ------------------------------------------------------------------

import streamlit as st
import re
import fitz  # PyMuPDF
import docx
import pandas as pd
import altair as alt
import google.generativeai as genai
from streamlit_gsheets import GSheetsConnection
from datetime import datetime
import uuid

# ------------------------------------------------------------------
# CONFIGURATION & SECRETS
# ------------------------------------------------------------------
st.set_page_config(page_title="Tether V6.7.5", page_icon="🧬", layout="wide")

# Initialize Session ID if not present
if 'session_id' not in st.session_state:
    st.session_state['session_id'] = str(uuid.uuid4())

# Setup Gemini
if "gemini" in st.secrets:
    genai.configure(api_key=st.secrets["gemini"]["api_key"])
else:
    st.error("Gemini API Key not found. Please add it to Streamlit Secrets.")
    st.stop()

# ------------------------------------------------------------------
# 1. CORE LOGIC
# ------------------------------------------------------------------

BRIDGE_VERBS = [
    "negotiate", "close", "prospect", "canvass", "pitch", "lobby", "advocate", 
    "rally", "galvanize", "broker", "influence", "charm", "convert", "recruit", 
    "source", "interview", "hire", "onboard", "persuade", "sell", "upsell",
    "win", "secure", "capture", "retain", "deal", "network",
    "align", "unify", "integrate", "merge", "mentor", "coach", "empower", 
    "facilitate", "mediate", "liaise", "collaborate", "partner", "guide", 
    "teach", "train", "present", "speak", "communicate", "translate", 
    "bridge", "connect", "represent", "champion", "evangelize", "foster",
    "cultivate", "nurture", "relationship", "stakeholder"
]

BUILDER_VERBS = [
    "build", "architect", "engineer", "develop", "code", "program", "design",
    "create", "construct", "forge", "implement", "deploy", "launch", "ship",
    "prototype", "draft", "compose", "write", "author", "fabricate", "assemble",
    "invent", "innovate", "pioneer", "found", "establish", "generate", "produce",
    "craft", "devise", "formulate", "conceptualize", "model"
]

OPERATOR_VERBS = [
    "manage", "operate", "run", "maintain", "support", "administer", "optimize",
    "streamline", "scale", "execute", "process", "handle", "oversee", "supervise",
    "direct", "coordinate", "monitor", "track", "report", "analyze", "audit",
    "ensure", "enforce", "comply", "regulate", "budget", "forecast", "schedule",
    "logistics", "inventory", "efficiency", "workflow", "systematize", "organize"
]

SALES_KEYWORDS = ["sales", "account", "business development", "biz dev", "recruiter", "talent acquisition", "pr", "public relations", "brand", "marketing", "client", "customer success"]
EXECUTIVE_KEYWORDS = ["chief", "president", "vp", "vice president", "head of", "director", "founder", "c-suite", "principal"]

def analyze_archetype(text):
    text_lower = text.lower()
    words = re.findall(r'\b\w+\b', text_lower)
    
    builder_score = sum(10 for w in words if w in BUILDER_VERBS)
    operator_score = sum(10 for w in words if w in OPERATOR_VERBS)
    bridge_score = sum(10 for w in words if w in BRIDGE_VERBS)

    is_commercial = any(k in text_lower for k in SALES_KEYWORDS)
    is_executive = any(k in text_lower for k in EXECUTIVE_KEYWORDS)

    if is_commercial:
        bridge_score = int(bridge_score * 1.5)

    if is_executive:
        shift = int(operator_score * 0.2)
        operator_score -= shift
        bridge_score += shift

    total = builder_score + operator_score + bridge_score
    if total == 0:
        return {"Builder": 0, "Operator": 0, "Bridge": 0, "Total": 1}

    return {
        "Builder": builder_score,
        "Operator": operator_score,
        "Bridge": bridge_score,
        "Total": total
    }

def get_archetype_percentages(scores):
    total = scores['Total']
    pcts = {
        "Builder": round((scores['Builder'] / total) * 100),
        "Operator": round((scores['Operator'] / total) * 100),
        "Bridge": round((scores['Bridge'] / total) * 100)
    }
    sorted_pcts = sorted(pcts.items(), key=lambda x: x[1], reverse=True)
    primary = sorted_pcts[0]
    secondary = sorted_pcts[1]
    
    gap = primary[1] - secondary[1]
    is_hybrid = gap < 20
    
    return pcts, sorted_pcts, is_hybrid

# ------------------------------------------------------------------
# 2. FILE PARSING
# ------------------------------------------------------------------

def extract_text_from_pdf(file):
    doc = fitz.open(stream=file.read(), filetype="pdf")
    text = ""
    for page in doc:
        text += page.get_text()
    return text

def extract_text_from_docx(file):
    doc = docx.Document(file)
    text = "\n".join([para.text for para in doc.paragraphs])
    return text

# ------------------------------------------------------------------
# 3. GEMINI AI GENERATION
# ------------------------------------------------------------------

def generate_stroma_audit(text, pcts, sorted_pcts, is_hybrid):
    primary_name = sorted_pcts[0][0]
    secondary_name = sorted_pcts[1][0]
    
    identity_instruction = ""
    if is_hybrid:
        identity_instruction = f"This user is a hybrid ({primary_name} + {secondary_name}). Acknowledge both strengths in the identity section."
    else:
        identity_instruction = f"This user is a dominant {primary_name}. Focus 100% on their {primary_name} nature."

    prompt = f"""
    You are Nex, Stroma Lab's proprietary career profiling AI. 
    Review the resume and the DNA Signal.
    
    Signal DNA:
    - {primary_name}: {sorted_pcts[0][1]}%
    - {secondary_name}: {sorted_pcts[1][1]}%
    - {sorted_pcts[2][0]}: {sorted_pcts[2][1]}%
    
    INSTRUCTIONS:
    1. Write in a direct, professional, slightly clinical but empowering mentor-like tone.
    2. **First-Person Voice:** In the 'Hero Statement', use "I..." phrasing.
    3. {identity_instruction}
    
    OUTPUT FORMAT:
    
    ## Your Tether Audit

    ### 1. THE MIRROR
    [Define who they are. 2-3 sentences max.]
    
    **Hero Statement:** [A single, bold First-Person sentence summarizing their value.]

    ### 2. THE ENVIRONMENT
    [Describe the specific ecosystem where this archetype thrives. Be diagnostic, not poetic.]
    * **Culture:** (Focus on Incentives. Does this person need a culture that rewards speed, precision, consensus, or bold risk-taking?)
    * **Structure:** (Focus on Autonomy. Do they need a flat matrix, a rigid hierarchy, or a "skunkworks" lab environment to function?)
    * **The Trap:** (The "Kryptonite." Identify the specific corporate dysfunction—e.g., analysis paralysis, micromanagement, lack of vision—that turns this high-performer into a low-performer.)
    
    ### 3. THE PROOF
    [Find 3 weak/passive bullet points in the resume text and rewrite them to sound like a {primary_name}.]
    * **Original:** ...
    * **Rewritten:** ...
    
    RESUME TEXT:
    {text[:3000]}
    """
    
    try:
        model = genai.GenerativeModel('gemini-2.0-flash') 
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"Error generating audit: {e}"

# ------------------------------------------------------------------
# 4. LOGGING (SCHEMA MATCHED)
# ------------------------------------------------------------------
def log_to_gsheets(text, pcts, sorted_pcts, audit_result, is_hybrid):
    try:
        conn = st.connection("gsheets", type=GSheetsConnection)
        
        # 1. Prepare Data to match EXACT Sheet Columns
        primary = sorted_pcts[0][0]
        secondary = sorted_pcts[1][0]
        delta = sorted_pcts[0][1] - sorted_pcts[1][1]
        
        # Determine Label
        if is_hybrid:
            label = f"{primary} + {secondary}"
        else:
            label = primary
            
        new_row = pd.DataFrame([{
            "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "Session_ID": st.session_state['session_id'],
            "Archetype_Label": label,
            "Archetype_Primary": primary,
            "Archetype_Secondary": secondary,
            "Gap_Delta": delta,
            "Score_Builder": pcts['Builder'],
            "Score_Operator": pcts['Operator'],
            "Score_Bridge": pcts['Bridge'],
            "Input_Redacted": text[:500] + "...", # Safe snippet
            "Output_Report": audit_result
        }])
        
        # 2. Read, Concat, Update
        existing_data = conn.read(worksheet="Logs", usecols=list(range(11)), ttl=5)
        updated_data = pd.concat([existing_data, new_row], ignore_index=True)
        conn.update(worksheet="Logs", data=updated_data)
        return True
    except Exception as e:
        print(f"Logging Error: {e}")
        return False

# ------------------------------------------------------------------
# 5. UI/UX
# ------------------------------------------------------------------

st.title("Tether.")
st.markdown("Upload your resume. See who you actually are.")

uploaded_file = st.file_uploader("Upload PDF or DOCX", type=["pdf", "docx"])

if uploaded_file is not None:
    # 1. Parse
    if uploaded_file.name.endswith(".pdf"):
        resume_text = extract_text_from_pdf(uploaded_file)
    else:
        resume_text = extract_text_from_docx(uploaded_file)
        
    # 2. Analyze
    scores = analyze_archetype(resume_text)
    pcts, sorted_pcts, is_hybrid = get_archetype_percentages(scores)
    
    primary_name = sorted_pcts[0][0]
    secondary_name = sorted_pcts[1][0]
    
    # 3. Visuals (Top Section)
    st.divider()
    
    st.caption("Dominant Strength")
    if is_hybrid:
        st.header(f"{primary_name} + {secondary_name}")
    else:
        st.header(primary_name)
    
    # Layout
    col1, col2 = st.columns([1, 2])
    
    with col1:
        legend_col, chart_col = st.columns([0.5, 1])
        
        with legend_col:
            st.markdown("##### Signal DNA")
            color_map = {"Builder": "#20BF55", "Operator": "#2F75C6", "Bridge": "#E1BC29"}
            
            for arch in ['Builder', 'Operator', 'Bridge']:
                color = color_map[arch]
                pct = pcts[arch]
                st.markdown(f"<span style='color:{color}'>■</span> {arch} {pct}%", unsafe_allow_html=True)

        with chart_col:
            chart_df = pd.DataFrame({
                'Archetype': ['Builder', 'Operator', 'Bridge'],
                'Percentage': [pcts['Builder'], pcts['Operator'], pcts['Bridge']],
                'Color': ['#20BF55', '#2F75C6', '#E1BC29']
            })
            
            donut = alt.Chart(chart_df).mark_arc(innerRadius=40).encode(
                theta=alt.Theta(field="Percentage", type="quantitative"),
                color=alt.Color(field="Color", type="nominal", scale=None),
                tooltip=['Archetype', 'Percentage']
            ).properties(width=160, height=160)
            
            st.altair_chart(donut, use_container_width=False)

    with col2:
        with st.spinner("Calibrating the Mirror..."):
            audit_result = generate_stroma_audit(resume_text, pcts, sorted_pcts, is_hybrid)
            st.markdown(audit_result)
            
            # Log Data (Using New Schema)
            log_to_gsheets(resume_text, pcts, sorted_pcts, audit_result, is_hybrid)
            
# Footer
st.markdown(
    """
    <div style='text-align: center; color: rgba(255, 255, 255, 0.5); font-size: 12px; margin-top: 20px; font-weight: 300;'>
        © 2025 Stroma Labs. All rights reserved.
    </div>
    """, 
    unsafe_allow_html=True
)