from airflow import DAG
from airflow.operators.bash import BashOperator
from datetime import datetime, timedelta

default_args = {
    "owner": "retail-platform",
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
}

with DAG(
    dag_id="dag_ingest_raw",
    description="Ingest raw datasets into DuckDB",
    schedule="0 2 * * *",
    start_date=datetime(2024, 1, 1),
    catchup=False,
    default_args=default_args,
    tags=["ingestion", "raw"],
) as dag:

    ingest_online_retail = BashOperator(
        task_id="ingest_online_retail",
        bash_command="cd /opt/retail-intelligence-platform && source venv/bin/activate && python pipelines/load_online_retail.py",
    )

    ingest_m5 = BashOperator(
        task_id="ingest_m5",
        bash_command="cd /opt/retail-intelligence-platform && source venv/bin/activate && python pipelines/load_m5.py",
    )

    ingest_instacart = BashOperator(
        task_id="ingest_instacart",
        bash_command="cd /opt/retail-intelligence-platform && source venv/bin/activate && python pipelines/load_instacart.py",
    )

    [ingest_online_retail, ingest_m5, ingest_instacart]
