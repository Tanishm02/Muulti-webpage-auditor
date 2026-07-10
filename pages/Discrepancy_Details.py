"""
Discrepancy Detail Page - With Cell Highlighting & Duplicate Grouping
Using HTML tables for reliable rendering
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
    
    /* Scrollable table container */
    .table-container {
        max-height: 500px;
        overflow-y: auto;
        border: 1px solid #334155;
        border-radius: 8px;
        margin-bottom: 8px;
    }
    .table-container table {
        width: 100%;
        border-collapse: collapse;
        font-size: 14px;
        font-family: 'Inter', sans-serif;
    }
    .table-container thead {
        position: sticky;
        top: 0;
        z-index: 1;
    }
    .table-container th {
        background-color: #1E293B;
        color: #94A3B8;
        padding: 12px;
        border: 1px solid #334155;
        text-align: left;
        font-weight: 600;
    }
    .table-container td {
        background-color: #0F172A;
        color: #E2E8F0;
        padding: 10px 12px;
        border: 1px solid #1E293B;
    }
    .table-container tr:hover td {
        background-color: rgba(30,41,59,0.6) !important;
    }
    /* Highlighted cell */
    .cell-hl {
        background-color: rgba(239,85,59,0.3) !important;
        color: #FCA5A5 !important;
        font-weight: 600;
    }
    /* Group header */
    .group-header {
        background: rgba(30,41,59,0.6);
        border: 1px solid #334155;
        border-left: 4px solid #636EFA;
        border-radius: 6px;
        padding: 10px 16px;
        margin: 8px 0;
    }
    .group-gap {
        height: 20px;
    }
    </style>
""", unsafe_allow_html=True)


# ═══════════════════════════════════════════════
#  HELPER: Render HTML Table
# ═══════════════════════════════════════════════

def render_html_table(df, highlight_fn=None):
    """
    Render a dataframe as an HTML table with optional cell highlighting.
    highlight_fn: function(val) -> bool (True = highlight cell)
    """
    html = '<div class="table-container"><table>'
    
    # Header row
    html += '<thead><tr>'
    for col in df.columns:
        html += f'<th>{col}</th>'
    html += '</tr></thead>'
    
    # Data rows
    html += '<tbody>'
    for _, row in df.iterrows():
        html += '<tr>'
        for col in df.columns:
            val = row[col]
            # Format display value
            if pd.isna(val):
                display_val = '<em style="color:#64748B;">NULL</em>'
            else:
                display_val = str(val)
            
            # Check if cell should be highlighted
            cell_class = ' class="cell-hl"' if (highlight_fn and highlight_fn(val)) else ''
            html += f'<td{cell_class}>{display_val}</td>'
        html += '</tr>'
    html += '</tbody></table></div>'
    
    st.markdown(html, unsafe_allow_html=True)


# ═══════════════════════════════════════════════
#  HIGHLIGHT FUNCTIONS (return True/False)
# ═══════════════════════════════════════════════

def is_unknown_invalid(val):
    """Check if value is UNKNOWN or INVALID"""
    if isinstance(val, str):
        val_upper = val.upper().strip()
        return "UNKNOWN" in val_upper or "INVALID" in val_upper
    return False

def is_null_empty(val):
    """Check if value is null or empty"""
    if pd.isna(val):
        return True
    if isinstance(val, str) and val.strip() == "":
        return True
    return False

def is_negative(val):
    """Check if value is negative"""
    if isinstance(val, (int, float)) and not pd.isna(val):
        return val < 0
    return False


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
        display_df = group.drop(columns=["_group_key"]).copy().reset_index(drop=True)
        display_df.insert(0, "Group", group_num)
        display_df.insert(1, "Copies", len(group))
        
        # Display group header
        st.markdown(
            f'<div class="group-header"><strong>Group {group_num}</strong> — {len(group)} identical record(s)</div>',
            unsafe_allow_html=True
        )
        
        # Render table (no highlighting needed for duplicates - all rows are identical)
        render_html_table(display_df)
        
        # Visual gap between groups
        st.markdown('<div class="group-gap"></div>', unsafe_allow_html=True)
    
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
    
    flagged_df = df.loc[sorted(indices)].copy().reset_index(drop=True)
    flagged_df.insert(0, "#", range(1, len(flagged_df) + 1))
    
    render_html_table(flagged_df, highlight_fn=is_unknown_invalid)
    st.caption("🔴 Highlighted cells contain **UNKNOWN** or **INVALID** values.")


# ═══════════════════════════════════════════════
#  RENDERER: INCOMPLETE RECORDS
# ═══════════════════════════════════════════════

def render_incomplete_records(df, indices):
    """Highlight null/empty cells"""
    if not indices:
        st.info("✅ No incomplete records.")
        return
    
    flagged_df = df.loc[sorted(indices)].copy().reset_index(drop=True)
    flagged_df.insert(0, "#", range(1, len(flagged_df) + 1))
    
    render_html_table(flagged_df, highlight_fn=is_null_empty)
    st.caption("🔴 Highlighted cells are **null / empty** values.")


# ═══════════════════════════════════════════════
#  RENDERER: INCORRECT CLASSIFICATION
# ═══════════════════════════════════════════════

