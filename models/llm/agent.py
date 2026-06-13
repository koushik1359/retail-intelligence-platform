import duckdb
import json
import os
import re
import chromadb
from datetime import datetime
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

DUCKDB_PATH = os.getenv("DUCKDB_PATH", "data/warehouse.duckdb")
client      = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


# ── Input validation — prevents SQL injection ──────────────────────────────────

def _safe_id(value: str) -> str:
    if not re.match(r'^[A-Za-z0-9_\-]+$', value):
        raise ValueError(f"Invalid identifier: {value!r}")
    return value

def _safe_date(value: str) -> str:
    datetime.strptime(value, "%Y-%m-%d")
    return value


# ── Tool implementations ───────────────────────────────────────────────────────

def query_kpis(time_window: str, store_id: str = "all", category: str = "all") -> dict:
    con = duckdb.connect(DUCKDB_PATH, read_only=True)
    window_map = {"1h": 1, "4h": 1, "24h": 1, "7d": 7}
    days = window_map.get(time_window, 1)

    store_filter    = f"AND store_id = '{_safe_id(store_id)}'"    if store_id != "all" else ""
    category_filter = f"AND dept_id = '{_safe_id(category)}'"    if category != "all" else ""

    rows = con.execute(f"""
        SELECT
            SUM(total_revenue)       AS total_revenue,
            SUM(total_units)         AS total_units,
            AVG(avg_price)           AS avg_price,
            COUNT(DISTINCT store_id) AS active_stores,
            MAX(sale_date)           AS latest_date
        FROM main_mart.fct_daily_demand
        WHERE sale_date >= (SELECT MAX(sale_date) - INTERVAL '{days} days'
                            FROM main_mart.fct_daily_demand)
        {store_filter} {category_filter}
    """).fetchdf()

    top = con.execute(f"""
        SELECT dept_id, SUM(total_revenue) AS revenue
        FROM main_mart.fct_daily_demand
        WHERE sale_date >= (SELECT MAX(sale_date) - INTERVAL '{days} days'
                            FROM main_mart.fct_daily_demand)
        {store_filter}
        GROUP BY 1 ORDER BY 2 DESC LIMIT 5
    """).fetchdf()

    bottom = con.execute(f"""
        SELECT dept_id, SUM(total_revenue) AS revenue
        FROM main_mart.fct_daily_demand
        WHERE sale_date >= (SELECT MAX(sale_date) - INTERVAL '{days} days'
                            FROM main_mart.fct_daily_demand)
        {store_filter}
        GROUP BY 1 ORDER BY 2 ASC LIMIT 5
    """).fetchdf()
    con.close()

    return {
        "time_window":       time_window,
        "store_id":          store_id,
        "summary":           rows.to_dict(orient="records")[0] if not rows.empty else {},
        "top_departments":   top.to_dict(orient="records"),
        "bottom_departments": bottom.to_dict(orient="records"),
    }


def get_forecast_vs_actual(date: str, store_id: str = "all", top_n: int = 10) -> dict:
    con  = duckdb.connect(DUCKDB_PATH, read_only=True)
    date = _safe_date(date)
    filt = f"AND store_id = '{_safe_id(store_id)}'" if store_id != "all" else ""
    rows = con.execute(f"""
        SELECT
            store_id,
            dept_id,
            sale_date,
            total_units                         AS actual_units,
            total_revenue                       AS actual_revenue,
            units_28d_avg                       AS forecast_proxy,
            CASE WHEN units_28d_avg > 0
                 THEN ABS(total_units - units_28d_avg) / units_28d_avg * 100
            END                                 AS mape_pct
        FROM main_mart.fct_daily_demand
        WHERE sale_date = ? {filt}
        ORDER BY mape_pct DESC NULLS LAST
        LIMIT ?
    """, [date, top_n]).fetchdf()
    con.close()
    if rows.empty:
        return {"date": date, "message": "No data for this date", "items": []}
    avg_mape = float(rows["mape_pct"].dropna().mean())
    return {
        "date":            date,
        "avg_mape_pct":    round(avg_mape, 2),
        "top_deviations":  rows.to_dict(orient="records"),
    }


