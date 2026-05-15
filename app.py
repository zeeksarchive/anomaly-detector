import streamlit as st
import pandas as pd
import anthropic
import yaml
from yaml.loader import SafeLoader
import os
import bcrypt
import stripe

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
.upgrade-box {background: linear-gradient(135deg, #0f3460, #533483); border-radius: 16px; padding: 2rem; text-align: center; border: 1px solid #7c3aed; margin: 1rem 0;}
.upgrade-box h3 {color: white; font-size: 1.8rem; margin-bottom: 0.5rem;}
.upgrade-box p {color: #c4b5fd; font-size: 1.1rem;}
.feature-grid {display: grid; grid-template-columns: repeat(3, 1fr); gap: 1rem; margin: 2rem 0;}
.feature-card {background: #16213e; border-radius: 12px; padding: 1.5rem; border: 1px solid #0f3460; text-align: center;}
.feature-card h4 {color: white; margin-bottom: 0.5rem;}
.feature-card p {color: #a0aec0; font-size: 0.9rem;}
.pricing-box {background: #16213e; border-radius: 16px; padding: 2rem; text-align: center; border: 1px solid #0f3460; margin: 2rem 0;}
.pricing-box h3 {color: white; font-size: 1.5rem; margin-bottom: 0.5rem;}
.pricing-box .price {font-size: 3rem; color: #7c3aed; font-weight: bold;}
.pricing-box .price span {font-size: 1rem; color: #a0aec0;}
.pricing-box ul {list-style: none; padding: 0; color: #a0aec0; margin: 1rem 0;}
.pricing-box ul li {padding: 0.3rem 0;}
.stButton > button {background: linear-gradient(135deg, #7c3aed, #4f46e5) !important; color: white !important; border: none !important; border-radius: 8px !important; font-weight: bold !important; font-size: 1rem !important;}
.stButton > button:hover {background: linear-gradient(135deg, #6d28d9, #4338ca) !important; color: white !important;}
[data-testid="stFileUploader"] {border: 2px dashed #7c3aed !important; border-radius: 12px !important; padding: 1rem !important;}
</style>""", unsafe_allow_html=True)

stripe.api_key = st.secrets["STRIPE_SECRET_KEY"]

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

def save_config():
    with open(CONFIG_FILE, "w") as f:
        yaml.dump(config, f)

def get_user(username):
    return config["users"].get(username, {})

def is_paid(username):
    return get_user(username).get("paid", False)

def get_uses(username):
    return get_user(username).get("uses", 0)

def increment_uses(username):
    config["users"][username]["uses"] = get_uses(username) + 1
    save_config()

FREE_LIMIT = 5

if st.session_state.logged_in:
    username = st.session_state.username
    uses = get_uses(username)
    paid = is_paid(username)

    st.sidebar.markdown("## 🔍 Anomaly Detector")
    st.sidebar.markdown("---")
    st.sidebar.write(f"Welcome, **{st.session_state.name}**!")
    if not paid:
        st.sidebar.info(f"Free uses: {uses}/{FREE_LIMIT}")
    else:
        st.sidebar.success("⭐ Pro Member")
    if st.sidebar.button("Logout", use_container_width=True):
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

    if not paid and uses >= FREE_LIMIT:
        st.markdown("""<div class="upgrade-box">
<h3>🔓 Unlock Unlimited Access</h3>
<p>You've used all 5 free analyses. Upgrade to Pro for unlimited anomaly detection.</p>
</div>""", unsafe_allow_html=True)
        col1, col2, col3 = st.columns([1,2,1])
        with col2:
            if st.button("✨ Upgrade to Pro — $9/month", use_container_width=True):
                try:
                    session = stripe.checkout.Session.create(
                        payment_method_types=["card"],
                        line_items=[{"price": st.secrets["STRIPE_PRICE_ID"], "quantity": 1}],
                        mode="subscription",
                        success_url="https://anomaly-detector-ai.streamlit.app/?paid=true&user=" + username,
                        cancel_url="https://anomaly-detector-ai.streamlit.app/",
                        client_reference_id=username,
                    )
                    st.markdown(f'<meta http-equiv="refresh" content="0; url={session.url}">', unsafe_allow_html=True)
                    st.markdown(f"[Click here if not redirected]({session.url})")
                except Exception as e:
                    st.error(f"Error: {str(e)}")
    else:
        params = st.query_params
        if params.get("paid") == "true" and params.get("user") == username:
            config["users"][username]["paid"] = True
            save_config()
            st.success("🎉 Payment successful! You now have unlimited access.")
            st.query_params.clear()
            st.rerun()

        uploaded_file = st.file_uploader("📂 Upload a CSV or Excel file", type=["csv", "xlsx"])

        if uploaded_file:
            if uploaded_file.name.endswith(".csv"):
                df = pd.read_csv(uploaded_file)
            else:
                df = pd.read_excel(uploaded_file)

            st.write("### Your Data", df)

            if st.button("🔍 Detect Anomalies", use_container_width=True):
                if not paid and uses >= FREE_LIMIT:
                    st.error("You've reached the free limit. Please upgrade.")
                else:
                    with st.spinner("Analyzing your data for anomalies..."):
                        increment_uses(username)
                        client = anthropic.Anthropic(api_key=st.secrets["ANTHROPIC_API_KEY"])
                        data_summary = df.describe().to_string()
                        data_sample = df.head(50).to_string()
                        message = client.messages.create(
                            model="claude-sonnet-4-6",
                            max_tokens=1500,
                            messages=[{"role": "user", "content": f"You are a data analyst. Analyze this data for anomalies.\n\nSummary:\n{data_summary}\n\nSample:\n{data_sample}\n\nFind unusual spikes, outliers, data quality issues. Be specific about row numbers. Write in plain English."}],
                        )
                    st.markdown("### 🧠 Anomaly Report")
                    st.markdown(message.content[0].text)
                    if not paid:
                        remaining = FREE_LIMIT - get_uses(username)
                        if remaining > 0:
                            st.info(f"You have {remaining} free {'analysis' if remaining == 1 else 'analyses'} remaining.")
                        else:
                            st.warning("That was your last free analysis! Upgrade to Pro for unlimited access.")

else:
    st.markdown("""<div class="hero">
<h1>🔍 Anomaly Detector</h1>
<p>AI-powered data analysis that instantly finds outliers, suspicious patterns, and data quality issues in any CSV or Excel file.</p>
</div>""", unsafe_allow_html=True)

    st.markdown("""<div class="feature-grid">
<div class="feature-card">
<h4>⚡ Instant Analysis</h4>
<p>Upload your file and get a full anomaly report in seconds.</p>
</div>
<div class="feature-card">
<h4>📊 Any Data Format</h4>
<p>Works with CSV and Excel files of any size or structure.</p>
</div>
<div class="feature-card">
<h4>🎯 Plain English Reports</h4>
<p>No jargon. Clear, specific findings with exact row numbers.</p>
</div>
</div>""", unsafe_allow_html=True)

    st.markdown("""<div class="pricing-box">
<h3>Simple Pricing</h3>
<div class="price">$9<span>/month</span></div>
<ul>
<li>5 free analyses to start</li>
<li>Unlimited analyses with Pro</li>
<li>CSV & Excel support</li>
<li>Cancel anytime</li>
</ul>
</div>""", unsafe_allow_html=True)

    st.markdown("---")

    col1, col2 = st.columns(2)
    with col1:
        if st.button("Login", use_container_width=True, key="tab_login"):
            st.session_state.auth_mode = "Login"
    with col2:
        if st.button("Sign Up", use_container_width=True, key="tab_signup"):
            st.session_state.auth_mode = "Sign Up"

    mode = st.session_state.auth_mode

    if mode == "Login":
        st.subheader("Login")
        username = st.text_input("Username", key="login_user")
        password = st.text_input("Password", type="password", key="login_pass")
        if st.button("Login", use_container_width=True, key="login_submit"):
            user = config["users"].get(username)
            if user and bcrypt.checkpw(password.encode(), user["password"].encode()):
                st.session_state.logged_in = True
                st.session_state.username = username
                st.session_state.name = user.get("name", username)
                st.rerun()
            else:
                st.error("Invalid username or password.")

    else:
        st.subheader("Create Account")
        name = st.text_input("Full Name", key="signup_name")
        username = st.text_input("Username", key="signup_user")
        password = st.text_input("Password", type="password", key="signup_pass")
        if st.button("Create Account", use_container_width=True, key="signup_submit"):
            if username in config["users"]:
                st.error("Username already exists.")
            elif not username or not password or not name:
                st.error("Please fill in all fields.")
            else:
                hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
                config["users"][username] = {"name": name, "password": hashed, "uses": 0, "paid": False}
                save_config()
                st.session_state.logged_in = True
                st.session_state.username = username
                st.session_state.name = name
                st.rerun()
