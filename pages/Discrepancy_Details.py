"""
Discrepancy Detail Page
-----------------------
Opened from the main dashboard via hyperlink.
Reads query param  ?type=Category_Name  and session state to display
the specific flagged records for that discrepancy category.

For "Duplicate Records" this page performs near-duplicate (fuzzy)
detection, groups results by descending similarity, and inserts
visual row gaps between groups.
"""

import streamlit as st
import pandas as pd
import numpy as np
from audit_engine import find_near_duplicates

# ── Page config (must be first Streamlit call) ──
st.set_page_config(
    page_title="Discrepancy Details",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── Global dark styling (matches dashboard) ──
st.markdown("""
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    .block-container {padding-top: 2rem !important; padding-bottom: 2rem !important;}
    body { background-color: #0F172A !important; color: #e4e2e4 !important; font-family: 'Inter', sans-serif !important; }
    /* Hide this page from sidebar nav to keep navigation clean */
    [data-testid="stSidebarNav"] [href*="Discrepancy_Details"] { display: none; }
    </style>
""", unsafe_allow_html=True)


# ═══════════════════════════════════════════════
#  HELPER: styled dataframe matching dark theme
# ═══════════════════════════════════════════════

def _dark_style(df):
    """Return a Styler with the dashboard's dark colour scheme."""
    return (
        df.style
        .set_properties(**{
            "color": "#E2E8F0",
            "background-color": "#0F172A",
            "border-color": "#1E293B",
        })
        .set_table_styles([
            {"selector": "th", "props": [
                "background-color: #1E293B",
                "color: #94A3B8",
                "font-weight: 600",
            ]},
            {"selector": "td", "props": [
                "border-color: #1E293B",
            ]},
            {"selector": "tr:hover td", "props": [
                "background-color: rgba(30,41,59,0.6)",
            ]},
        ])
        .hide(axis="index")
    )


def _highlight_if(val, condition_fn):
    """Cell-level highlighter — red tint when condition is True."""
    if condition_fn(val):
        return "background-color: rgba(239,85,59,0.15); color: #FCA5A5; font-weight: 600;"
    return "color: #E2E8F0; background-color: #0F172A;"


# ═══════════════════════════════════════════════
#  CATEGORY-SPECIFIC RENDERERS
# ═══════════════════════════════════════════════

def render_duplicates(df, indices, count):
    """
    Near-duplicate fuzzy detection.
    Groups are sorted by descending average similarity with visual gaps.
    """
    if len(df) < 2:
        st.info("Not enough records to perform near-duplicate analysis.")
        return

    st.subheader("Near-Duplicate Detection")
    st.caption(
        "Records are grouped by pairwise string similarity across ALL columns. "
        "Adjust the threshold to broaden or narrow the match scope."
    )

    # Large-dataset warning
    if len(df) > 500:
        st.warning(
            "⚠️ Your dataset has **{:,}** rows. Pairwise analysis is O(n²) and may "
            "take a while. If it's too slow, consider uploading a filtered subset.".format(len(df))
        )

    col_t, col_s = st.columns([1, 3])
    with col_t:
        threshold = st.slider(
            "Similarity Threshold",
            min_value=0.50,
            max_value=0.99,
            value=0.70,
            step=0.01,
            format="%.2f",
        )
    with col_s:
        st.markdown(
            f"<div style='padding-top:28px;color:#94A3B8;'>"
            f"Groups with average similarity ≥ "
            f"<strong style='color:#60A5FA;'>{threshold:.0%}</strong> "
            f"will be displayed.</div>",
            unsafe_allow_html=True,
        )

    with st.spinner("Computing pairwise similarity matrix…"):
        groups = find_near_duplicates(df, threshold=threshold)

    if not groups:
        st.warning(
            f"No near-duplicate groups found at **{threshold:.0%}** threshold. "
            "Try lowering the slider."
        )
        return

    # Summary bar
    total_involved = sum(len(m) for _, m in groups)
    st.success(
        f"Found **{len(groups)}** near-duplicate group(s) involving "
        f"**{total_involved}** unique records "
        f"(dashboard count: **{count}** exact duplicates)."
    )

    # ── Render each group with a header card + table + gap ──
    for gi, (avg_sim, members) in enumerate(groups, 1):
        # Colour code by similarity band
        if avg_sim >= 0.90:
            sim_color = "#22C55E"
            band = "High"
        elif avg_sim >= 0.75:
            sim_color = "#F59E0B"
            band = "Medium"
        else:
            sim_color = "#EF553B"
            band = "Low"

        st.markdown(
            f"""
            <div style="
                background:rgba(30,41,59,0.6);
                border:1px solid #334155;
                border-left:4px solid {sim_color};
                border-radius:8px;
                padding:14px 20px;
                margin-bottom:6px;
            ">
                <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:8px;">
                    <span style="font-weight:700;font-size:1.05em;">Group {gi}</span>
                    <span style="color:{sim_color};font-weight:600;font-size:0.95em;">
                        Avg Similarity: {avg_sim:.1%}
                        &nbsp;·&nbsp; {band} Match
                        &nbsp;·&nbsp; {len(members)} record(s)
                    </span>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        group_df = df.iloc[members].copy()
        group_df.insert(0, "_Group", gi)
        group_df.insert(1, "_Similarity", f"{avg_sim:.1%}")

        styler = _dark_style(group_df)
        row_h = max(44 * len(group_df) + 44, 100)
        st.dataframe(styler, use_container_width=True, height=row_h)

        # ← visual row gap between groups
        st.markdown("<div style='height:28px;'></div>", unsafe_allow_html=True)


def render_data_entry_errors(df, indices):
    """Highlight cells containing UNKNOWN or INVALID."""
    if not indices:
        st.info("No records with data entry errors found.")
        return
    subset = df.loc[sorted(indices)].copy()
    pattern = r"(?i)UNKNOWN|INVALID"

    def hl(val):
        return _highlight_if(
            val,
            lambda v: isinstance(v, str) and bool(pd.Series(v).str.contains(pattern, na=False).iloc[0]),
        )

    styler = _dark_style(subset)
    # applymap works in all pandas versions that Streamlit supports
    styler = styler.applymap(hl)
    st.dataframe(styler, use_container_width=True)
    st.caption("🔴 Highlighted cells contain **UNKNOWN** or **INVALID** values.")


def render_incomplete_records(df, indices):
    """Highlight null/empty cells."""
    if not indices:
        st.info("No incomplete records found.")
        return
    subset = df.loc[sorted(indices)].copy()

    def hl(val):
        return _highlight_if(val, pd.isna)

    styler = _dark_style(subset).applymap(hl)
    st.dataframe(styler, use_container_width=True)
    st.caption("🔴 Highlighted cells are **null / empty** values.")


def render_incorrect_classification(df, indices):
    """Highlight negative Credit_Limit cells."""
    if not indices:
        st.info("No records with incorrect classification found.")
        return
    subset = df.loc[sorted(indices)].copy()

    def hl(val):
        return _highlight_if(val, lambda v: isinstance(v, (int, float)) and v < 0)

    styler = _dark_style(subset).applymap(hl)
    st.dataframe(styler, use_container_width=True)
    st.caption("🔴 Highlighted cells contain **negative Credit_Limit** values.")


def render_inconsistent_maintenance(df, indices):
    """Show records with inconsistent formatting."""
    if not indices:
        st.info("No records with inconsistent data maintenance found.")
        return
    subset = df.loc[sorted(indices)].copy()
    st.dataframe(_dark_style(subset), use_container_width=True)
    st.caption(
        "These records have **formatting inconsistencies** (e.g., mixed case) "
        "compared to the dominant pattern in their respective columns."
    )


def render_lack_of_governance(df, indices):
    """Highlight missing governance-critical fields."""
    if not indices:
        st.info("No records flagged for lack of governance.")
        return
    subset = df.loc[sorted(indices)].copy()

    def hl(val):
        return _highlight_if(val, pd.isna)

    styler = _dark_style(subset).applymap(hl)
    st.dataframe(styler, use_container_width=True)
    st.caption("🔴 Highlighted cells are **missing governance-critical** values.")


# ═══════════════════════════════════════════════
#  PAGE ENTRY POINT
# ═══════════════════════════════════════════════

# ── Read ?type= from URL query params ──
try:
    # Streamlit >= 1.30
    discrepancy_type = st.query_params.get("type", "Duplicate_Records")
    if isinstance(discrepancy_type, (list, tuple)):
        discrepancy_type = discrepancy_type[0]
except AttributeError:
    # Streamlit < 1.30
    qp = st.experimental_get_query_params()
    discrepancy_type = qp.get("type", ["Duplicate_Records"])[0]

discrepancy_type = discrepancy_type.replace("_", " ")

# ── Guard: session state must exist ──
if "raw_df" not in st.session_state or "discrepancy_results" not in st.session_state:
    st.error("⚠️ No data loaded. Please upload a file from the main dashboard first.")
    st.markdown('[← Return to Dashboard](/)', unsafe_allow_html=True)
    st.stop()

raw_df = st.session_state["raw_df"]
results = st.session_state["discrepancy_results"]
file_name = st.session_state.get("file_name", "Unknown")

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
st.title(f"🔍 {discrepancy_type} — Detailed Record View")
st.markdown(
    f"**Source:** `{file_name}` &nbsp;│&nbsp; "
    f"**Flagged Records:** {count} &nbsp;│&nbsp; "
    f"**Severity:** <span style='color:{sev_color};font-weight:600;'>{severity}</span>",
    unsafe_allow_html=True,
)
st.markdown("---")

# ── Dispatch to the correct renderer ──
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
