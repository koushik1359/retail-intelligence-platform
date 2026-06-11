from airflow import DAG
from airflow.operators.bash import BashOperator
from datetime import datetime, timedelta

default_args = {
    "owner": "retail-platform",
    "retries": 2,
    "retry_delay": timedelta(minutes=3),
}

with DAG(
    dag_id="dag_enrich_catalog",
    description="Enrich product catalog with Claude Haiku and index into ChromaDB",
    schedule="0 5 * * 1",
    start_date=datetime(2024, 1, 1),
    catchup=False,
    default_args=default_args,
    tags=["llm", "catalog", "chromadb"],
) as dag:

    enrich_catalog = BashOperator(
        task_id="enrich_catalog",
        bash_command="cd /opt/retail-intelligence-platform && source venv/bin/activate && python pipelines/catalog_enrichment.py",
    )

    build_chroma = BashOperator(
        task_id="build_chromadb",
        bash_command="cd /opt/retail-intelligence-platform && source venv/bin/activate && python pipelines/build_chromadb.py",
    )

    enrich_catalog >> build_chroma
