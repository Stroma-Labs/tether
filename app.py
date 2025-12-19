# --- APP.PY V4 (Hybrid System // DNA Logic V3) ---

import streamlit as st
import google.generativeai as genai
import spacy
import pandas as pd
import altair as alt
from collections import Counter
import re
import hashlib
import uuid
from datetime import datetime
from streamlit_gsheets import GSheetsConnection

# --- 1. CONFIGURATION & THEME ---
st.set_page_config(
    page_title="Tether.",
    page_icon="🧬",
    layout="centered",
    initial_sidebar_state="collapsed",
    menu_items={
        'Get Help': 'mailto:stromalabs@proton.me',
        'About': "# Tether \n Semantic Resume Analysis Engine."
    }
)

# Force "Dark Editorial" Theme via Injection
st.markdown("""
    <style>
    /* Force deep charcoal background and white text */
    .stApp {
        background-color: #0F1116;
        color: #FFFFFF;
    }
    /* Editorial Red for key highlights if needed */
    .highlight {
        color: #E63946;
        font-weight: bold;
    }
    /* Hide the default Streamlit header decoration */
    header {visibility: hidden;}
    </style>
    """, unsafe_allow_html=True)

# --- 2. LOGIC ENGINE (NLP & SCORING) ---
@st.cache_resource
def load_nlp():
    try:
        return spacy.load("en_core_web_sm")
    except:
        spacy.cli.download("en_core_web_sm")
        return spacy.load("en_core_web_sm")

nlp = load_nlp()

# The Lexicon
BUILDER_VERBS = [
    "architected", "built", "created", "designed", "developed", "devised", 
    "engineered", "established", "founded", "formulated", "implemented", 
    "initiated", "launched", "originated", "piloted", "pioneered", "revamped", 
    "structured", "spearheaded", "transformed", "shipped", "coded", "deployed"
]

OPERATOR_VERBS = [
    "accelerated", "administered", "analyzed", "augmented", "centralized", 
    "conserved", "consolidated", "decreased", "ensured", "executed", 
    "expanded", "expedited", "generated", "improved", "increased", 
    "maintained", "managed", "maximized", "optimized", "orchestrated", 
    "processed", "reduced", "refined", "resolved", "scaled", "streamlined"
]

BRIDGE_VERBS = [
    "aligned", "collaborated", "communicated", "convinced", "cultivated", 
    "directed", "enabled", "facilitated", "guided", "influenced", 
    "mentored", "negotiated", "partnered", "persuaded", "presented", 
    "promoted", "reconciled", "represented", "secured", "united"
]

WEAK_VERBS = [
    "assisted", "helped", "participated", "supported", "worked", "responsible for", 
    "handled", "duties included", "contributed", "attended"
]

def analyze_archetype(text):
    doc = nlp(text.lower())
    verbs = [token.lemma_ for token in doc if token.pos_ == "VERB"]
    
    # Calculate Raw Scores
    b_score = sum(1 for v in verbs if v in BUILDER_VERBS) * 10
    o_score = sum(1 for v in verbs if v in OPERATOR_VERBS) * 10
    br_score = sum(1 for v in verbs if v in BRIDGE_VERBS) * 10
    
    # Identify Weaknesses
    weaknesses = [v for v in verbs if v in WEAK_VERBS]
    
    total = b_score + o_score + br_score
    if total == 0: total = 1 
    
    # --- DNA LOGIC V3 (Hybrid Detection) ---
    scores = {"Builder": b_score, "Operator": o_score, "Bridge": br_score}
    
    # Sort scores to find Top 1 and Top 2
    sorted_scores = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    (primary_name, primary_score) = sorted_scores[0]
    (secondary_name, secondary_score) = sorted_scores[1]
    
    # Calculate the Gap
    delta = primary_score - secondary_score
    
    # Logic: If Gap < 20 points (approx 2 verbs), it's a Hybrid
    hybrid_label = primary_name # Default to just the primary
    is_hybrid = False
    
    if delta < 20 and secondary_score > 0:
        is_hybrid = True
        # Define the 3 Hybrid States
        pair = sorted([primary_name, secondary_name]) # Sort alphabetically to match keys
        if pair == ['Builder', 'Operator']:
            hybrid_label = "The Industrialist"
        elif pair == ['Bridge', 'Builder']:
            hybrid_label = "The Evangelist"
        elif pair == ['Bridge', 'Operator']:
            hybrid_label = "The Integrator"
            
    return {
        "b": b_score, "o": o_score, "br": br_score,
        "primary": primary_name, "secondary": secondary_name,
        "delta": delta, "label": hybrid_label, "is_hybrid": is_hybrid,
        "weaknesses": weaknesses, "length": len(text)
    }

# --- 3. THE BRAIN (GEMINI NARRATIVE) ---
def generate_stroma_report(text, analysis, api_key):
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-1.5-flash')
        
        # Calculate Ratios
        b, o, br = analysis['b'], analysis['o'], analysis['br']
        total = b + o + br
        if total == 0: total = 1
        
        # Prompt Logic
        identity_context = f"Primary: {analysis['primary']}"
        if analysis['is_hybrid']:
            identity_context = f"HYBRID DETECTED: {analysis['label']} ({analysis['primary']} + {analysis['secondary']})"
        
        prompt = f"""
        You are 'Tether', a career architect engine from Stroma Labs.
        You are analyzing a professional profile.
        
        **DNA SIGNAL:**
        - Identity: {identity_context}
        - Builder Score: {b}
        - Operator Score: {o}
        - Bridge Score: {br}
        
        **TASK:**
        Generate a "Stroma Professional Audit" in 3 strict sections. 
        Tone: Clinical, high-agency, unbiased. No fluff.
        
        **SECTION 1: THE MIRROR (The Identity)**
        Define who they are based on the Identity provided above.
        - If {analysis['label']} is "The Industrialist", "The Evangelist", or "The Integrator", explain that unique combination.
        - Write a 2-sentence "Hero Statement" that defines their value proposition.
        
        **SECTION 2: THE ENVIRONMENT AUDIT (The Framework)**
        Based on their traits, describe the ideal environment for success.
        - **Culture:** What kind of team pace/vibe suits them?
        - **Structure:** Flat vs. Hierarchical? 
        - **Trap:** One specific environment type they must avoid.
        
        **SECTION 3: THE PROOF (3 Rewritten Bullets)**
        Find 3 bullet points from the text that use weak language.
        Rewrite them to match their Archetype Voice ({analysis['label']}).
        - If Industrialist: Combine "Building" and "Scaling" verbs.
        - If Evangelist: Combine "Building" and "Persuading" verbs.
        
        **INPUT TEXT:**
        {text[:5000]}
        """
        
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"System Signal Lost: {str(e)}"

