# Retail Intelligence Platform

An end-to-end ML + LLM system covering demand forecasting, product recommendations, real-time transaction streaming, and natural-language catalog search — served through a FastAPI backend and a Streamlit dashboard.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                         Data Sources                                │
│  M5 Forecasting  ·  Instacart Orders  ·  Online Retail II  ·  Amazon│
└──────────┬──────────────────────────────────────────────────────────┘
           │ Parquet / DuckDB ingestion
           ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    Data Warehouse  (DuckDB)                         │
│   raw.*  ──▶  dbt transforms  ──▶  main_mart.*                     │
│   fct_daily_sales · fct_product_performance · dim_products          │
└──────────┬──────────────────────────────────────────────────────────┘
           │
    ┌──────┴──────┐
    │             │
    ▼             ▼
┌───────┐   ┌──────────────────────────────────────┐
│ ML    │   │  Kafka  (Redpanda)                    │
│ layer │   │  raw.transactions ──▶ stream_processor│
│       │   │  ──▶ enriched.transactions            │
│ ·LGB  │   │  ──▶ alerts.inventory / revenue       │
│ ·ALS  │   └──────────────────────────────────────┘
│ ·UMAP │
│ ·FAISS│   ┌──────────────────────────────────────┐
└───┬───┘   │  LLM layer  (Claude Opus 4.8)         │
    │       │  · Catalog enrichment  (ChromaDB RAG) │
    │       │  · Executive summary  (adaptive think)│
    │       │  · Agentic analyst  (5 custom tools)  │
    └───────┴───────────┬──────────────────────────┘
                        │
                        ▼
              ┌─────────────────┐
              │  FastAPI :8000  │
              │  /forecast      │
              │  /recommend     │
              │  /ask           │
              │  /executive-... │
              │  /ab-test/...   │
              └────────┬────────┘
                       │
                       ▼
            ┌──────────────────┐
            │ Streamlit :8501  │
            │ Executive Ovrvw  │
            │ Demand Forecast  │
            │ Recommendations  │
            │ Catalog Q&A      │
            │ Live Transactions│
            └──────────────────┘
```

---

## Tech Stack

| Layer | Tools |
|---|---|
| Data warehouse | DuckDB + dbt |
| Orchestration | Apache Airflow |
| Forecasting | LightGBM Tweedie · 3-fold time-series CV · MLflow |
| Recommendations | ALS (implicit) · FAISS · UMAP · A/B hash routing |
| Streaming | Kafka (Redpanda) · kafka-python |
| LLM / RAG | Claude Opus 4.8 · ChromaDB · MiniLM-L6-v2 |
| API | FastAPI + Uvicorn |
| Dashboard | Streamlit · Plotly |
| Data quality | Great Expectations |
| CI | GitHub Actions |

---

## Datasets

| Dataset | Purpose | Records |
|---|---|---|
| M5 Forecasting (Walmart) | Demand forecasting | 58M daily sales rows |
| Instacart Online Grocery | ALS recommendations | 3.4M orders · 49,685 products |
| Online Retail II (UCI) | Kafka streaming simulation | 1M transactions |
| Amazon Product Catalog | Catalog enrichment / RAG | ~500K product descriptions |

---

## Setup

### Prerequisites

- Python 3.12
- [Redpanda](https://redpanda.com/redpanda-console-ui) (Kafka-compatible broker) running on `localhost:9092`
- Anthropic API key
- OpenAI API key (embeddings only)

### Install

```bash
git clone https://github.com/your-username/retail-intelligence-platform.git
cd retail-intelligence-platform

python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate     # macOS / Linux

pip install -r requirements.txt
```

### Configure

```bash
cp .env.example .env
# Fill in ANTHROPIC_API_KEY and OPENAI_API_KEY
```

### Data ingestion

```bash
# 1. Clean raw datasets (download from Kaggle first — see links below)
python data/clean_m5.py
python data/clean_instacart.py
python data/clean_online_retail.py
python data/clean_amazon.py

# 2. Load into DuckDB
python data/init_duckdb.py
python data/load_to_duckdb.py

# 3. Run dbt transforms
cd features && dbt run && dbt test && cd ..
```

### Train models

```bash
# Demand forecasting (LightGBM)
python models/forecasting/train_forecaster.py

# Recommendations (ALS + FAISS + UMAP)
python models/recommendations/train_recommender.py
python models/recommendations/build_faiss_index.py
python models/recommendations/umap_projection.py
```

### Build vector store

```bash
# Catalog enrichment + ChromaDB index
python pipelines/catalog_enrichment.py
python pipelines/build_vector_store.py
```

### Start services

```bash
# Terminal 1 — API
uvicorn api.main:app --reload --port 8000

# Terminal 2 — Dashboard
cd dashboard && streamlit run app.py

# Terminal 3 — Kafka producer (replays Online Retail II)
python pipelines/kafka/transaction_producer.py

# Terminal 4 — Stream processor (enriches & routes to topics)
python pipelines/kafka/stream_processor.py

# Terminal 5 — Alert consumer (optional)
python pipelines/kafka/alert_consumer.py
```

---

## Dashboard Pages

| Page | Description |
|---|---|
| Executive Overview | KPI cards, revenue trend, top stores, Claude-generated weekly narrative |
| Demand Forecast | LightGBM 28-day forecast by store/item with ±20% confidence band |
| Recommendations | ALS top-N recs, UMAP embedding scatter, A/B variant badge |
| Catalog Q&A | Natural-language product search (RAG + Claude Opus 4.8) |
| Live Transactions | Real-time Kafka feed — revenue by country, top-seller mix donut |

---

## API Endpoints

```
GET  /forecast          ?store_id=CA_1&item_id=FOODS_3_001&horizon=28
GET  /recommend         ?user_id=42&n=10
POST /ask               {"question": "Best snacks for kids?"}
GET  /executive-summary
GET  /ab-test/results
GET  /health
```

---

## Project Structure

```
retail-intelligence-platform/
├── api/                    FastAPI app (main.py + schemas.py)
├── dashboard/              Streamlit pages + shared style system
│   ├── app.py
│   ├── style.py
│   └── pages/
├── data/                   Ingestion + cleaning scripts
├── features/               dbt project (models, tests, docs)
├── models/
│   ├── forecasting/        LightGBM train + predict + SHAP
│   ├── recommendations/    ALS + FAISS + UMAP
│   └── llm/                Claude agent + executive summary
├── monitoring/             Prometheus config + Grafana dashboard JSON
├── notebooks/              EDA for each dataset
├── pipelines/
│   ├── dags/               Airflow DAGs (4 pipelines)
│   ├── kafka/              Producer · Processor · Alert consumer
│   ├── catalog_enrichment.py
│   └── build_vector_store.py
├── tests/                  pytest + Great Expectations
├── .github/workflows/      CI (dbt test + pytest on push)
├── docker-compose.yml      Redpanda + MLflow
├── requirements.txt
└── .env.example
```

---

## Running Tests

```bash
pytest tests/ -v
```

---

## Dataset Sources

- [M5 Forecasting](https://www.kaggle.com/competitions/m5-forecasting-accuracy/data)
- [Instacart Online Grocery](https://www.kaggle.com/datasets/psparks/instacart-market-basket-analysis)
- [Online Retail II](https://www.kaggle.com/datasets/mashlyn/online-retail-ii-uci)
- [Amazon Product Catalog](https://www.kaggle.com/datasets/piyushjain16/amazon-product-data)
