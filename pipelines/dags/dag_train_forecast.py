from airflow import DAG
from airflow.operators.bash import BashOperator
from datetime import datetime, timedelta

default_args = {
    "owner": "retail-platform",
    "retries": 1,
    "retry_delay": timedelta(minutes=10),
}

with DAG(
    dag_id="dag_train_forecast",
    description="Build features and retrain LightGBM Tweedie forecaster",
    schedule="0 4 * * 1",
    start_date=datetime(2024, 1, 1),
    catchup=False,
    default_args=default_args,
    tags=["ml", "forecasting"],
) as dag:

    build_features = BashOperator(
        task_id="build_features",
        bash_command="cd /opt/retail-intelligence-platform && source venv/bin/activate && python models/forecasting/build_features.py",
    )

    train_model = BashOperator(
        task_id="train_model",
        bash_command="cd /opt/retail-intelligence-platform && source venv/bin/activate && python models/forecasting/train_forecaster.py",
    )

    shap_explain = BashOperator(
        task_id="shap_explain",
        bash_command="cd /opt/retail-intelligence-platform && source venv/bin/activate && python models/forecasting/shap_explainer.py",
    )

    build_features >> train_model >> shap_explain
