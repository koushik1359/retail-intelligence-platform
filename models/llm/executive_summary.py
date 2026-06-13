import duckdb
import json
import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

DUCKDB_PATH = os.getenv("DUCKDB_PATH", "data/warehouse.duckdb")
client      = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def get_weekly_kpis() -> dict:
    con = duckdb.connect(DUCKDB_PATH, read_only=True)

    summary = con.execute("""
        WITH latest_week AS (
            SELECT *
            FROM main_mart.mart_executive_kpis
            WHERE kpi_date >= (SELECT MAX(kpi_date) - INTERVAL '7 days'
                               FROM main_mart.mart_executive_kpis)
        ),
        prior_week AS (
            SELECT *
            FROM main_mart.mart_executive_kpis
            WHERE kpi_date >= (SELECT MAX(kpi_date) - INTERVAL '14 days'
                               FROM main_mart.mart_executive_kpis)
              AND kpi_date <  (SELECT MAX(kpi_date) - INTERVAL '7 days'
                               FROM main_mart.mart_executive_kpis)
        )
        SELECT
            ROUND(SUM(l.total_revenue), 2)          AS revenue_this_week,
            ROUND(SUM(p.total_revenue), 2)          AS revenue_last_week,
            SUM(l.total_orders)                     AS orders_this_week,
            SUM(p.total_orders)                     AS orders_last_week,
            SUM(l.unique_customers)                 AS customers_this_week,
            ROUND(AVG(l.avg_basket_size), 2)        AS avg_basket_size,
            COUNT(CASE WHEN l.is_revenue_spike THEN 1 END) AS spike_days
        FROM latest_week l
        CROSS JOIN (SELECT SUM(total_revenue) AS total_revenue,
                           SUM(total_orders)  AS total_orders
                    FROM prior_week) p
    """).fetchdf()

    top_products = con.execute("""
        SELECT product_name, total_revenue, total_units_sold, revenue_rank
        FROM main_mart.fct_product_performance
        ORDER BY revenue_rank
        LIMIT 10
    """).fetchdf()

    agent_reports = con.execute("""
        SELECT report, created_at
        FROM main_mart.agent_reports
        ORDER BY created_at DESC
        LIMIT 1
    """).fetchdf()

    con.close()

    kpis = summary.to_dict(orient="records")[0] if not summary.empty else {}
    kpis["top_products"]        = top_products.to_dict(orient="records")
    kpis["latest_agent_report"] = (
        agent_reports.iloc[0]["report"] if not agent_reports.empty else "No report yet."
    )
    return kpis


def generate_weekly_summary() -> str:
    print("Fetching KPIs from DuckDB...")
    kpis = get_weekly_kpis()

    print("Generating executive summary with GPT-4o-mini...")
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        max_tokens=1500,
        timeout=30,
        messages=[
            {
                "role": "system",
                "content": "You are a senior retail analyst. Be direct, concise, and data-driven.",
            },
            {
                "role": "user",
                "content": (
                    "Generate a weekly retail performance summary for a VP of Merchandising.\n\n"
                    "Use bullet points. Highlight anomalies. Recommend 3 specific actions.\n"
                    "Format: Executive Summary header, KPI Highlights, Anomalies & Risks, "
                    "3 Recommended Actions.\n\n"
                    f"KPI DATA:\n{json.dumps(kpis, indent=2, default=str)}"
                ),
            },
        ],
    )

    return response.choices[0].message.content


if __name__ == "__main__":
    summary = generate_weekly_summary()
    print("\n" + "="*60)
    print(summary)
    print("="*60)
