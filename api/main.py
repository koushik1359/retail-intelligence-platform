import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
from starlette.responses import Response
import duckdb, chromadb, anthropic, numpy as np, faiss, pickle, time, json
from dotenv import load_dotenv

from api.schemas import (
    ForecastResponse, RecommendResponse, AskRequest, AskResponse,
    KPIResponse, AgentReportResponse, ABTestResults,
)
from models.forecasting.predict import forecast as run_forecast

load_dotenv()

DUCKDB_PATH = os.getenv("DUCKDB_PATH", "data/warehouse.duckdb")
REC_DIR     = "models/recommendations/artifacts"

# ── Prometheus metrics ─────────────────────────────────────────────────────────
REQUEST_COUNT   = Counter("api_requests_total", "Total requests", ["endpoint"])
REQUEST_LATENCY = Histogram("api_request_latency_seconds", "Request latency", ["endpoint"])

# ── App state (loaded once at startup) ────────────────────────────────────────
state = {}

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Loading models...")
    state["item_index"]    = faiss.read_index(f"{REC_DIR}/item_index.faiss")
    state["item_emb_norm"] = np.load(f"{REC_DIR}/item_embeddings_norm.npy")
    state["user_emb"]      = np.load(f"{REC_DIR}/user_embeddings.npy")
    with open(f"{REC_DIR}/item_encoder.pkl", "rb") as f:
        state["item_enc"] = pickle.load(f)
    with open(f"{REC_DIR}/user_encoder.pkl", "rb") as f:
        state["user_enc"] = pickle.load(f)

    con = duckdb.connect(DUCKDB_PATH, read_only=True)
    state["products"] = con.execute("""
        SELECT DISTINCT product_id, product_name, department
        FROM main_intermediate.int_user_product_interactions
    """).fetchdf().set_index("product_id")
    con.close()

    state["chroma"] = chromadb.PersistentClient(path="data/chromadb")
    state["claude"] = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
    print("All models loaded.")
    yield
    state.clear()

