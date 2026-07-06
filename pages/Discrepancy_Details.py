"""
Discrepancy Detail Page - Simplified Version
--------------------------------------------
Shows only the flagged records in a clean table format.
"""

import streamlit as st
import pandas as pd

# ── Page config ──
st.set_page_config(
    page_title="Discrepancy Details",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── Dark styling ──
st.markdown("""
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    .block-container {padding-top: 2rem !important; padding-bottom: 2rem !important;}
    body { background-color: #0F172A !important; color: #e4e2e4 !important; font-family: 'Inter', sans-serif !important; }
    [data-testid="stSidebarNav"] [href*="Discrepancy_Details"] { display: none; }
    
    /* Clean table styling */
    .dataframe {
        background-color: #0F172A !important;
        color: #E2E8F0 !important;
        border: 1px solid #334155 !important;
    }
    .dataframe th {
        background-color: #1E293B !important;
        color: #94A3B8 !important;
        border: 1px solid #334155 !important;
        padding: 12px !important;
    }
    .dataframe td {
        border: 1px solid #1E293B !important;
        padding: 10px !important;
        color: #E2E8F0 !important;
    }
    .dataframe tr:hover {
        background-color: rgba(30,41,59,0.6) !important;
    }
    </style>
""", unsafe_allow_html=True)


# ═══════════════════════════════════════════════
#  GET DISCREPANCY TYPE FROM SESSION STATE
# ═══════════════════════════════════════════════

# FIXED: Read from session state instead of query_params
discrepancy_type = st.session_state.get("selected_discrepancy", None)

if discrepancy_type is None:
    st.error("⚠️ No discrepancy category selected. Please go back to the dashboard and click a category.")
    st.markdown('[← Return to Dashboard](/)', unsafe_allow_html=True)
    st.stop()


# ═══════════════════════════════════════════════
#  CHECK SESSION STATE EXISTS
# ═══════════════════════════════════════════════

if "raw_df" not in st.session_state or "discrepancy_results" not in st.session_state:
    st.error("⚠️ No data loaded. Please upload a file from the main dashboard first.")
    st.markdown('[← Return to Dashboard](/)', unsafe_allow_html=True)
    st.stop()

raw_df = st.session_state["raw_df"]
results = st.session_state["discrepancy_results"]
file_name = st.session_state.get("file_name", "Unknown")


# ═══════════════════════════════════════════════
#  VALIDATE CATEGORY
# ═══════════════════════════════════════════════

if discrepancy_type not in results:
    st.error(f"⚠️ Unknown discrepancy category: **{discrepancy_type}**")
    st.markdown('[← Return to Dashboard](/)', unsafe_allow_html=True)
    st.stop()

info = results[discrepancy_type]
indices = sorted(info["indices"])
count = info["count"]
severity = info["severity"]
sev_color = "#EF553B" if severity == "High" else "#636EFA"


# ═══════════════════════════════════════════════
#  RENDER PAGE HEADER
# ═══════════════════════════════════════════════

st.markdown('[← Return to Dashboard](/)', unsafe_allow_html=True)
st.title(f"🔍 {discrepancy_type}")
st.markdown(
    f"**Source:** `{file_name}` &nbsp;│&nbsp; "
    f"**Flagged Records:** {count} &nbsp;│&nbsp; "
    f"**Severity:** <span style='color:{sev_color};font-weight:600;'>{severity}</span>",
    unsafe_allow_html=True,
)
st.markdown("---")


# ═══════════════════════════════════════════════
#  GET AND DISPLAY THE FLAGGED RECORDS
# ═══════════════════════════════════════════════

if not indices:
    st.info("✅ No records found with this discrepancy type.")
    st.stop()

# Get the flagged records
flagged_df = raw_df.loc[indices].copy().reset_index(drop=True)

# Add a row number column for reference
flagged_df.insert(0, "#", range(1, len(flagged_df) + 1))

# Display the table
st.subheader(f"Flagged Records ({len(flagged_df)})")

# Use simple dataframe display - no complex styling that causes errors
st.dataframe(
    flagged_df,
    use_container_width=True,
    height=min(400, 35 * len(flagged_df) + 40),
)

st.markdown("---")

# Simple description based on category
descriptions = {
    "Duplicate Records": "These records have identical values across all columns with at least one other record.",
    "Data Entry Errors": "These records contain 'UNKNOWN' or 'INVALID' values in one or more fields.",
    "Incomplete Records": "These records have missing (null/empty) values in one or more fields.",
    "Incorrect Classification": "These records have negative Credit_Limit values, which is invalid.",
    "Inconsistent Data Maintenance": "These records have formatting inconsistencies (e.g., mixed case) compared to the dominant pattern.",
    "Lack of Governance": "These records are missing governance-critical fields (email, phone, address, etc.).",
}

st.caption(f"📌 **Description:** {descriptions.get(discrepancy_type, 'Records flagged with this discrepancy type.')}")

# Show which columns are affected (helpful for debugging)
st.caption(f"📌 **Total records in file:** {len(raw_df):,} | **Records shown:** {len(flagged_df)}")
