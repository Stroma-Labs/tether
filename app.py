import streamlit as st
import pandas as pd
import spacy
import os
import sys
import re
import google.generativeai as genai

# --- 1. THE LEADER'S STUDIO (CSS) ---
st.set_page_config(page_title="Tether", layout="centered")

st.markdown("""
    <style>
    /* Global Reset */
    .stApp {
        background-color: #0E1117; /* Deepest Charcoal */
        color: #F5F5F5;
        font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif;
    }
    
    /* Typography */
    h1 { color: #FFFFFF !important; font-weight: 700; letter-spacing: -1.5px; font-size: 2.8rem; margin-bottom: 10px; }
    h2, h3 { color: #E0E0E0 !important; font-weight: 600; }
    p, li { color: #CCCCCC !important; line-height: 1.6; font-size: 1.05rem; }
    strong { color: #FFFFFF !important; font-weight: 700; }
    
    /* The Manifesto Box */
    .manifesto {
        margin-bottom: 30px;
        padding-bottom: 20px;
        border-bottom: 1px solid #333;
    }
    .manifesto-text {
        font-size: 1.1rem;
        color: #AAAAAA;
        font-weight: 300;
        line-height: 1.6;
    }
    .manifesto-highlight {
        color: #FFFFFF;
        font-weight: 500;
    }

    /* Input Area */
    .stTextArea textarea {
        background-color: #161B22 !important;
        border: 1px solid #333 !important;
        color: #FFFFFF !important;
        font-family: 'Consolas', monospace;
        font-size: 15px;
        border-radius: 8px;
    }
    .stTextArea textarea:focus {
        border: 1px solid #777 !important;
    }

    /* Metrics Strip */
    .metric-strip {
        background-color: #161B22;
        border-radius: 12px;
        padding: 25px;
        margin: 20px 0;
        display: flex;
        align-items: center;
        justify-content: space-between;
        border: 1px solid #222;
    }
    .big-score {
        font-size: 3.5rem;
        font-weight: 700;
        color: #FFFFFF;
        line-height: 1;
        letter-spacing: -2px;
    }
    .score-label {
        text-transform: uppercase;
        letter-spacing: 1.5px;
        font-size: 0.75rem;
        color: #666;
        margin-top: 5px;
        font-weight: 600;
    }

    /* Passive Tags */
    .passive-pill {
        display: inline-block;
        padding: 6px 12px;
        margin: 0 4px 4px 0;
        background-color: #331111;
        color: #FF5555;
        border: 1px solid #662222;
        border-radius: 6px;
        font-size: 0.85rem;
        font-weight: 500;
    }

    /* The Narrative Container */
    .story-container {
        font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif;
        font-size: 1.1rem;
        line-height: 1.7;
        color: #DDDDDD;
        background-color: #121212;
        padding: 0px;
        margin-top: 30px;
    }
    
    /* Styled Headers for Generated Content */
    .story-header {
        color: #FFFFFF;
        font-size: 1.2rem;
        font-weight: 700;
        letter-spacing: 1px;
        text-transform: uppercase;
        margin-top: 40px;
        margin-bottom: 20px;
        padding-bottom: 10px;
        border-bottom: 1px solid #333;
    }

    /* BUTTON STYLING */
    div.stButton > button {
        background-color: #222222;
        color: #FFFFFF;
        border: 1px solid #444;
        border-radius: 8px;
        font-weight: 600;
        padding: 12px 24px;
        font-size: 1rem;
        transition: all 0.2s;
    }
    div.stButton > button:hover {
        background-color: #333333;
        border-color: #666;
        color: #FFFFFF;
    }
    div.stButton > button:active {
        transform: scale(0.98);
    }
    
    /* Hide Streamlit Chrome */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    </style>
    """, unsafe_allow_html=True)

# --- 2. INTELLIGENCE LOADER ---
@st.cache_resource
def load_nlp():
    # The model is now installed via requirements.txt
    return spacy.load("en_core_web_sm")
    except:
        import subprocess
        subprocess.check_call([sys.executable, "-m", "spacy", "download", "en_core_web_sm"])
        return spacy.load("en_core_web_sm")