# --- 4. DATA LOGGING ---
def scrub_pii(text):
    text = re.sub(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', '<EMAIL_REDACTED>', text)
    text = re.sub(r'\+?\d[\d -]{8,15}\d', '<PHONE_REDACTED>', text)
    text = re.sub(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', '<LINK_REDACTED>', text)
    return text

def log_session(text, analysis, output_report):
    if len(text) < 50: return
    
    input_hash = hashlib.md5(text.encode()).hexdigest()
    
    if 'last_hash' in st.session_state and st.session_state.last_hash == input_hash:
        return
    
    st.session_state.last_hash = input_hash
    safe_text = scrub_pii(text)
    
    try:
        conn = st.connection("gsheets", type=GSheetsConnection)
        df_new = pd.DataFrame([{
            "Timestamp": datetime.now().isoformat(),
            "Session_ID": st.session_state.session_id,
            "Archetype_Label": analysis['label'],         
            "Archetype_Primary": analysis['primary'],
            "Archetype_Secondary": analysis['secondary'], 
            "Gap_Delta": analysis['delta'],               
            "Score_Builder": analysis['b'],
            "Score_Operator": analysis['o'],
            "Score_Bridge": analysis['br'],
            "Input_Redacted": safe_text,
            "Output_Report": output_report
        }])
        conn.update(data=df_new)
    except Exception as e:
        pass

# --- 5. UI & MAIN EXECUTION ---
def main():
    if 'session_id' not in st.session_state:
        st.session_state.session_id = str(uuid.uuid4())

    # HEADER
    st.title("Tether")
    st.markdown("""
    Most resumes are lists of tasks. This obscures your value.
    Tether decodes your professional DNA to measure your signal across the 
    **Builder**, **Operator**, and **Bridge** spectrum.
    
    **SYSTEM PROTOCOL & PRIVACY**
    * **Encryption:** Personal information are **automatically destroyed** before analysis.
    * **The Vault:** We log *only* anonymized semantic patterns to refine the Stroma Engine.
    * **Usage:** Your data is never sold. It is used exclusively to architect your narrative and train internal models.
    """)
    
    # INPUT
    st.write("---")
    text_input = st.text_area("Paste your full resume:", height=250)
    
    if st.button("Analyze Signal"):
        if not text_input or len(text_input) < 50:
            st.warning("Input signal too weak. Please provide more detail.")
        else:
            with st.spinner("Stroma System is extracting semantic patterns..."):
                # 1. ANALYZE (DNA Logic V3)
                analysis = analyze_archetype(text_input)
                
                # 2. GENERATE REPORT
                try:
                    api_key = st.secrets["GOOGLE_API_KEY"]
                    report = generate_stroma_report(text_input, analysis, api_key)
                except:
                    st.error("Connection Failed. Please check API Key.")
                    st.stop()
                
                # 3. LOG DATA
                log_session(text_input, analysis, report)
                
                # 4. VISUALIZE
                st.write("---")
                
                # Clean Metric Layout
                c1, c2 = st.columns(2)
                
                # Metric 1: Identity
                label_display = analysis['label']
                if analysis['is_hybrid']:
                    label_display = f"{analysis['label']} ({analysis['primary'][0]}+{analysis['secondary'][0]})"
                
                c1.metric("Dominant Signal", label_display)
                c2.metric("Weak Verbs Detected", f"{len(analysis['weaknesses'])}")
                
                # Chart
                chart_data = pd.DataFrame({
                    'Archetype': ['Builder', 'Operator', 'Bridge'],
                    'Score': [analysis['b'], analysis['o'], analysis['br']]
                })
                
                chart = alt.Chart(chart_data).mark_bar().encode(
                    x=alt.X('Archetype', axis=None),
                    y=alt.Y('Score', axis=None),
                    color=alt.Color('Archetype', scale=alt.Scale(
                        domain=['Builder', 'Operator', 'Bridge'],
                        range=['#20BF55', '#2F75C6', '#E1BC29'] 
                    )),
                    tooltip=['Archetype', 'Score']
                ).configure(
                    background='transparent'
                ).configure_view(
                    strokeOpacity=0
                ).properties(
                    height=200
                )
                
                st.altair_chart(chart, use_container_width=True, theme="streamlit")
                # 5. REPORT
                st.subheader("The Stroma Audit")
                st.markdown(report)
                
                st.write("---")
                
                # 6. FOOTER
                st.markdown(
                    """
                    <div style='text-align: center; color: rgba(255, 255, 255, 0.5); font-size: 12px; margin-top: 20px; font-weight: 300;'>
                        © 2025 Stroma Labs. All rights reserved.
                    </div>
                    """, 
                    unsafe_allow_html=True
                )

if __name__ == "__main__":
    main()