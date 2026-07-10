"""
Discrepancy Detail Page - With Cell Highlighting & Duplicate Grouping
"""

import streamlit as st
import pandas as pd
import numpy as np

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
    </style>
""", unsafe_allow_html=True)


# ═══════════════════════════════════════════════
#  HELPER: Base table styling
# ═══════════════════════════════════════════════

def get_base_styles():
    """Return base table styles for dark theme"""
    return [
        {"selector": "th", "props": [
            "background-color: #1E293B",
            "color: #94A3B8",
            "font-weight: 600",
            "border: 1px solid #334155",
            "text-align: left",
        ]},
        {"selector": "td", "props": [
            "background-color: #0F172A",
            "color: #E2E8F0",
            "border: 1px solid #1E293B",
        ]},
        {"selector": "tr:hover td", "props": [
            "background-color: rgba(30,41,59,0.6) !important",
        ]},
        {"selector": ".row_heading", "props": [
            "display: none",
        ]},
    ]


def apply_base_style(styler):
    """Apply base dark theme to styler"""
    return styler.set_table_styles(get_base_styles()).hide(axis="index")


# ═══════════════════════════════════════════════
#  HIGHLIGHT FUNCTIONS (return CSS or empty string)
# ═══════════════════════════════════════════════

HL_STYLE = "background-color: rgba(239,85,59,0.3); color: #FCA5A5; font-weight: 600;"

def hl_unknown_invalid(val):
    """Highlight UNKNOWN or INVALID values"""
    if isinstance(val, str):
        val_upper = val.upper().strip()
        if "UNKNOWN" in val_upper or "INVALID" in val_upper:
            return HL_STYLE
    return ""

def hl_null_empty(val):
    """Highlight null or empty values"""
    if pd.isna(val) or (isinstance(val, str) and val.strip() == ""):
        return HL_STYLE
    return ""

def hl_negative(val):
    """Highlight negative numeric values"""
    if isinstance(val, (int, float)) and not pd.isna(val) and val < 0:
        return HL_STYLE
    return ""


# ═══════════════════════════════════════════════
#  RENDERER: DUPLICATE RECORDS (GROUPED)
# ═══════════════════════════════════════════════

def render_duplicates(df, indices, count):
    """Group exact duplicates together with visual gaps"""
    if len(df) < 2:
        st.info("Not enough records to detect duplicates.")
        return
    
    # Get duplicated rows (keep=False marks ALL duplicates)
    dup_mask = df.duplicated(keep=False)
    dup_df = df[dup_mask].copy()
    
    if dup_df.empty:
        st.info("No duplicate records found.")
        return
    
    # Group by all column values to find duplicate groups
    # Convert to tuple for grouping (handles NaN properly)
    def make_key(row):
        return tuple(str(v) if not pd.isna(v) else "__NaN__" for v in row)
    
    dup_df["_group_key"] = dup_df.apply(make_key, axis=1)
    groups = dup_df.groupby("_group_key")
    
    group_num = 0
    total_shown = 0
    
    for key, group in groups:
        if len(group) < 2:
            continue
        
        group_num += 1
        total_shown += len(group)
        
        # Prepare display dataframe
        display_df = group.drop(columns=["_group_key"]).copy()
        display_df.insert(0, "Group", group_num)
        display_df.insert(1, "Copies", len(group))
        
        # Display group header
        st.markdown(
            f"""
            <div style="
                background: rgba(30,41,59,0.6);
                border: 1px solid #334155;
                border-left: 4px solid #636EFA;
                border-radius: 6px;
                padding: 10px 16px;
                margin-bottom: 8px;
            ">
                <strong>Group {group_num}</strong> — {len(group)} identical record(s)
            </div>
            """,
            unsafe_allow_html=True
        )
        
        # Style and display
        styler = apply_base_style(display_df.style)
        row_height = min(250, 40 * len(display_df) + 50)
        st.dataframe(styler, use_container_width=True, height=row_height)
        
        # Visual gap between groups
        st.markdown("<div style='height:20px;'></div>", unsafe_allow_html=True)
    
    if group_num == 0:
        st.info("No duplicate groups found.")
    else:
        st.success(f"Displayed **{group_num}** duplicate group(s) containing **{total_shown}** total records.")


# ═══════════════════════════════════════════════
#  RENDERER: DATA ENTRY ERRORS
# ═══════════════════════════════════════════════

def render_data_entry_errors(df, indices):
    """Highlight cells with UNKNOWN or INVALID"""
    if not indices:
        st.info("✅ No records with data entry errors.")
        return
    
    flagged_df = df.loc[sorted(indices)].copy()
    flagged_df.insert(0, "#", range(1, len(flagged_df) + 1))
    
    styler = apply_base_style(flagged_df.style)
    styler = styler.map(hl_unknown_invalid)
    
    st.dataframe(styler, use_container_width=True)
    st.caption("🔴 Highlighted cells contain **UNKNOWN** or **INVALID** values.")


# ═══════════════════════════════════════════════
#  RENDERER: INCOMPLETE RECORDS
# ═══════════════════════════════════════════════

def render_incomplete_records(df, indices):
    """Highlight null/empty cells"""
    if not indices:
        st.info("✅ No incomplete records.")
        return
    
    flagged_df = df.loc[sorted(indices)].copy()
    flagged_df.insert(0, "#", range(1, len(flagged_df) + 1))
    
    styler = apply_base_style(flagged_df.style)
    styler = styler.map(hl_null_empty)
    
    st.dataframe(styler, use_container_width=True)
    st.caption("🔴 Highlighted cells are **null / empty** values.")


# ═══════════════════════════════════════════════
#  RENDERER: INCORRECT CLASSIFICATION
# ═══════════════════════════════════════════════

def render_incorrect_classification(df, indices):
    """Highlight negative Credit_Limit cells"""
    if not indices:
        st.info("✅ No records with incorrect classification.")
        return
    
    flagged_df = df.loc[sorted(indices)].copy()
    flagged_df.insert(0, "#", range(1, len(flagged_df) + 1))
    
    styler = apply_base_style(flagged_df.style)
    
    # Only highlight Credit_Limit column if it exists
    if "Credit_Limit" in flagged_df.columns:
        styler = styler.map(hl_negative, subset=["Credit_Limit"])
    
    st.dataframe(styler, use_container_width=True)
    st.caption("🔴 Highlighted cells have **negative Credit_Limit** values.")


# ═══════════════════════════════════════════════
#  RENDERER: INCONSISTENT DATA MAINTENANCE
# ═══════════════════════════════════════════════

def render_inconsistent_maintenance(df, indices):
    """Highlight cells with inconsistent casing"""
    if not indices:
        st.info("✅ No records with inconsistent formatting.")
        return
    
    flagged_df = df.loc[sorted(indices)].copy()
    flagged_df.insert(0, "#", range(1, len(flagged_df) + 1))
    
    # Determine dominant case pattern for each string column
    dominant_case = {}
    for col in df.select_dtypes(include=["object"]).columns:
        vals = df[col].dropna().astype(str)
        if len(vals) < 2:
            dominant_case[col] = None
            continue
        upper_count = vals.str.isupper().sum()
        lower_count = vals.str.islower().sum()
        if upper_count > lower_count:
            dominant_case[col] = "upper"
        elif lower_count > upper_count:
            dominant_case[col] = "lower"
        else:
            dominant_case[col] = None
    
    # Create highlight functions for each column
    styler = apply_base_style(flagged_df.style)
    
    for col, pattern in dominant_case.items():
        if pattern is None or col not in flagged_df.columns:
            continue
        
        if pattern == "upper":
            def hl_wrong_case(val, p=pattern):
                if isinstance(val, str) and val.strip() and val.strip().isalpha():
                    return HL_STYLE if not val.strip().isupper() else ""
                return ""
        else:  # lower
            def hl_wrong_case(val, p=pattern):
                if isinstance(val, str) and val.strip() and val.strip().isalpha():
                    return HL_STYLE if not val.strip().islower() else ""
                return ""
        
        styler = styler.map(hl_wrong_case, subset=[col])
    
    st.dataframe(styler, use_container_width=True)
    st.caption("🔴 Highlighted cells have **inconsistent casing** compared to the dominant format.")


# ═══════════════════════════════════════════════
#  RENDERER: LACK OF GOVERNANCE
# ═══════════════════════════════════════════════

def render_lack_of_governance(df, indices):
    """Highlight missing governance-critical fields"""
    if not indices:
        st.info("✅ No records flagged for lack of governance.")
        return
    
    flagged_df = df.loc[sorted(indices)].copy()
    flagged_df.insert(0, "#", range(1, len(flagged_df) + 1))
    
    # Identify governance-critical columns
    gov_keywords = [
        "email", "phone", "tax", "vat", "registration",
        "region", "country", "postal", "zip", "city", "address"
    ]
    gov_cols = [c for c in df.columns if any(kw in c.lower() for kw in gov_keywords)]
    
    # Fallback to first 3 columns if no governance columns found
    if not gov_cols:
        gov_cols = list(df.columns[:3])
    
    styler = apply_base_style(flagged_df.style)
    
    # Only highlight governance columns
    for col in gov_cols:
        if col in flagged_df.columns:
            styler = styler.map(hl_null_empty, subset=[col])
    
    st.dataframe(styler, use_container_width=True)
    st.caption(f"🔴 Highlighted cells are **missing governance-critical** values (columns: {', '.join(gov_cols)}).")


# ═══════════════════════════════════════════════
#  PAGE ENTRY POINT
# ═══════════════════════════════════════════════

# Get discrepancy type from session state
discrepancy_type = st.session_state.get("selected_discrepancy", None)

if discrepancy_type is None:
    st.error("⚠️ No discrepancy category selected. Please go back to the dashboard.")
    st.markdown('[← Return to Dashboard](/)', unsafe_allow_html=True)
    st.stop()

# Check session state exists
if "raw_df" not in st.session_state or "discrepancy_results" not in st.session_state:
    st.error("⚠️ No data loaded. Please upload a file from the main dashboard first.")
    st.markdown('[← Return to Dashboard](/)', unsafe_allow_html=True)
    st.stop()

raw_df = st.session_state["raw_df"]
results = st.session_state["discrepancy_results"]
file_name = st.session_state.get("file_name", "Unknown")

# Validate category
if discrepancy_type not in results:
    st.error(f"⚠️ Unknown discrepancy category: **{discrepancy_type}**")
    st.markdown('[← Return to Dashboard](/)', unsafe_allow_html=True)
    st.stop()

info = results[discrepancy_type]
indices = sorted(info["indices"])
count = info["count"]
severity = info["severity"]
sev_color = "#EF553B" if severity == "High" else "#636EFA"

# ── Page header ──
st.markdown('[← Return to Dashboard](/)', unsafe_allow_html=True)
st.title(f"🔍 {discrepancy_type}")
st.markdown(
    f"**Source:** `{file_name}` &nbsp;│&nbsp; "
    f"**Flagged Records:** {count} &nbsp;│&nbsp; "
    f"**Severity:** <span style='color:{sev_color};font-weight:600;'>{severity}</span>",
    unsafe_allow_html=True,
)
st.markdown("---")

# ── Dispatch to correct renderer ──
renderers = {
    "Duplicate Records":              lambda: render_duplicates(raw_df, indices, count),
    "Data Entry Errors":              lambda: render_data_entry_errors(raw_df, indices),
    "Incomplete Records":             lambda: render_incomplete_records(raw_df, indices),
    "Incorrect Classification":       lambda: render_incorrect_classification(raw_df, indices),
    "Inconsistent Data Maintenance":  lambda: render_inconsistent_maintenance(raw_df, indices),
    "Lack of Governance":             lambda: render_lack_of_governance(raw_df, indices),
}

renderer = renderers.get(discrepancy_type)
if renderer:
    renderer()
else:
    st.error(f"No detail view implemented for: {discrepancy_type}")