@st.cache_data
def load_db():
    base_path = "data"
    files = {
        "Builder":   f"data/Lexicon_Matrix_Builder_v1.csv",
        "Operator":  f"data/Lexicon_Matrix_Operator_v1.csv",
        "Bridge":    f"data/Lexicon_Matrix_Bridge_v1.csv",
        "Universal": f"data/Lexicon_Matrix_Universal_v1.csv",
        "Weakness":  f"data/Lexicon_Matrix_Weakness_v1.csv"
    }
    
    db = {}
    for role, filename in files.items():
        if os.path.exists(filename):
            try:
                df = pd.read_csv(filename)
                df.columns = [c.lower().strip() for c in df.columns]
                
                pair_col = next((c for c in df.columns if "pair" in c), None)
                tier_col = next((c for c in df.columns if "tier" in c), None)
                
                if pair_col:
                    for _, row in df.iterrows():
                        raw_pair = str(row[pair_col]).lower().strip()
                        parts = raw_pair.split()
                        
                        # GATEKEEPING: Only allow single words if Weakness
                        if len(parts) == 1 and role != "Weakness":
                            continue 
                            
                        if len(parts) >= 1: 
                            trigger = parts[0]
                            target = parts[1] if len(parts) > 1 else trigger 
                            
                            if role == "Weakness":
                                base_score = -50
                                tier = 3
                            else:
                                tier = int(row[tier_col]) if (tier_col and pd.notnull(row[tier_col])) else 2
                                base_score = 100 if tier == 1 else (50 if tier == 2 else 10)

                            db[raw_pair] = {
                                "Trigger": trigger,
                                "Target": target,
                                "Role": role,
                                "Score": base_score,
                                "Pair": raw_pair.upper()
                            }
            except: pass
    return db

nlp = load_nlp()
db = load_db()

# --- 3. ANALYSIS ENGINE (With Hard Filter) ---
def analyze_text(text):
    doc = nlp(text.lower())
    hits = []
    weaknesses_found = []
    metric_pattern = re.compile(r'(\$|\%|\d+[kmbt]?)')
    
    # HARD FILTER: Explicitly ignore these words even if they appear in Weakness CSV
    FALSE_POSITIVES = [
        "coordinate", "execute", "work", "lead", "manage", "drive", 
        "create", "build", "design", "develop", "in", "and", "the", "to", "for"
    ]
    
    for token in doc:
        word = token.lemma_
        candidates = [k for k, v in db.items() if v['Trigger'] == word]
        if candidates:
            start = token.i
            end = min(token.i + 8, len(doc))
            neighborhood_lemmas = [t.lemma_ for t in doc[start:end]]
            neighborhood_text = " ".join([t.text for t in doc[start:end]])
            
            for pair_key in candidates:
                signal = db[pair_key].copy()
                
                # Logic: Weakness
                if signal['Role'] == "Weakness":
                    trigger_word = signal['Trigger'].lower()
                    # Check the Hard Filter
                    if trigger_word not in FALSE_POSITIVES:
                        weaknesses_found.append(signal['Trigger'].upper())
                
                # Logic: Strengths
                elif db[pair_key]['Target'] in neighborhood_lemmas:
                    if signal['Score'] > 0:
                        if metric_pattern.search(neighborhood_text):
                            signal['Score'] = int(signal['Score'] * 1.5)
                    hits.append(signal)

    return hits, weaknesses_found

# --- 4. THE SOVEREIGN ARCHITECT ---
def rewrite_resume(text, hits_df, weaknesses):
    try:
        api_key = st.secrets["GOOGLE_API_KEY"]
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-2.0-flash') 
    except:
        return "Error: System Connection Failed. Please check API Key."

    # DNA Calculation
    if not hits_df.empty:
        signal_df = hits_df[hits_df['Role'] != 'Weakness']
        if not signal_df.empty:
            role_counts = signal_df['Role'].value_counts(normalize=True)
            builder_pct = int(role_counts.get('Builder', 0) * 100)
            operator_pct = int(role_counts.get('Operator', 0) * 100)
            bridge_pct = int(role_counts.get('Bridge', 0) * 100)
            universal_pct = int(role_counts.get('Universal', 0) * 100)
            primary_role = role_counts.idxmax()
        else:
            builder_pct, operator_pct, bridge_pct, universal_pct = 0, 0, 0, 0
            primary_role = "Generalist"
    else:
        primary_role = "Generalist"
        builder_pct, operator_pct, bridge_pct, universal_pct = 0, 0, 0, 0

    identity_matrix = f"""
    WORK STYLE DATA:
    - Dominant Style: {primary_role}
    - Product/Creation (Builder): {builder_pct}%
    - Execution/Process (Operator): {operator_pct}%
    - People/Persuasion (Bridge): {bridge_pct}%
    - Foundation/Universal: {universal_pct}%
    """

    system_prompt = f"""
    ROLE: Elite Career Strategist.
    TONE: Editorial, clean, inspiring, professional. NO JARGON.
    
    INPUT DATA:
    {identity_matrix}
    
    FRAMEWORK (3-P Logic):
    - Product Focus = Creating Value, Innovation.
    - Project Focus = Reliability, Scale, Process.
    - People Focus = Negotiation, Buy-in, Leadership.

    TASK:
    1. EXTRACT candidate name (if any).
    2. TRANSFORM profile into a "Professional Story".
    
    OUTPUT INSTRUCTIONS:
    - USE STRICT MARKDOWN.
    - HEADERS MUST BE ALL CAPS: "### PART 1: THE PROFESSIONAL STORY" and "### PART 2: THE POTENTIAL REPORT".
    - Do not use "Title Case" for headers.

    ### PART 1: THE PROFESSIONAL STORY
    (Rewrite the roles. Bold the Titles. Use *Italics* for the 2-sentence Strategic Context under each title. Use clean, high-impact bullet points.)

    ### PART 2: THE POTENTIAL REPORT
    (A personal letter to the candidate. 
    - Paragraph 1: The Alignment Check (Title vs Data). 
    - Paragraph 2: The 3-P Analysis (Their unique mix).
    - Paragraph 3: The Pivot (Specific advice).)

    INPUT TEXT:
    {text}
    """
    
    try:
        response = model.generate_content(system_prompt)
        return response.text
    except Exception as e:
        return f"GenAI Error: {e}"