app = FastAPI(title="Retail Intelligence Platform API", version="1.0.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


# ── Helpers ────────────────────────────────────────────────────────────────────

def get_ab_variant(user_id: int) -> str:
    return "treatment" if hash(str(user_id)) % 100 >= 50 else "control"

def log_ab_impression(user_id: int, variant: str, items: list):
    try:
        con = duckdb.connect(DUCKDB_PATH)
        con.execute("""
            CREATE TABLE IF NOT EXISTS main_mart.ab_test_log (
                logged_at   TIMESTAMP DEFAULT now(),
                user_id     BIGINT,
                variant     VARCHAR,
                items_shown INTEGER,
                clicked     INTEGER DEFAULT 0,
                converted   INTEGER DEFAULT 0
            )
        """)
        con.execute(
            "INSERT INTO main_mart.ab_test_log (user_id, variant, items_shown) VALUES (?,?,?)",
            [user_id, variant, len(items)]
        )
        con.close()
    except Exception:
        pass


# ── Endpoints ──────────────────────────────────────────────────────────────────

@app.get("/health")
def health():
    return {"status": "ok", "models_loaded": len(state) > 0}


@app.get("/metrics")
def metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.get("/forecast", response_model=ForecastResponse)
def forecast(
    store_id: str = Query(..., example="CA_1"),
    item_id:  str = Query(..., example="FOODS_3_001"),
    horizon:  int = Query(28, ge=1, le=56),
):
    t0 = time.time()
    REQUEST_COUNT.labels(endpoint="/forecast").inc()
    result = run_forecast(store_id, item_id, horizon)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    REQUEST_LATENCY.labels(endpoint="/forecast").observe(time.time() - t0)
    return result


@app.get("/recommend", response_model=RecommendResponse)
def recommend(
    user_id: int = Query(..., example=1),
    n:       int = Query(10, ge=1, le=50),
):
    t0      = time.time()
    REQUEST_COUNT.labels(endpoint="/recommend").inc()
    variant = get_ab_variant(user_id)

    try:
        uid = state["user_enc"].transform([user_id])[0]
    except ValueError:
        raise HTTPException(status_code=404, detail=f"user_id {user_id} not in training data")

    user_vec = state["user_emb"][uid].reshape(1, -1).astype(np.float32)
    norm     = np.linalg.norm(user_vec)
    if norm > 0:
        user_vec /= norm

    _, I    = state["item_index"].search(user_vec, n + 1)
    item_ids = state["item_enc"].inverse_transform(I[0])

    items = []
    for pid in item_ids[:n]:
        row  = state["products"].loc[pid] if pid in state["products"].index else None
        items.append({
            "product_id":   int(pid),
            "product_name": str(row["product_name"]) if row is not None else "Unknown",
            "department":   str(row["department"])   if row is not None else "Unknown",
        })

    log_ab_impression(user_id, variant, items)
    REQUEST_LATENCY.labels(endpoint="/recommend").observe(time.time() - t0)
    return {"user_id": user_id, "variant": variant, "items": items}


@app.post("/ask", response_model=AskResponse)
def ask(body: AskRequest):
    t0 = time.time()
    REQUEST_COUNT.labels(endpoint="/ask").inc()

    col     = state["chroma"].get_or_create_collection("product_catalog")
    results = col.query(query_texts=[body.question], n_results=5)
    docs    = results["documents"][0]
    context = "\n\n".join(docs)

    response = state["claude"].messages.create(
        model="claude-opus-4-8",
        max_tokens=1024,
        thinking={"type": "adaptive"},
        messages=[{"role": "user", "content":
            f"You are a retail analytics assistant. Answer using only the catalog data below.\n\n"
            f"CATALOG:\n{context}\n\nQUESTION: {body.question}"
        }],
    )
    answer = next(b.text for b in reversed(response.content) if b.type == "text")
    REQUEST_LATENCY.labels(endpoint="/ask").observe(time.time() - t0)
    return {"question": body.question, "answer": answer, "sources": docs}


@app.get("/kpis")
def kpis(days: int = Query(7, ge=1, le=90)):
    REQUEST_COUNT.labels(endpoint="/kpis").inc()
    con  = duckdb.connect(DUCKDB_PATH, read_only=True)
    rows = con.execute(f"""
        SELECT kpi_date::varchar AS kpi_date, total_orders, unique_customers, total_units,
               total_revenue, avg_basket_size, revenue_wow_pct, is_revenue_spike
        FROM main_mart.mart_executive_kpis
        ORDER BY kpi_date DESC
        LIMIT {days}
    """).fetchdf()
    con.close()
    return rows.to_dict(orient="records")


@app.get("/agent/run")
def agent_run():
    REQUEST_COUNT.labels(endpoint="/agent/run").inc()
    from models.llm.agent import run_monitoring_agent
    run_monitoring_agent()
    con  = duckdb.connect(DUCKDB_PATH, read_only=True)
    row  = con.execute("""
        SELECT report_id::varchar, created_at::varchar, report
        FROM main_mart.agent_reports ORDER BY created_at DESC LIMIT 1
    """).fetchdf()
    con.close()
    if row.empty:
        raise HTTPException(status_code=500, detail="Agent produced no report")
    return row.to_dict(orient="records")[0]


@app.get("/agent/reports")
def agent_reports(limit: int = Query(10, ge=1, le=100)):
    REQUEST_COUNT.labels(endpoint="/agent/reports").inc()
    con  = duckdb.connect(DUCKDB_PATH, read_only=True)
    rows = con.execute(f"""
        SELECT report_id::varchar, created_at::varchar, report
        FROM main_mart.agent_reports ORDER BY created_at DESC LIMIT {limit}
    """).fetchdf()
    con.close()
    return rows.to_dict(orient="records")


@app.get("/ab-test/results")
def ab_test_results():
    REQUEST_COUNT.labels(endpoint="/ab-test/results").inc()
    con = duckdb.connect(DUCKDB_PATH, read_only=True)
    try:
        rows = con.execute("""
            SELECT variant,
                   COUNT(*)            AS impressions,
                   AVG(items_shown)    AS avg_items_shown,
                   SUM(clicked)        AS total_clicks,
                   SUM(converted)      AS total_conversions
            FROM main_mart.ab_test_log
            GROUP BY variant
        """).fetchdf()
    except Exception:
        rows = None
    con.close()
    if rows is None or rows.empty:
        return {"message": "No A/B test data yet. Call /recommend first."}
    return rows.to_dict(orient="records")
