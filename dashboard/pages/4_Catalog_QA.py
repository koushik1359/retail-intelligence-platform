import streamlit as st
import requests
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from style import inject_css, sidebar_brand, page_header, PRIMARY, MUTED, BORDER, TEXT, BG

st.set_page_config(page_title="Catalog Q&A", layout="wide")
inject_css()

st.markdown(f"""
<style>
.answer-box {{
    background: white;
    border: 1px solid {BORDER};
    border-left: 3px solid {PRIMARY};
    border-radius: 0 8px 8px 0;
    padding: 1rem 1.2rem;
    font-size: 0.9rem;
    line-height: 1.7;
    color: {TEXT};
    margin: 0.5rem 0 0.8rem;
}}
.source-pill {{
    display: inline-block;
    background: {BG};
    border: 1px solid {BORDER};
    border-radius: 6px;
    padding: 5px 10px;
    font-size: 0.78rem;
    color: {MUTED};
    margin: 3px 3px 3px 0;
}}
.q-label {{
    font-size:0.75rem;font-weight:700;
    color:{MUTED};text-transform:uppercase;
    letter-spacing:0.06em;margin-bottom:3px;
}}
</style>
""", unsafe_allow_html=True)

API = "https://koushik1359-retail-intelligence-api.hf.space"
HEADERS = {"X-API-Key": os.getenv("INTERNAL_API_KEY", "")}
EXAMPLES = [
    "Best snacks for kids?",
    "Breakfast items under £3",
    "What organic products do we carry?",
    "Beverages for a party",
]

with st.sidebar:
    sidebar_brand()
    st.page_link("app.py",                          label="Home",               icon="🏠")
    st.page_link("pages/1_Executive_overview.py",   label="Executive Overview", icon="📊")
    st.page_link("pages/2_Demand_Forecast.py",      label="Demand Forecast",    icon="📈")
    st.page_link("pages/3_Recommendations.py",      label="Recommendations",    icon="🛒")
    st.page_link("pages/4_Catalog_QA.py",           label="Catalog Q&A",        icon="💬")
    st.page_link("pages/5_Real_Time_Transactions.py", label="Live Transactions",icon="⚡")
    st.markdown("---")
    st.markdown(f"""
    <div style='padding:0.5rem 0.2rem'>
        <p style='font-size:0.75rem;font-weight:600;color:{MUTED};text-transform:uppercase;
                  letter-spacing:0.05em;margin-bottom:0.4rem'>Powered by</p>
        <p style='font-size:0.85rem;font-weight:600;color:{TEXT};margin:0'>Claude Opus 4.8</p>
        <p style='font-size:0.8rem;color:{MUTED};margin:2px 0'>ChromaDB · MiniLM-L6-v2</p>
        <p style='font-size:0.78rem;color:{MUTED};margin-top:6px'>500 products indexed<br>k=5 similarity retrieval</p>
    </div>
    """, unsafe_allow_html=True)

page_header("Catalog Q&A", "Natural language search over the enriched product catalog")

if "qa_question" not in st.session_state: st.session_state["qa_question"] = ""
if "qa_history"  not in st.session_state: st.session_state["qa_history"]  = []

st.markdown(f"<p style='font-size:0.82rem;color:{MUTED};margin-bottom:6px'>Try an example:</p>",
            unsafe_allow_html=True)
cols = st.columns(len(EXAMPLES))
for i, ex in enumerate(EXAMPLES):
    if cols[i].button(ex, key=f"ex_{i}"):
        st.session_state["qa_question"] = ex
        st.rerun()

question = st.text_input("Question", value=st.session_state["qa_question"],
                         placeholder="Ask anything about the product catalog…",
                         label_visibility="collapsed")
ask = st.button("Ask", type="primary")

if ask and question:
    st.session_state["qa_question"] = question
    with st.spinner("Searching catalog…"):
        r = requests.post(f"{API}/ask", json={"question": question}, headers=HEADERS)
    if r.status_code == 200:
        data = r.json()
        st.session_state["qa_history"].append({
            "question": question,
            "answer":   data["answer"],
            "sources":  data.get("sources", []),
        })
        st.session_state["qa_question"] = ""
    else:
        st.error(f"API error {r.status_code}")

for entry in reversed(st.session_state["qa_history"]):
    st.markdown(f'<div class="q-label">Q</div><p style="font-size:0.9rem;font-weight:600;margin:0">{entry["question"]}</p>', unsafe_allow_html=True)
    st.markdown(f'<div class="answer-box">{entry["answer"]}</div>', unsafe_allow_html=True)
    if entry["sources"]:
        pills = "".join(f'<span class="source-pill">{s[:60]}…</span>' for s in entry["sources"])
        with st.expander(f"{len(entry['sources'])} products retrieved"):
            st.markdown(pills, unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)
