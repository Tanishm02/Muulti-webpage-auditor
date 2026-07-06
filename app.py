import streamlit as st
import pandas as pd
import plotly.express as px
import requests
from audit_engine import detect_discrepancies

# --- 1. SET PAGE AND APPLICATION LAYOUT CONFIGURATION ---
st.set_page_config(page_title="SAP Master Data Governance Dashboard", layout="wide", initial_sidebar_state="collapsed")

# Inject styling to clear standard Streamlit headers/footers to frame the template aesthetic
st.markdown("""
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    .block-container {padding-top: 2rem !important; padding-bottom: 2rem !important;}
    body { background-color: #0F172A !important; color: #e4e2e4 !important; font-family: 'Inter', sans-serif !important; }
    .glass-card { background: rgba(30, 41, 59, 0.6); backdrop-filter: blur(12px); border: 1px solid #334155; transition: all 0.3s ease; }
    </style>
""", unsafe_allow_html=True)

# --- 2. HEADER INTERFACE BANNER ---
st.title("📊 SAP MDM Quality Control & Governance Dashboard")
st.markdown("### Executive Master Data Audit Profile & Severity Tracking")
st.markdown("Upload your customer master dataset below to run automated system audits and generate an AI-powered data governance summary.")

# --- 3. DYNAMIC FILE PROCESSING COMPONENT ---
uploaded_file = st.file_uploader("Upload SAP Customer Master Dataset (.csv, .xlsx)", type=["csv", "xlsx"])

