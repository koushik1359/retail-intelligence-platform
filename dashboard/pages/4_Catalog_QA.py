import streamlit as st
import requests

st.set_page_config(page_title="Catalog Q&A", layout="wide")
st.title("💬 Catalog Q&A")
st.caption("Ask natural language questions about the product catalog. Powered by Claude Opus 4.8 + ChromaDB RAG.")

API = "http://localhost:8000"

EXAMPLES = [
    "What are the best snack products for kids?",
    "Which products are good for breakfast?",
    "What organic products do we carry?",
    "Suggest some beverages for a party",
]

if "qa_question" not in st.session_state:
    st.session_state["qa_question"] = ""

st.markdown("**Example questions:**")
cols = st.columns(len(EXAMPLES))
for i, ex in enumerate(EXAMPLES):
    if cols[i].button(ex, key=f"ex_{i}"):
        st.session_state["qa_question"] = ex
        st.rerun()

question = st.text_input("Or type your own question:", value=st.session_state["qa_question"])

if st.button("Ask", type="primary") and question:
    st.session_state["qa_question"] = question
    with st.spinner("Claude is thinking..."):
        r = requests.post(f"{API}/ask", json={"question": question})

    if r.status_code == 200:
        data = r.json()
        st.subheader("Answer")
        st.markdown(data["answer"])
        with st.expander("📚 Source Products Retrieved"):
            for i, src in enumerate(data["sources"], 1):
                st.markdown(f"**{i}.** {src[:300]}...")
    else:
        st.error(f"API error {r.status_code}: {r.text}")
