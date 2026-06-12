import anthropic
import duckdb
import json
import os
import chromadb
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()

DUCKDB_PATH = os.getenv("DUCKDB_PATH", "data/warehouse.duckdb")
client      = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))


# ── Tool implementations ───────────────────────────────────────────────────────

def query_kpis(time_window: str, store_id: str = "all", category: str = "all") -> dict:
    con = duckdb.connect(DUCKDB_PATH, read_only=True)
    window_map = {"1h": 1, "4h": 1, "24h": 1, "7d": 7}
    days = window_map.get(time_window, 1)
    store_filter    = f"AND store_id = '{store_id}'" if store_id != "all" else ""
    category_filter = f"AND dept_id = '{category}'" if category != "all" else ""

    rows = con.execute(f"""
        SELECT
            SUM(total_revenue)                          AS total_revenue,
            SUM(total_units)                            AS total_units,
            AVG(avg_price)                              AS avg_price,
            COUNT(DISTINCT store_id)                    AS active_stores,
            MAX(sale_date)                              AS latest_date
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
        "time_window": time_window,
        "store_id": store_id,
        "summary": rows.to_dict(orient="records")[0] if not rows.empty else {},
        "top_departments": top.to_dict(orient="records"),
        "bottom_departments": bottom.to_dict(orient="records"),
    }


def get_forecast_vs_actual(date: str, store_id: str = "all", top_n: int = 10) -> dict:
    con  = duckdb.connect(DUCKDB_PATH, read_only=True)
    filt = f"AND store_id = '{store_id}'" if store_id != "all" else ""
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
        WHERE sale_date = '{date}' {filt}
        ORDER BY mape_pct DESC NULLS LAST
        LIMIT {top_n}
    """).fetchdf()
    con.close()
    if rows.empty:
        return {"date": date, "message": "No data for this date", "items": []}
    avg_mape = float(rows["mape_pct"].dropna().mean())
    return {
        "date": date,
        "avg_mape_pct": round(avg_mape, 2),
        "top_deviations": rows.to_dict(orient="records"),
    }


def get_inventory_status(store_id: str, threshold_days: float = 2.0) -> dict:
    con  = duckdb.connect(DUCKDB_PATH, read_only=True)
    filt = f"WHERE store_id = '{store_id}'" if store_id != "all" else ""
    rows = con.execute(f"""
        WITH latest AS (
            SELECT
                store_id,
                dept_id,
                sale_date,
                total_units,
                units_28d_avg,
                CASE WHEN units_28d_avg > 0
                     THEN total_units / units_28d_avg
                END AS days_of_stock_proxy,
                ROW_NUMBER() OVER (
                    PARTITION BY store_id, dept_id
                    ORDER BY sale_date DESC
                ) AS rn
            FROM main_mart.fct_daily_demand
            {filt}
        )
        SELECT store_id, dept_id, sale_date, total_units, units_28d_avg, days_of_stock_proxy
        FROM latest
        WHERE rn = 1
          AND days_of_stock_proxy < {threshold_days}
        ORDER BY days_of_stock_proxy ASC
        LIMIT 20
    """).fetchdf()

    con.close()
    return {
        "store_id": store_id,
        "threshold_days": threshold_days,
        "at_risk_count": len(rows),
        "at_risk_items": rows.to_dict(orient="records"),
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
            alert_id      VARCHAR DEFAULT gen_random_uuid(),
            created_at    TIMESTAMP DEFAULT now(),
            severity      VARCHAR,
            title         VARCHAR,
            message       VARCHAR,
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


# ── Tool schemas ───────────────────────────────────────────────────────────────

TOOLS = [
    {
        "name": "query_kpis",
        "description": "Query real-time KPIs from the data warehouse. Returns revenue, units sold, avg price, and top/bottom performing departments for a given time window.",
        "input_schema": {
            "type": "object",
            "properties": {
                "time_window": {"type": "string", "enum": ["1h", "4h", "24h", "7d"]},
                "store_id":    {"type": "string", "description": "Store ID or 'all'"},
                "category":    {"type": "string", "description": "Department ID or 'all'"},
            },
            "required": ["time_window"],
        },
    },
    {
        "name": "get_forecast_vs_actual",
        "description": "Compare demand forecast (28-day rolling baseline) to actual sales. Returns MAPE and top deviating store-department pairs.",
        "input_schema": {
            "type": "object",
            "properties": {
                "date":     {"type": "string", "description": "Date in YYYY-MM-DD format"},
                "store_id": {"type": "string"},
                "top_n":    {"type": "integer", "default": 10},
            },
            "required": ["date"],
        },
    },
    {
        "name": "get_inventory_status",
        "description": "Check current stock levels and flag departments at risk of stockout based on sales velocity vs rolling average.",
        "input_schema": {
            "type": "object",
            "properties": {
                "store_id":       {"type": "string"},
                "threshold_days": {"type": "number", "description": "Flag items with < N days of stock remaining"},
            },
            "required": ["store_id"],
        },
    },
    {
        "name": "search_catalog",
        "description": "Search the product catalog using semantic similarity to find related products or substitutes.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query":     {"type": "string"},
                "n_results": {"type": "integer", "default": 5},
            },
            "required": ["query"],
        },
    },
    {
        "name": "generate_alert",
        "description": "Post a formatted alert to the operations dashboard when an anomaly requires human attention.",
        "input_schema": {
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
]


# ── Agentic loop ───────────────────────────────────────────────────────────────

def run_monitoring_agent():
    print("Starting retail monitoring agent...")
    messages = [{
        "role": "user",
        "content": (
            "You are a retail operations AI monitoring a large retail chain. "
            "Your job is to:\n"
            "1. Check KPIs for the last 7 days across all stores\n"
            "2. Check forecast accuracy for the most recent available date\n"
            "3. Check inventory status for stores CA_1 and TX_1\n"
            "4. If you find any anomalies or concerning trends, generate an alert\n"
            "5. Search the catalog for any products relevant to the anomalies you find\n"
            "6. Write a concise operations report: what you found, what actions you recommend\n\n"
            "Use your tools to gather data. Be thorough but efficient."
        ),
    }]

    while True:
        response = client.messages.create(
            model="claude-haiku-4-5",
            max_tokens=4096,
            tools=TOOLS,
            messages=messages,
        )

        print(f"\n[Agent] stop_reason={response.stop_reason}  "
              f"blocks={[b.type for b in response.content]}")

        if response.stop_reason == "end_turn":
            report = next(
                (b.text for b in reversed(response.content) if b.type == "text"),
                "No report generated."
            )
            save_report(report)
            break

        if response.stop_reason == "tool_use":
            messages.append({"role": "assistant", "content": response.content})
            tool_results = []
            for block in response.content:
                if block.type == "tool_use":
                    print(f"  → calling {block.name}({json.dumps(block.input)[:120]})")
                    result = execute_tool(block.name, block.input)
                    tool_results.append({
                        "type":        "tool_result",
                        "tool_use_id": block.id,
                        "content":     json.dumps(result, default=str),
                    })
            messages.append({"role": "user", "content": tool_results})


if __name__ == "__main__":
    run_monitoring_agent()