if uploaded_file is not None:
    try:
        # Load data matrix safely based on extension boundary
        if uploaded_file.name.endswith('.csv'):
            raw_df = pd.read_csv(uploaded_file)
        else:
            raw_df = pd.read_excel(uploaded_file)

        # ── Persist to session state so sub-pages can access the data ──
        st.session_state["raw_df"] = raw_df
        st.session_state["file_name"] = uploaded_file.name

        # --- 4. BACKEND AUDIT CRITERIA CALCULATION ENGINE ---
        # All counts are now PER ROW (not per cell).
        # • Same discrepancy type appearing in multiple columns of one row = 1 count.
        # • Two different discrepancy types in one row = 1 count in each category.
        results = detect_discrepancies(raw_df)
        st.session_state["discrepancy_results"] = results

        total_audited_records = len(raw_df)

        # Build classification structural matrix from engine results
        categories = [
            "Duplicate Records", "Data Entry Errors", "Incomplete Records",
            "Incorrect Classification", "Inconsistent Data Maintenance", "Lack of Governance",
        ]
        data = {
            "DISCREPANCY_CATEGORY": categories,
            "COUNT": [results[c]["count"] for c in categories],
            "SEVERITY": [results[c]["severity"] for c in categories],
        }
        df = pd.DataFrame(data)

        # Ensure safe scaling when file is flawless
        total_incidents = df["COUNT"].sum()
        if total_incidents == 0:
            df["PERCENTAGE"] = 0.0
            health_index = 100.0
            high_severity_count = 0
        else:
            df["PERCENTAGE"] = (df["COUNT"] / total_incidents) * 100
            high_severity_count = df[df["SEVERITY"] == "High"]["COUNT"].sum()
            health_index = 100.0 - ((high_severity_count / total_incidents) * 100)

        # --- 5. RENDER ENTERPRISE KPI GRID ---
        st.success(f"✅ Master File Successfully Loaded: {uploaded_file.name} | Processed Rows: {total_audited_records:,}")

        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric(label="Total Records Audited", value=f"{total_audited_records:,}")
        with col2:
            st.metric(label="Overall Data Health Index %", value=f"{health_index:.2f}%", delta=f"{(health_index - 100.0):.2f}% Change")
        with col3:
            st.metric(label="Critical Risks Flagged (High Severity)", value=f"{high_severity_count}")

        st.markdown("---")

        # --- 6. ADVANCED DUAL CHART DISPLAY AREA ---
        chart_col1, chart_col2 = st.columns([2, 1])

        with chart_col1:
            st.subheader("Chart A: Discrepancy Frequency Distribution")
            fig_bar = px.bar(
                df.sort_values(by="COUNT", ascending=True),
                x="COUNT",
                y="DISCREPANCY_CATEGORY",
                orientation='h',
                text="COUNT",
                color="SEVERITY",
                color_discrete_map={"High": "#EF553B", "Medium": "#636EFA"},
                labels={"COUNT": "Incident Count", "DISCREPANCY_CATEGORY": "Category"},
            )
            fig_bar.update_layout(height=400, margin=dict(l=20, r=20, t=20, b=20), paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font_color='#E2E8F0')
            st.plotly_chart(fig_bar, use_container_width=True, config={'displayModeBar': False})

        with chart_col2:
            st.subheader("Chart B: Severity Distribution")
            severity_df = df.groupby("SEVERITY")["COUNT"].sum().reset_index()
            fig_pie = px.pie(
                severity_df,
                values="COUNT",
                names="SEVERITY",
                hole=0.4,
                color="SEVERITY",
                color_discrete_map={"High": "#EF553B", "Medium": "#636EFA"}
            )
            fig_pie.update_layout(height=400, margin=dict(l=20, r=20, t=20, b=20), paper_bgcolor='rgba(0,0,0,0)', font_color='#E2E8F0')
            st.plotly_chart(fig_pie, use_container_width=True, config={'displayModeBar': False})

        st.markdown("---")

        # --- 7. CLICKABLE STRUCTURAL DATA VIEW ---
        # Each category name is a hyperlink that opens the detail page in a new tab.
        st.subheader("📋 Consolidated Failure Master Data Reference Table")
        st.caption("Click any discrepancy category below to view the specific flagged records in a new tab.")

        table_html = """
        <div style="overflow-x:auto;">
        <table style="width:100%; border-collapse:collapse; color:#E2E8F0; font-size:0.95em;">
        <thead>
        <tr style="border-bottom:2px solid #334155;">
            <th style="padding:14px 16px; text-align:left; color:#94A3B8; font-weight:600;">Discrepancy Category</th>
            <th style="padding:14px 16px; text-align:right; color:#94A3B8; font-weight:600;">Count</th>
            <th style="padding:14px 16px; text-align:center; color:#94A3B8; font-weight:600;">Severity</th>
            <th style="padding:14px 16px; text-align:right; color:#94A3B8; font-weight:600;">Percentage</th>
        </tr>
        </thead>
        <tbody>
        """
        for _, row in df.iterrows():
            cat = row["DISCREPANCY_CATEGORY"]
            url_cat = cat.replace(" ", "_")
            sev = row["SEVERITY"]
            sev_color = "#EF553B" if sev == "High" else "#636EFA"
            pct = row["PERCENTAGE"]
            cnt = row["COUNT"]
            table_html += f"""
            <tr style="border-bottom:1px solid #1E293B; transition:background 0.2s;"
                onmouseover="this.style.background='rgba(30,41,59,0.8)'"
                onmouseout="this.style.background='transparent'">
                <td style="padding:14px 16px;">
                    <a href="/Discrepancy_Details?type={url_cat}" target="_blank"
                       style="color:#60A5FA; text-decoration:none; font-weight:600; border-bottom:1px dashed rgba(96,165,250,0.35);">
                        {cat} <span style="font-size:0.75em; opacity:0.55;">↗</span>
                    </a>
                </td>
                <td style="padding:14px 16px; text-align:right; font-weight:600; font-variant-numeric:tabular-nums;">{cnt:,}</td>
                <td style="padding:14px 16px; text-align:center;">
                    <span style="background:{sev_color}1A; color:{sev_color}; padding:5px 14px; border-radius:20px; font-size:0.85em; font-weight:600; border:1px solid {sev_color}33;">
                        {sev}
                    </span>
                </td>
                <td style="padding:14px 16px; text-align:right; font-variant-numeric:tabular-nums;">{pct:.2f}%</td>
            </tr>
            """
        table_html += "</tbody></table></div>"
        st.markdown(table_html, unsafe_allow_html=True)

        st.markdown("---")

        # --- 8. SECURE OPENROUTER NETWORK CALL INTEGRATION ---
        st.subheader("🤖 AI Executive Audit Insights & Remediation Roadmap")

        try:
            api_key = st.secrets["OPENROUTER_API_KEY"]

            summary_stats_payload = df.to_json(orient="records")

            prompt = f"""
            You are an expert Enterprise SAP Master Data Governance Specialist.
            I have just finalized a deep quality assurance validation run on an SAC customer data export.

            Data Audit Performance Profile:
            - File Name: {uploaded_file.name}
            - Base System Accounts Inspected: {total_audited_records}
            - Data Health Index calculated: {health_index:.2f}%
            - Summary Profile Dataset metrics: {summary_stats_payload}

            Based on these metrics, generate a comprehensive strategic Executive Report. You must include:
            1. A formal data validation audit performance summary paragraph.
            2. A rigorous corporate risk table matching the classification profile details.
            3. 3 core action points explicitly identifying mitigation strategies for our master data engineering team.
            Maintain an enterprise-ready tone. Do not include markdown code wrapping blocks.
            """

            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            }
            payload = {
                "model": "nvidia/nemotron-3-ultra-550b-a55b:free",
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.1,
            }

            with st.spinner("NVIDIA Nemotron 3 Ultra processing corporate audit analytics matrix..."):
                response = requests.post(
                    "https://openrouter.ai/api/v1/chat/completions",
                    headers=headers,
                    json=payload,
                )
                if response.status_code == 200:
                    ai_narrative = response.json()["choices"][0]["message"]["content"]
                    st.markdown(ai_narrative)
                else:
                    st.error(f"Cloud Network Error {response.status_code}: API Gateway connection failed.")

        except KeyError:
            st.warning("⚠️ Configuration Alert: Ensure your OpenRouter developer key flag is configured inside `.streamlit/secrets.toml`.")

    except Exception as e:
        st.error(f"❌ Error compiling target database structures: {e}")

else:
    st.info("👋 Welcome to the Auditor Console. Please upload a CSV or Excel Customer Master export to launch the live analytics pipeline.")
