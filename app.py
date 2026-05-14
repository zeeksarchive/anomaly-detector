import streamlit as st
import pandas as pd
import anthropic
import yaml
from yaml.loader import SafeLoader
import os
import bcrypt

st.set_page_config(page_title="Anomaly Detector", page_icon="🔍", layout="wide")

st.markdown("""<style>
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
header {visibility: hidden;}
[data-testid="stToolbar"] {visibility: hidden;}
.viewerBadge_container__r5tak {display: none;}
#stDecoration {display: none;}
.hero {background: linear-gradient(135deg, #1a1a2e, #16213e); padding: 3rem 2rem; border-radius: 16px; margin-bottom: 2rem; text-align: center; border: 1px solid #0f3460;}
.hero h1 {font-size: 3rem; color: white; margin-bottom: 0.5rem;}
.hero p {font-size: 1.2rem; color: #a0aec0; max-width: 600px; margin: 0 auto 1rem;}
div[data-testid="stRadio"] > div {display: flex; gap: 0; margin-bottom: 1.5rem; border-radius: 8px; overflow: hidden; border: 1px solid #0f3460;}
div[data-testid="stRadio"] label {flex: 1; text-align: center; padding: 0.6rem 1.5rem; cursor: pointer; color: white; background: #16213e; border: none; margin: 0;}
div[data-testid="stRadio"] label:has(input:checked) {background: #0f3460; font-weight: bold;}
div[data-testid="stRadio"] input {display: none !important;}
div[data-testid="stRadio"] label {white-space: nowrap !important;}
</style>""", unsafe_allow_html=True)

CONFIG_FILE = os.path.join(os.path.dirname(__file__), "config.yaml")

if not os.path.exists(CONFIG_FILE):
    with open(CONFIG_FILE, "w") as f:
        yaml.dump({"users": {}}, f)

with open(CONFIG_FILE) as f:
    config = yaml.load(f, Loader=SafeLoader) or {"users": {}}

if "users" not in config:
    config["users"] = {}

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.username = ""
    st.session_state.name = ""

if "auth_mode" not in st.session_state:
    st.session_state.auth_mode = "Login"

if st.session_state.logged_in:
    st.sidebar.write(f"Welcome, {st.session_state.name}!")
    if st.sidebar.button("Logout"):
        st.session_state.logged_in = False
        st.session_state.username = ""
        st.session_state.name = ""
        st.rerun()

    st.markdown("""<div class="hero">
<h1>🔍 Anomaly Detector</h1>
<p>Upload any CSV or Excel file and AI instantly finds outliers, suspicious patterns, and data quality issues.</p>
</div>""", unsafe_allow_html=True)

    with st.expander("👀 See a sample report before uploading"):
        st.markdown("""**Sample Report**

**1. Unusual spike in Row 47:** Revenue jumped to $94,000 on March 3rd, roughly 8x the daily average.

**2. Missing values in Region column:** 23 out of 500 rows have no region assigned.

**3. Negative quantities in rows 112-115:** Four orders show negative item counts.""")

    st.markdown("---")
    uploaded_file = st.file_uploader("Upload a CSV or Excel file", type=["csv", "xlsx"])

    if uploaded_file:
        if uploaded_file.name.endswith(".csv"):
            df = pd.read_csv(uploaded_file)
        else:
            df = pd.read_excel(uploaded_file)

        st.write("### Your Data", df)

        if st.button("🔍 Detect Anomalies"):
            with st.spinner("Analyzing your data for anomalies..."):
                client = anthropic.Anthropic(api_key=st.secrets["ANTHROPIC_API_KEY"])
                data_summary = df.describe().to_string()
                data_sample = df.head(50).to_string()
                message = client.messages.create(
                    model="claude-sonnet-4-6",
                    max_tokens=1500,
                    messages=[{"role": "user", "content": f"You are a data analyst. Analyze this data for anomalies.\n\nSummary:\n{data_summary}\n\nSample:\n{data_sample}\n\nFind unusual spikes, outliers, data quality issues. Be specific about row numbers. Write in plain English."}],
                )
                st.write("### 🔍 Anomaly Report")
                st.write(message.content[0].text)

else:
    st.markdown("""<div class="hero">
<h1>🔍 Anomaly Detector</h1>
<p>AI-powered data analysis. Upload any spreadsheet and instantly find what doesn't look right.</p>
</div>""", unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 1.2, 1])
    with col2:
        mode = st.radio("", ["Login", "Sign Up"], horizontal=True, label_visibility="collapsed", index=0 if st.session_state.auth_mode == "Login" else 1, key="auth_radio")
        st.session_state.auth_mode = mode

        if mode == "Login":
            st.markdown("### Welcome back")
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            if st.button("Login", use_container_width=True):
                users = config.get("users", {})
                if username in users:
                    stored = users[username]["password"].encode()
                    if bcrypt.checkpw(password.encode(), stored):
                        with st.spinner("Logging in..."):
                            st.session_state.logged_in = True
                            st.session_state.username = username
                            st.session_state.name = users[username]["name"]
                        st.rerun()
                    else:
                        st.error("Incorrect password")
                else:
                    st.error("Username not found")

        else:
            st.markdown("### Create an account")
            new_name = st.text_input("Full Name")
            new_username = st.text_input("Username")
            new_password = st.text_input("Password", type="password")
            new_password2 = st.text_input("Confirm Password", type="password")
            if st.button("Sign Up", use_container_width=True):
                if not new_name or not new_username or not new_password:
                    st.error("Please fill in all fields")
                elif new_password != new_password2:
                    st.error("Passwords do not match")
                elif new_username in config["users"]:
                    st.error("Username already taken")
                else:
                    hashed = bcrypt.hashpw(new_password.encode(), bcrypt.gensalt()).decode()
                    config["users"][new_username] = {"name": new_name, "password": hashed}
                    with open(CONFIG_FILE, "w") as f:
                        yaml.dump(config, f)
                    st.success("Account created! Redirecting to login...")
                    st.session_state.auth_mode = "Login"
                    st.rerun()