# --- 5. THE STUDIO INTERFACE ---

# Header & Manifesto
st.markdown("<h1>Tether.</h1>", unsafe_allow_html=True)
st.markdown("""
<div class='manifesto'>
    <div class='manifesto-text'>
        Most resumes are lists of tasks. This is a friction point that obscures your value.<br>
        Tether decodes your professional DNA to reveal your <span class='manifesto-highlight'>Impact Archetype</span>: 
        <b>Builder</b> (Product), <b>Operator</b> (Project), or <b>Bridge</b> (People).
        <br><br>
        We identify your core strengths, remove passive language, and architect a narrative that reflects your true impact value.
    </div>
</div>
""", unsafe_allow_html=True)

# Input Logic
if st.session_state.get('analyzed'):
    if st.button("←  Analyze New Profile", type="primary"):
        st.session_state.clear()
        st.rerun()
else:
    target_text = st.text_area("input_hidden", label_visibility="collapsed", height=250, placeholder="Paste your full resume or bullet points here...")
    
    if st.button("Analyze Profile", type="primary", use_container_width=True):
        if target_text:
            hits, weaknesses = analyze_text(target_text)
            st.session_state['hits'] = hits
            st.session_state['weaknesses'] = weaknesses
            st.session_state['text'] = target_text
            st.session_state['analyzed'] = True
            st.rerun()

# --- 6. THE MIRROR (Results) ---
if st.session_state.get('analyzed'):
    hits = st.session_state['hits']
    weaknesses = st.session_state['weaknesses']
    text_len = len(st.session_state['text'])
    
    # 6A. DATA PROCESSING
    total_score = 0
    df_hits = pd.DataFrame()
    if hits:
        df_hits = pd.DataFrame(hits)
        total_score = df_hits['Score'].sum()
        st.session_state['hits_df'] = df_hits
    
    # 6B. METRICS DASHBOARD
    st.markdown(f"""
    <div class='metric-strip'>
        <div>
            <div class='big-score'>{total_score}</div>
            <div class='score-label'>Impact Score</div>
        </div>
        <div style='text-align: right;'>
            <div class='score-label' style='margin-bottom: 8px;'>Passive Language</div>
            {''.join([f"<span class='passive-pill'>{w.lower()}</span>" for w in list(set(weaknesses))[:8]]) if weaknesses else "<span style='color:#666;'>0 detected</span>"}
        </div>
    </div>
    """, unsafe_allow_html=True)

    # 6C. WARNING LOGIC
    if text_len < 100:
        st.info("⚠️ **Low Data Volume:** For a complete Archetype Profile, please paste a full resume.")

    # 6D. CHART
    if not df_hits.empty:
        signal_df = df_hits[df_hits['Role'] != 'Weakness']
        if not signal_df.empty:
            role_counts = signal_df['Role'].value_counts()
            c1, c2, c3 = st.columns([1, 4, 1])
            with c2:
                st.caption("ARCHETYPE DNA")
                st.bar_chart(role_counts, height=150)

    # 6E. ELEVATION BUTTON
    st.markdown("<div style='height: 20px;'></div>", unsafe_allow_html=True)
    
    if st.button("Reveal Impact Narrative", type="secondary", use_container_width=True):
        with st.spinner("Architecting narrative..."):
            raw_text = rewrite_resume(
                st.session_state['text'], 
                st.session_state.get('hits_df', pd.DataFrame()), 
                st.session_state.get('weaknesses', [])
            )
            
            # FORMATTING FIX: Clean up Markdown Headers for Consistency
            clean_text = raw_text.replace("### PART 1", "<div class='story-header'>PART 1").replace("### PART 2", "<div class='story-header'>PART 2")
            clean_text = clean_text.replace("THE PROFESSIONAL STORY", "THE PROFESSIONAL STORY</div>").replace("THE POTENTIAL REPORT", "THE POTENTIAL REPORT</div>")
            
            # If AI uses different markdown, just ensure styling works
            clean_text = re.sub(r'###\s*(.*)', r"<div class='story-header'>\1</div>", raw_text)

            st.markdown(f"<div class='story-container'>{clean_text}</div>", unsafe_allow_html=True)

# --- 7. FOOTER ---
st.markdown("<div style='height: 50px;'></div>", unsafe_allow_html=True)