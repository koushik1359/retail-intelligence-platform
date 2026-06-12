import streamlit as st

BG      = "#F7F8FC"
CARD    = "#FFFFFF"
BORDER  = "#E5E7EB"
PRIMARY = "#6366F1"
IND_LT  = "#EEF2FF"
TEAL    = "#0D9488"
GREEN   = "#059669"
AMBER   = "#D97706"
RED     = "#DC2626"
TEXT    = "#111827"
MUTED   = "#6B7280"

CHART_COLORS = ["#6366F1", "#0D9488", "#F59E0B", "#EF4444", "#8B5CF6", "#06B6D4"]


def inject_css():
    st.markdown(f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
    html, body, [class*="css"] {{ font-family: 'Inter', sans-serif !important; }}
    .stApp {{ background: {BG} !important; }}
    .block-container {{ padding: 2rem 2.5rem !important; max-width: 1300px !important; }}
    #MainMenu, footer {{ visibility: hidden; }}

    /* Sidebar */
    [data-testid="stSidebar"] {{
        background: {CARD} !important;
        border-right: 1px solid {BORDER} !important;
        box-shadow: 2px 0 12px rgba(0,0,0,0.04);
    }}
    [data-testid="stSidebar"] label,
    [data-testid="stSidebar"] .stMarkdown p {{ color: {MUTED} !important; font-size: 0.82rem; }}
    [data-testid="stSidebar"] h1,
    [data-testid="stSidebar"] h2,
    [data-testid="stSidebar"] h3 {{ color: {TEXT} !important; }}
    [data-testid="stSidebarNav"] {{ padding: 0 0.5rem; }}
    [data-testid="stSidebarNav"] a {{
        padding: 7px 12px !important;
        border-radius: 8px !important;
        font-size: 0.84rem !important;
        font-weight: 500 !important;
        color: {MUTED} !important;
    }}
    [data-testid="stSidebarNav"] a:hover {{
        background: {BG} !important;
        color: {TEXT} !important;
    }}
    [data-testid="stSidebarNav"] a[aria-selected="true"] {{
        background: {IND_LT} !important;
        color: {PRIMARY} !important;
        font-weight: 600 !important;
    }}

    /* Metric cards */
    [data-testid="metric-container"] {{
        background: {CARD};
        border-radius: 14px;
        padding: 1.2rem 1.4rem;
        box-shadow: 0 1px 3px rgba(0,0,0,0.07), 0 4px 20px rgba(99,102,241,0.07);
        border: 1px solid {BORDER};
    }}
    [data-testid="stMetricLabel"] {{
        font-size: 0.71rem !important;
        font-weight: 600 !important;
        color: {MUTED} !important;
        text-transform: uppercase;
        letter-spacing: 0.07em;
    }}
    [data-testid="stMetricValue"] {{
        font-size: 1.7rem !important;
        font-weight: 700 !important;
        color: {TEXT} !important;
        letter-spacing: -0.02em;
    }}

    /* Chart wrapper */
    [data-testid="stPlotlyChart"] > div {{
        background: {CARD};
        border-radius: 14px;
        border: 1px solid {BORDER};
        box-shadow: 0 1px 3px rgba(0,0,0,0.06), 0 4px 16px rgba(0,0,0,0.04);
        padding: 0.75rem;
    }}

    /* Buttons */
    .stButton > button {{
        background: {PRIMARY} !important;
        color: white !important;
        border: none !important;
        border-radius: 8px !important;
        font-size: 0.85rem !important;
        font-weight: 600 !important;
        padding: 0.5rem 1.2rem !important;
        box-shadow: 0 2px 8px rgba(99,102,241,0.28);
        transition: all 0.15s;
    }}
    .stButton > button:hover {{
        opacity: 0.88 !important;
        transform: translateY(-1px);
        box-shadow: 0 4px 14px rgba(99,102,241,0.36) !important;
    }}

    /* Inputs */
    [data-testid="stSelectbox"] > div > div,
    [data-testid="stNumberInput"] input,
    .stTextInput > div > div input {{
        background: {CARD} !important;
        border: 1px solid {BORDER} !important;
        border-radius: 8px !important;
        font-size: 0.875rem !important;
        color: {TEXT} !important;
    }}

    /* Dataframe */
    [data-testid="stDataFrame"] {{
        border-radius: 12px !important;
        overflow: hidden;
        border: 1px solid {BORDER} !important;
        box-shadow: 0 1px 4px rgba(0,0,0,0.05);
    }}

    /* Expander */
    details {{
        background: {CARD} !important;
        border: 1px solid {BORDER} !important;
        border-radius: 10px !important;
    }}

    /* Info */
    [data-testid="stInfo"] {{
        background: {IND_LT} !important;
        border-left: 3px solid {PRIMARY} !important;
        border-radius: 8px;
        color: #3730A3 !important;
    }}

    hr {{ border: none !important; border-top: 1px solid {BORDER} !important; margin: 1.5rem 0; }}

    h1 {{
        font-size: 1.55rem !important;
        font-weight: 700 !important;
        color: {TEXT} !important;
        letter-spacing: -0.03em !important;
    }}
    h2 {{
        font-size: 0.95rem !important;
        font-weight: 600 !important;
        color: {TEXT} !important;
        margin-bottom: 0.6rem !important;
    }}

    .badge {{
        display: inline-block;
        padding: 2px 10px;
        border-radius: 20px;
        font-size: 0.72rem;
        font-weight: 600;
        letter-spacing: 0.03em;
    }}
    .b-indigo {{ background: {IND_LT}; color: #4338CA; }}
    .b-teal   {{ background: #CCFBF1; color: #0F766E; }}
    .b-green  {{ background: #D1FAE5; color: #065F46; }}
    .b-amber  {{ background: #FEF3C7; color: #92400E; }}
    .b-red    {{ background: #FEE2E2; color: #991B1B; }}
    .b-gray   {{ background: {BG};    color: {MUTED};  }}
    </style>
    """, unsafe_allow_html=True)


def sidebar_brand():
    st.markdown(f"""
    <div style='padding:1.4rem 1rem 1rem;border-bottom:1px solid {BORDER};margin-bottom:1rem'>
        <div style='display:flex;align-items:center;gap:9px'>
            <div style='width:32px;height:32px;border-radius:9px;
                        background:linear-gradient(135deg,{PRIMARY} 0%,{TEAL} 100%);
                        display:flex;align-items:center;justify-content:center;
                        font-size:15px;color:white;font-weight:700;flex-shrink:0'>R</div>
            <div>
                <div style='font-size:0.92rem;font-weight:700;color:{TEXT};line-height:1.2'>Retail Intel</div>
                <div style='font-size:0.7rem;color:{MUTED}'>Analytics Platform</div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)


def page_header(title, subtitle=""):
    st.markdown(f"<h1 style='margin-bottom:0.15rem'>{title}</h1>", unsafe_allow_html=True)
    if subtitle:
        st.markdown(
            f"<p style='color:{MUTED};font-size:0.85rem;margin-top:0;margin-bottom:1.4rem'>{subtitle}</p>",
            unsafe_allow_html=True,
        )


def section(label):
    st.markdown(
        f"<h2 style='margin-top:1.6rem;margin-bottom:0.5rem'>{label}</h2>",
        unsafe_allow_html=True,
    )


def badge(label, style="indigo"):
    return f'<span class="badge b-{style}">{label}</span>'


def plotly_layout(fig, title="", height=320):
    fig.update_layout(
        title=dict(text=title, font=dict(size=12.5, color=MUTED,
                   family="Inter,sans-serif"), x=0.01, y=0.97),
        height=height,
        margin=dict(l=8, r=8, t=38 if title else 12, b=8),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter,sans-serif", color=MUTED, size=11.5),
        xaxis=dict(gridcolor="#F3F4F6", linecolor=BORDER, zeroline=False,
                   tickfont=dict(size=11, color=MUTED)),
        yaxis=dict(gridcolor="#F3F4F6", linecolor="rgba(0,0,0,0)",
                   zeroline=False, tickfont=dict(size=11, color=MUTED)),
        legend=dict(bgcolor="rgba(0,0,0,0)", borderwidth=0,
                    font=dict(size=11, color=MUTED)),
        colorway=CHART_COLORS,
        hoverlabel=dict(bgcolor=CARD, bordercolor=BORDER,
                        font=dict(size=12, color=TEXT, family="Inter,sans-serif")),
    )
    return fig