def render_incorrect_classification(df, indices):
    """Highlight negative Credit_Limit cells"""
    if not indices:
        st.info("✅ No records with incorrect classification.")
        return
    
    flagged_df = df.loc[sorted(indices)].copy().reset_index(drop=True)
    flagged_df.insert(0, "#", range(1, len(flagged_df) + 1))
    
    # Create column-specific highlight function
    def highlight_credit_limit(val, col_name="Credit_Limit"):
        # This will be called for all cells, but we only want to highlight Credit_Limit
        return False  # We'll handle this differently below
    
    # For this case, we need column-specific highlighting
    # So we'll build the HTML manually
    html = '<div class="table-container"><table>'
    html += '<thead><tr>'
    for col in flagged_df.columns:
        html += f'<th>{col}</th>'
    html += '</tr></thead><tbody>'
    
    for _, row in flagged_df.iterrows():
        html += '<tr>'
        for col in flagged_df.columns:
            val = row[col]
            if pd.isna(val):
                display_val = '<em style="color:#64748B;">NULL</em>'
            else:
                display_val = str(val)
            
            # Only highlight if it's Credit_Limit and negative
            if col == "Credit_Limit" and is_negative(val):
                html += f'<td class="cell-hl">{display_val}</td>'
            else:
                html += f'<td>{display_val}</td>'
        html += '</tr>'
    html += '</tbody></table></div>'
    
    st.markdown(html, unsafe_allow_html=True)
    st.caption("🔴 Highlighted cells have **negative Credit_Limit** values.")


# ═══════════════════════════════════════════════
#  RENDERER: INCONSISTENT DATA MAINTENANCE
# ═══════════════════════════════════════════════

def render_inconsistent_maintenance(df, indices):
    """Highlight cells with inconsistent casing"""
    if not indices:
        st.info("✅ No records with inconsistent formatting.")
        return
    
    flagged_df = df.loc[sorted(indices)].copy().reset_index(drop=True)
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
    
    # Build HTML with column-specific highlighting
    html = '<div class="table-container"><table>'
    html += '<thead><tr>'
    for col in flagged_df.columns:
        html += f'<th>{col}</th>'
    html += '</tr></thead><tbody>'
    
    for _, row in flagged_df.iterrows():
        html += '<tr>'
        for col in flagged_df.columns:
            val = row[col]
            if pd.isna(val):
                display_val = '<em style="color:#64748B;">NULL</em>'
            else:
                display_val = str(val)
            
            # Check if this cell should be highlighted
            should_highlight = False
            if col in dominant_case and dominant_case[col] is not None:
                if isinstance(val, str) and val.strip() and val.strip().isalpha():
                    if dominant_case[col] == "upper" and not val.strip().isupper():
                        should_highlight = True
                    elif dominant_case[col] == "lower" and not val.strip().islower():
                        should_highlight = True
            
            if should_highlight:
                html += f'<td class="cell-hl">{display_val}</td>'
            else:
                html += f'<td>{display_val}</td>'
        html += '</tr>'
    html += '</tbody></table></div>'
    
    st.markdown(html, unsafe_allow_html=True)
    st.caption("🔴 Highlighted cells have **inconsistent casing** compared to the dominant format.")


# ═══════════════════════════════════════════════
#  RENDERER: LACK OF GOVERNANCE
# ═══════════════════════════════════════════════

def render_lack_of_governance(df, indices):
    """Highlight missing governance-critical fields"""
    if not indices:
        st.info("✅ No records flagged for lack of governance.")
        return
    
    flagged_df = df.loc[sorted(indices)].copy().reset_index(drop=True)
    flagged_df.insert(0, "#", range(1, len(flagged_df) + 1))
    
    # Identify governance-critical columns
    gov_keywords = [
        "email", "phone", "tax", "vat", "registration",
        "region", "country", "postal", "zip", "city", "address"
    ]
    gov_cols = set(c for c in df.columns if any(kw in c.lower() for kw in gov_keywords))
    
    # Fallback to first 3 columns if no governance columns found
    if not gov_cols:
        gov_cols = set(df.columns[:3])
    
    # Build HTML with column-specific highlighting
    html = '<div class="table-container"><table>'
    html += '<thead><tr>'
    for col in flagged_df.columns:
        html += f'<th>{col}</th>'
    html += '</tr></thead><tbody>'
    
    for _, row in flagged_df.iterrows():
        html += '<tr>'
        for col in flagged_df.columns:
            val = row[col]
            if pd.isna(val):
                display_val = '<em style="color:#64748B;">NULL</em>'
            else:
                display_val = str(val)
            
            # Only highlight if it's a governance column and is null
            if col in gov_cols and is_null_empty(val):
                html += f'<td class="cell-hl">{display_val}</td>'
            else:
                html += f'<td>{display_val}</td>'
        html += '</tr>'
    html += '</tbody></table></div>'
    
    st.markdown(html, unsafe_allow_html=True)
    st.caption(f"🔴 Highlighted cells are **missing governance-critical** values (columns: {', '.join(sorted(gov_cols))}).")


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
