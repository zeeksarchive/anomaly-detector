import streamlit as st
import pandas as pd
import anthropic

st.set_page_config(page_title="Anomaly Detector", page_icon="logo.png", layout="wide")

st.title("🔍 Anomaly Detector")
st.subheader("Upload any data — AI finds what doesn't look right")

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
                model="claude-opus-4-5",
                max_tokens=1500,
                messages=[
                    {
                        "role": "user",
                        "content": f"""You are a data analyst and auditor. Analyze this dataset for anomalies, outliers, and suspicious patterns.

Data Summary:
{data_summary}

Data Sample:
{data_sample}

Please identify:
1. Any unusual spikes or drops in numeric columns
2. Suspicious patterns or outliers
3. Data quality issues
4. What each anomaly might mean in a business context
5. What to investigate further

Be specific about row numbers and values. Write in plain English for a non-technical audience."""
                    }
                ]
            )

            result = message.content[0].text
            st.write("### 🚨 Anomaly Report")
            st.write(result)