def get_inventory_status(store_id: str, threshold_days: float = 2.0) -> dict:
    con  = duckdb.connect(DUCKDB_PATH, read_only=True)
    filt = f"WHERE store_id = '{_safe_id(store_id)}'" if store_id != "all" else ""
    rows = con.execute(f"""
        WITH latest AS (
            SELECT
                store_id, dept_id, sale_date, total_units, units_28d_avg,
                CASE WHEN units_28d_avg > 0
                     THEN total_units / units_28d_avg
                END AS days_of_stock_proxy,
                ROW_NUMBER() OVER (
                    PARTITION BY store_id, dept_id ORDER BY sale_date DESC
                ) AS rn
            FROM main_mart.fct_daily_demand
            {filt}
        )
        SELECT store_id, dept_id, sale_date, total_units, units_28d_avg, days_of_stock_proxy
        FROM latest
        WHERE rn = 1 AND days_of_stock_proxy < ?
        ORDER BY days_of_stock_proxy ASC
        LIMIT 20
    """, [threshold_days]).fetchdf()
    con.close()
    return {
        "store_id":       store_id,
        "threshold_days": threshold_days,
        "at_risk_count":  len(rows),
        "at_risk_items":  rows.to_dict(orient="records"),
    }


def search_catalog(query: str, n_results: int = 5) -> dict:
    chroma  = chromadb.PersistentClient(path="data/chromadb")
    col     = chroma.get_or_create_collection("product_catalog")
    results = col.query(query_texts=[query], n_results=n_results)
    items   = []
    for i, doc in enumerate(results["documents"][0]):
        meta = results["metadatas"][0][i] if results["metadatas"] else {}
        items.append({"document": doc, "metadata": meta,
                      "distance": results["distances"][0][i]})
    return {"query": query, "results": items}


def generate_alert(severity: str, title: str, message: str,
                   recommended_action: str) -> dict:
    con = duckdb.connect(DUCKDB_PATH)
    con.execute("""
        CREATE TABLE IF NOT EXISTS main_mart.agent_alerts (
            alert_id           VARCHAR DEFAULT gen_random_uuid(),
            created_at         TIMESTAMP DEFAULT now(),
            severity           VARCHAR,
            title              VARCHAR,
            message            VARCHAR,
            recommended_action VARCHAR
        )
    """)
    con.execute("""
        INSERT INTO main_mart.agent_alerts
            (severity, title, message, recommended_action)
        VALUES (?, ?, ?, ?)
    """, [severity, title, message, recommended_action])
    con.close()
    return {"status": "alert_posted", "severity": severity, "title": title}


def save_report(report: str) -> None:
    con = duckdb.connect(DUCKDB_PATH)
    con.execute("""
        CREATE TABLE IF NOT EXISTS main_mart.agent_reports (
            report_id  VARCHAR DEFAULT gen_random_uuid(),
            created_at TIMESTAMP DEFAULT now(),
            report     VARCHAR
        )
    """)
    con.execute("INSERT INTO main_mart.agent_reports (report) VALUES (?)", [report])
    con.close()
    print("\n" + "="*60)
    print("AGENT REPORT SAVED")
    print("="*60)
    print(report)


# ── Tool dispatcher ────────────────────────────────────────────────────────────

def execute_tool(name: str, inputs: dict) -> dict:
    if name == "query_kpis":
        return query_kpis(**inputs)
    elif name == "get_forecast_vs_actual":
        return get_forecast_vs_actual(**inputs)
    elif name == "get_inventory_status":
        return get_inventory_status(**inputs)
    elif name == "search_catalog":
        return search_catalog(**inputs)
    elif name == "generate_alert":
        return generate_alert(**inputs)
    return {"error": f"Unknown tool: {name}"}


