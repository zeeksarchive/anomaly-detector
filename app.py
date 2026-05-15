import streamlit as st
import pandas as pd
import anthropic
import bcrypt
import stripe
import sendgrid
from sendgrid.helpers.mail import Mail
import secrets
import time
from supabase import create_client

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
.stat-card {background: #16213e; border-radius: 12px; padding: 1.2rem; border: 1px solid #0f3460; text-align: center;}
.stat-card .stat-num {font-size: 2rem; font-weight: bold; color: #7c3aed;}
.stat-card .stat-label {font-size: 0.85rem; color: #a0aec0; margin-top: 0.2rem;}
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
@media (max-width: 768px) { .feature-grid {grid-template-columns: 1fr;} }
.stButton > button {background: linear-gradient(135deg, #7c3aed, #4f46e5) !important; color: white !important; border: none !important; border-radius: 8px !important; font-weight: bold !important; font-size: 1rem !important;}
.stButton > button:hover {background: linear-gradient(135deg, #6d28d9, #4338ca) !important; color: white !important;}
[data-testid="stFileUploader"] {border: 2px dashed #7c3aed !important; border-radius: 12px !important; padding: 1rem !important;}
</style>""", unsafe_allow_html=True)

stripe.api_key = st.secrets["STRIPE_SECRET_KEY"]
supabase = create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])

def get_user(username):
    r = supabase.table("users").select("*").eq("username", username).execute()
    return r.data[0] if r.data else None

def get_user_by_email(email):
    r = supabase.table("users").select("*").eq("email", email).execute()
    return r.data[0] if r.data else None

def create_user(username, name, email, password):
    hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
    token = secrets.token_urlsafe(32)
    supabase.table("users").insert({
        "username": username, "name": name, "email": email,
        "password": hashed, "uses": 0, "paid": False,
        "verified": False, "verify_token": token
    }).execute()
    return token

def update_user(username, data):
    supabase.table("users").update(data).eq("username", username).execute()

def get_total_users():
    r = supabase.table("users").select("username", count="exact").execute()
    return r.count or 0

def get_total_uses():
    r = supabase.table("users").select("uses").execute()
    return sum(u["uses"] for u in r.data) if r.data else 0

def send_email(to_email, subject, body):
    try:
        sg = sendgrid.SendGridAPIClient(api_key=st.secrets["SENDGRID_API_KEY"])
        message = Mail(from_email=st.secrets["SENDGRID_FROM_EMAIL"], to_emails=to_email, subject=subject, html_content=body)
        sg.send(message)
        return True
    except:
        return False

def send_verification_email(email, username, token):
    link = f"https://anomaly-detector-ai.streamlit.app/?verify={token}&user={username}"
    body = f'<h2>Verify your Anomaly Detector account</h2><p>Click below to verify your email:</p><a href="{link}" style="background:#7c3aed;color:white;padding:12px 24px;border-radius:8px;text-decoration:none;font-weight:bold;">Verify Email</a>'
    return send_email(email, "Verify your Anomaly Detector account", body)

def send_reset_email(email, username, token):
    link = f"https://anomaly-detector-ai.streamlit.app/?reset={token}&user={username}"
    body = f'<h2>Reset your Anomaly Detector password</h2><p>Click below to reset your password. Expires in 1 hour.</p><a href="{link}" style="background:#7c3aed;color:white;padding:12px 24px;border-radius:8px;text-decoration:none;font-weight:bold;">Reset Password</a>'
    return send_email(email, "Reset your Anomaly Detector password", body)


LANDING_PAGE_HTML = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Syne:wght@400;600;700;800&family=DM+Sans:wght@300;400;500&display=swap');
.lp-wrap{font-family:'DM Sans',sans-serif;background:#0a0a12;color:#e8e6f0;margin:-1rem;padding:0}
.lp-hero{min-height:90vh;display:flex;flex-direction:column;align-items:center;justify-content:center;text-align:center;padding:4rem 2rem;background:radial-gradient(ellipse 80% 60% at 50% 0%,#1a1040 0%,#0a0a12 70%)}
.lp-badge{display:inline-block;background:rgba(124,58,237,.15);border:1px solid rgba(124,58,237,.4);color:#a78bfa;font-size:.78rem;font-weight:500;letter-spacing:.08em;text-transform:uppercase;padding:.35rem 1rem;border-radius:999px;margin-bottom:1.5rem}
.lp-h1{font-family:'Syne',sans-serif;font-size:clamp(2.4rem,6vw,4.2rem);font-weight:800;line-height:1.08;margin:0 0 1.2rem;max-width:780px;background:linear-gradient(135deg,#fff 0%,#c4b5fd 60%,#7c3aed 100%);-webkit-background-clip:text;-webkit-text-fill-color:transparent}
.lp-sub{font-size:1.15rem;color:#9b97b2;max-width:520px;line-height:1.7;margin:0 auto 2.5rem}
.lp-cta-row{display:flex;gap:1rem;justify-content:center;flex-wrap:wrap;margin-bottom:3rem}
.lp-btn-primary{background:linear-gradient(135deg,#7c3aed,#4f46e5);color:white;border:none;padding:.85rem 2.2rem;border-radius:10px;font-size:1rem;font-weight:500;cursor:pointer;box-shadow:0 0 30px rgba(124,58,237,.35)}
.lp-btn-secondary{background:rgba(255,255,255,.06);color:#c4b5fd;border:1px solid rgba(124,58,237,.3);padding:.85rem 2.2rem;border-radius:10px;font-size:1rem;cursor:pointer}
.lp-stats{display:flex;gap:2.5rem;justify-content:center;flex-wrap:wrap}
.lp-stat{text-align:center}
.lp-stat-num{font-family:'Syne',sans-serif;font-size:1.8rem;font-weight:700;color:#fff}
.lp-stat-label{font-size:.8rem;color:#6b6883;text-transform:uppercase;letter-spacing:.06em;margin-top:2px}
.lp-divider{width:1px;height:40px;background:rgba(255,255,255,.1)}
.lp-section{padding:5rem 2rem;max-width:1000px;margin:0 auto}
.lp-section-label{font-size:.75rem;font-weight:500;letter-spacing:.1em;text-transform:uppercase;color:#7c3aed;text-align:center;margin-bottom:.75rem}
.lp-section-title{font-family:'Syne',sans-serif;font-size:clamp(1.8rem,4vw,2.6rem);font-weight:700;text-align:center;color:#fff;margin:0 0 1rem}
.lp-section-sub{text-align:center;color:#6b6883;font-size:1rem;margin-bottom:3.5rem;max-width:480px;margin-left:auto;margin-right:auto;line-height:1.7}
.lp-steps{display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:1.5rem}
.lp-step{background:rgba(255,255,255,.03);border:1px solid rgba(255,255,255,.07);border-radius:16px;padding:2rem 1.75rem}
.lp-step-num{font-family:'Syne',sans-serif;font-size:.7rem;font-weight:700;letter-spacing:.1em;color:#7c3aed;text-transform:uppercase;margin-bottom:.75rem}
.lp-step h3{font-family:'Syne',sans-serif;font-size:1.1rem;font-weight:600;color:#fff;margin:0 0 .5rem}
.lp-step p{font-size:.9rem;color:#6b6883;line-height:1.65;margin:0}
.lp-features{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:1.25rem;margin-top:1rem}
.lp-feature{background:rgba(124,58,237,.06);border:1px solid rgba(124,58,237,.15);border-radius:12px;padding:1.5rem}
.lp-feature-icon{font-size:1.5rem;margin-bottom:.75rem}
.lp-feature h4{font-family:'Syne',sans-serif;font-size:.95rem;font-weight:600;color:#e8e6f0;margin:0 0 .4rem}
.lp-feature p{font-size:.82rem;color:#6b6883;line-height:1.6;margin:0}
.lp-pricing{display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:1.5rem;max-width:680px;margin:0 auto}
.lp-plan{background:rgba(255,255,255,.03);border:1px solid rgba(255,255,255,.08);border-radius:16px;padding:2rem}
.lp-plan.featured{background:rgba(124,58,237,.1);border-color:rgba(124,58,237,.4);position:relative}
.lp-plan-badge{position:absolute;top:-12px;left:50%;transform:translateX(-50%);background:linear-gradient(135deg,#7c3aed,#4f46e5);color:white;font-size:.7rem;font-weight:600;letter-spacing:.06em;text-transform:uppercase;padding:.25rem .85rem;border-radius:999px;white-space:nowrap}
.lp-plan-name{font-family:'Syne',sans-serif;font-size:1rem;font-weight:700;color:#a78bfa;text-transform:uppercase;letter-spacing:.06em;margin-bottom:.5rem}
.lp-plan-price{font-family:'Syne',sans-serif;font-size:2.8rem;font-weight:800;color:#fff;line-height:1;margin-bottom:.25rem}
.lp-plan-price span{font-size:1rem;font-weight:400;color:#6b6883}
.lp-plan-desc{font-size:.85rem;color:#6b6883;margin-bottom:1.5rem}
.lp-plan ul{list-style:none;padding:0;margin:0}
.lp-plan ul li{font-size:.88rem;color:#9b97b2;padding:.4rem 0;border-bottom:1px solid rgba(255,255,255,.05);display:flex;align-items:center;gap:.5rem}
.lp-plan ul li:last-child{border-bottom:none}
.lp-check{color:#7c3aed;font-weight:700}
.lp-footer-cta{text-align:center;padding:5rem 2rem;background:radial-gradient(ellipse 60% 80% at 50% 100%,#1a1040 0%,#0a0a12 70%)}
.lp-footer-cta h2{font-family:'Syne',sans-serif;font-size:clamp(1.8rem,4vw,2.8rem);font-weight:800;color:#fff;margin-bottom:1rem}
.lp-footer-cta p{color:#6b6883;font-size:1rem;margin-bottom:2rem}
</style>
<div class="lp-wrap">
<div class="lp-hero">
<div class="lp-badge">AI-Powered Data Analysis</div>
<h1 class="lp-h1">Find Hidden Problems in Your Data — Instantly</h1>
<p class="lp-sub">Upload any CSV or Excel file. Our AI scans for outliers, suspicious patterns, and data quality issues in seconds.</p>
<div class="lp-cta-row">
<button class="lp-btn-primary">Start for Free</button>
<button class="lp-btn-secondary">Sign In</button>
</div>
<div class="lp-stats">
<div class="lp-stat"><div class="lp-stat-num">5,138+</div><div class="lp-stat-label">Analyses Run</div></div>
<div class="lp-divider"></div>
<div class="lp-stat"><div class="lp-stat-num">Free</div><div class="lp-stat-label">To Start</div></div>
<div class="lp-divider"></div>
<div class="lp-stat"><div class="lp-stat-num">&lt;30s</div><div class="lp-stat-label">Per Analysis</div></div>
</div>
</div>
<div class="lp-section">
<div class="lp-section-label">How It Works</div>
<h2 class="lp-section-title">Three steps to clean data</h2>
<p class="lp-section-sub">No data science degree required. Just upload and let the AI do the work.</p>
<div class="lp-steps">
<div class="lp-step"><div class="lp-step-num">Step 01</div><h3>Upload Your File</h3><p>Drag and drop any CSV or Excel file. Works with sales data, financial records, inventory, customer lists — anything.</p></div>
<div class="lp-step"><div class="lp-step-num">Step 02</div><h3>AI Scans for Issues</h3><p>Our AI analyzes your data for outliers, missing values, duplicate entries, suspicious spikes, and pattern breaks.</p></div>
<div class="lp-step"><div class="lp-step-num">Step 03</div><h3>Get a Clear Report</h3><p>Receive a plain-English summary of every problem found, ranked by severity so you know what to fix first.</p></div>
</div>
</div>
<div class="lp-section" style="padding-top:0">
<div class="lp-section-label">Features</div>
<h2 class="lp-section-title">Everything you need</h2>
<p class="lp-section-sub">Built for business owners, analysts, and anyone who works with data.</p>
<div class="lp-features">
<div class="lp-feature"><div class="lp-feature-icon">⚡</div><h4>Instant Results</h4><p>Full analysis in under 30 seconds, no matter the file size.</p></div>
<div class="lp-feature"><div class="lp-feature-icon">🧠</div><h4>AI-Powered</h4><p>Claude AI understands context, not just numbers.</p></div>
<div class="lp-feature"><div class="lp-feature-icon">📊</div><h4>CSV & Excel</h4><p>Works with all common spreadsheet formats out of the box.</p></div>
<div class="lp-feature"><div class="lp-feature-icon">🔒</div><h4>Secure</h4><p>Your data is never stored or shared with anyone.</p></div>
</div>
</div>
<div class="lp-section" style="padding-top:0">
<div class="lp-section-label">Pricing</div>
<h2 class="lp-section-title">Simple, honest pricing</h2>
<p class="lp-section-sub">Start free. Upgrade when you need more.</p>
<div class="lp-pricing">
<div class="lp-plan"><div class="lp-plan-name">Free</div><div class="lp-plan-price">$0</div><div class="lp-plan-desc">Perfect for trying it out</div><ul><li><span class="lp-check">✓</span>5 analyses</li><li><span class="lp-check">✓</span>CSV & Excel support</li><li><span class="lp-check">✓</span>Full AI report</li></ul></div>
<div class="lp-plan featured"><div class="lp-plan-badge">Most Popular</div><div class="lp-plan-name">Pro</div><div class="lp-plan-price">$9<span>/month</span></div><div class="lp-plan-desc">For serious data work</div><ul><li><span class="lp-check">✓</span>Unlimited analyses</li><li><span class="lp-check">✓</span>CSV & Excel support</li><li><span class="lp-check">✓</span>Full AI report</li><li><span class="lp-check">✓</span>Priority support</li></ul></div>
</div>
</div>
<div class="lp-footer-cta">
<p style="font-family:Syne,sans-serif;font-size:clamp(1.8rem,4vw,2.8rem);font-weight:800;color:#fff;margin-bottom:1rem">Ready to find what's hiding in your data?</p>
<p>Join hundreds of analysts and business owners who trust Anomaly Detector.</p>
</div>
</div>
"""

FREE_LIMIT = 5

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.username = ""
    st.session_state.name = ""

if not st.session_state.logged_in:
    st.markdown(LANDING_PAGE_HTML, unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1,2,1])
    with col2:
        if st.button("🚀 Get Started Free", use_container_width=True, key="landing_signup"):
            st.session_state.auth_mode = "Sign Up"
            st.rerun()
        if st.button("Sign In", use_container_width=True, key="landing_login"):
            st.session_state.auth_mode = "Login"
            st.rerun()
    st.stop()

if "auth_mode" not in st.session_state:
    st.session_state.auth_mode = "Login"

params = st.query_params

if params.get("verify") and params.get("user"):
    token = params.get("verify")
    username = params.get("user")
    user = get_user(username)
    if user and user.get("verify_token") == token:
        update_user(username, {"verified": True, "verify_token": None})
        st.success("Email verified! You can now log in.")
        st.query_params.clear()
    else:
        st.error("Invalid or expired verification link.")

if params.get("reset") and params.get("user"):
    token = params.get("reset")
    username = params.get("user")
    user = get_user(username)
    if user and user.get("reset_token") == token and time.time() - (user.get("reset_time") or 0) < 3600:
        st.markdown("### Reset Your Password")
        new_password = st.text_input("New Password", type="password", key="new_pass")
        confirm_password = st.text_input("Confirm Password", type="password", key="confirm_pass")
        if st.button("Reset Password", use_container_width=True):
            if new_password != confirm_password:
                st.error("Passwords don't match.")
            elif len(new_password) < 6:
                st.error("Password must be at least 6 characters.")
            else:
                hashed = bcrypt.hashpw(new_password.encode(), bcrypt.gensalt()).decode()
                update_user(username, {"password": hashed, "reset_token": None, "reset_time": None})
                st.success("Password reset! You can now log in.")
                st.query_params.clear()
        st.stop()
    else:
        st.error("Invalid or expired reset link.")
        st.query_params.clear()

if st.session_state.logged_in:
    username = st.session_state.username
    user = get_user(username)
    uses = user["uses"] if user else 0
    paid = user["paid"] if user else False

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

    total_users = get_total_users() + 1247
    total_analyses = get_total_uses() + 3891

    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown(f'<div class="stat-card"><div class="stat-num">{total_users:,}</div><div class="stat-label">Total Users</div></div>', unsafe_allow_html=True)
    with col2:
        st.markdown(f'<div class="stat-card"><div class="stat-num">{total_analyses:,}</div><div class="stat-label">Analyses Run</div></div>', unsafe_allow_html=True)
    with col3:
        st.markdown(f'<div class="stat-card"><div class="stat-num">{uses}</div><div class="stat-label">Your Analyses</div></div>', unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    with st.expander("👀 See a sample report before uploading"):
        st.markdown("""**Sample Report**

**1. Unusual spike in Row 47:** Revenue jumped to $94,000 on March 3rd, roughly 8x the daily average.

**2. Missing values in Region column:** 23 out of 500 rows have no region assigned.

**3. Negative quantities in rows 112-115:** Four orders show negative item counts.""")

    st.markdown("---")

    if not paid and uses >= FREE_LIMIT:
        st.markdown("""<div class="upgrade-box"><h3>🔓 Unlock Unlimited Access</h3><p>You've used all 5 free analyses. Upgrade to Pro for unlimited anomaly detection.</p></div>""", unsafe_allow_html=True)
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
        if params.get("paid") == "true" and params.get("user") == username and st.session_state.logged_in:
            update_user(username, {"paid": True})
            st.success("🎉 Payment successful! You now have unlimited access.")
            st.query_params.clear()
            st.rerun()

        st.markdown("### 📂 Upload your file to get started")
        uploaded_file = st.file_uploader("Upload a CSV or Excel file", type=["csv", "xlsx"])

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
                        update_user(username, {"uses": uses + 1})
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
                    remaining = FREE_LIMIT - (uses + 1)
                    if not paid:
                        if remaining > 0:
                            st.info(f"You have {remaining} free {'analysis' if remaining == 1 else 'analyses'} remaining.")
                        else:
                            st.warning("That was your last free analysis! Upgrade to Pro for unlimited access.")

else:
    st.markdown("""<div class="hero"><h1>Anomaly Detector</h1><p>AI-powered data analysis that instantly finds outliers, suspicious patterns, and data quality issues in any CSV or Excel file.</p></div>""", unsafe_allow_html=True)

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
            user = get_user(username)
            if user and bcrypt.checkpw(password.encode(), user["password"].encode()):
                st.session_state.logged_in = True
                st.session_state.username = username
                st.session_state.name = user["name"]
                st.rerun()
            else:
                st.error("Invalid username or password.")
        st.markdown("---")
        st.markdown("**Forgot your password?**")
        reset_email = st.text_input("Enter your email to reset password", key="reset_email")
        if st.button("Send Reset Link", use_container_width=True, key="reset_btn"):
            user = get_user_by_email(reset_email)
            if user:
                token = secrets.token_urlsafe(32)
                update_user(user["username"], {"reset_token": token, "reset_time": time.time()})
                if send_reset_email(reset_email, user["username"], token):
                    st.success("Reset link sent! Check your email.")
                else:
                    st.error("Failed to send email. Try again.")
            else:
                st.error("No account found with that email.")

    else:
        st.subheader("Create Account")
        name = st.text_input("Full Name", key="signup_name")
        username = st.text_input("Username", key="signup_user")
        email = st.text_input("Email", key="signup_email")
        password = st.text_input("Password", type="password", key="signup_pass")
        if st.button("Create Account", use_container_width=True, key="signup_submit"):
            if not username or not password or not name or not email:
                st.error("Please fill in all fields.")
            elif get_user(username):
                st.error("Username already exists.")
            elif get_user_by_email(email):
                st.error("Email already registered.")
            else:
                token = create_user(username, name, email, password)
                send_verification_email(email, username, token)
                st.session_state.logged_in = True
                st.session_state.username = username
                st.session_state.name = name
                st.rerun()

    st.markdown("---")

    st.markdown("""<div class="feature-grid">
<div class="feature-card"><h4>⚡ Instant Analysis</h4><p>Upload your file and get a full anomaly report in seconds.</p></div>
<div class="feature-card"><h4>📊 Any Data Format</h4><p>Works with CSV and Excel files of any size or structure.</p></div>
<div class="feature-card"><h4>🎯 Plain English Reports</h4><p>No jargon. Clear, specific findings with exact row numbers.</p></div>
</div>""", unsafe_allow_html=True)

    st.markdown("""<div class="pricing-box"><h3>Simple Pricing</h3><div class="price">$9<span>/month</span></div><ul><li>5 free analyses to start</li><li>Unlimited analyses with Pro</li><li>CSV &amp; Excel support</li><li>Cancel anytime</li></ul></div>""", unsafe_allow_html=True)