# ── Tool schemas (OpenAI format) ───────────────────────────────────────────────

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "query_kpis",
            "description": "Query real-time KPIs from the data warehouse. Returns revenue, units sold, avg price, and top/bottom performing departments for a given time window.",
            "parameters": {
                "type": "object",
                "properties": {
                    "time_window": {"type": "string", "enum": ["1h", "4h", "24h", "7d"]},
                    "store_id":    {"type": "string", "description": "Store ID or 'all'"},
                    "category":    {"type": "string", "description": "Department ID or 'all'"},
                },
                "required": ["time_window"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_forecast_vs_actual",
            "description": "Compare demand forecast (28-day rolling baseline) to actual sales. Returns MAPE and top deviating store-department pairs.",
            "parameters": {
                "type": "object",
                "properties": {
                    "date":     {"type": "string", "description": "Date in YYYY-MM-DD format"},
                    "store_id": {"type": "string"},
                    "top_n":    {"type": "integer"},
                },
                "required": ["date"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_inventory_status",
            "description": "Check current stock levels and flag departments at risk of stockout based on sales velocity vs rolling average.",
            "parameters": {
                "type": "object",
                "properties": {
                    "store_id":       {"type": "string"},
                    "threshold_days": {"type": "number", "description": "Flag items with < N days of stock remaining"},
                },
                "required": ["store_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_catalog",
            "description": "Search the product catalog using semantic similarity to find related products or substitutes.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query":     {"type": "string"},
                    "n_results": {"type": "integer"},
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "generate_alert",
            "description": "Post a formatted alert to the operations dashboard when an anomaly requires human attention.",
            "parameters": {
                "type": "object",
                "properties": {
                    "severity":           {"type": "string", "enum": ["low", "medium", "high", "critical"]},
                    "title":              {"type": "string"},
                    "message":            {"type": "string"},
                    "recommended_action": {"type": "string"},
                },
                "required": ["severity", "title", "message", "recommended_action"],
            },
        },
    },
]


# ── Agentic loop ───────────────────────────────────────────────────────────────

def run_monitoring_agent():
    print("Starting retail monitoring agent...")
    messages = [
        {
            "role": "system",
            "content": (
                "You are a retail operations AI monitoring a large retail chain. "
                "Be thorough but efficient. Use your tools to gather data, then write a report."
            ),
        },
        {
            "role": "user",
            "content": (
                "Your job is to:\n"
                "1. Check KPIs for the last 7 days across all stores\n"
                "2. Check forecast accuracy for the most recent available date\n"
                "3. Check inventory status for stores CA_1 and TX_1\n"
                "4. If you find any anomalies or concerning trends, generate an alert\n"
                "5. Search the catalog for any products relevant to the anomalies you find\n"
                "6. Write a concise operations report: what you found, what actions you recommend"
            ),
        },
    ]

    while True:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            max_tokens=4096,
            tools=TOOLS,
            messages=messages,
        )

        choice = response.choices[0]
        print(f"\n[Agent] finish_reason={choice.finish_reason}")

        if choice.finish_reason == "stop":
            save_report(choice.message.content)
            break

        if choice.finish_reason == "tool_calls":
            messages.append({
                "role":       "assistant",
                "content":    choice.message.content,
                "tool_calls": [
                    {
                        "id":       tc.id,
                        "type":     "function",
                        "function": {"name": tc.function.name, "arguments": tc.function.arguments},
                    }
                    for tc in choice.message.tool_calls
                ],
            })

            for tc in choice.message.tool_calls:
                inputs = json.loads(tc.function.arguments)
                print(f"  → calling {tc.function.name}({json.dumps(inputs)[:120]})")
                result = execute_tool(tc.function.name, inputs)
                messages.append({
                    "role":         "tool",
                    "tool_call_id": tc.id,
                    "content":      json.dumps(result, default=str),
                })


if __name__ == "__main__":
    run_monitoring_agent()
