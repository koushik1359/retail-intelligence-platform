import pandas as pd
import numpy as np
import lightgbm as lgb
import shap
import mlflow
import matplotlib.pyplot as plt
import os
from sklearn.preprocessing import LabelEncoder
from dotenv import load_dotenv

load_dotenv()

MLFLOW_URI   = os.getenv("MLFLOW_TRACKING_URI", "http://localhost:5001")
FEATURE_PATH = "data/processed/m5_item_features.parquet"
MODEL_PATH   = "models/forecasting/artifacts/lgb_tweedie_fold_3.txt"
OUT_PATH     = "models/forecasting/artifacts/shap_feature_importance.png"

mlflow.set_tracking_uri(MLFLOW_URI)

print("Loading features...")
df = pd.read_parquet(FEATURE_PATH)

cat_cols = ["item_id", "store_id", "dept_id", "cat_id", "state_id"]
for col in cat_cols:
    le = LabelEncoder()
    df[col] = le.fit_transform(df[col].astype(str))

FEATURE_COLS = [c for c in df.columns if c not in
                ["sale_date", "unit_sales", "sell_price",
                 "snap_CA", "snap_TX", "snap_WI", "_store", "_item"]]

print("Loading champion model (fold 3)...")
model = lgb.Booster(model_file=MODEL_PATH)

print("Sampling 5,000 rows for SHAP...")
sample = df[FEATURE_COLS].sample(5000, random_state=42)

print("Computing SHAP values (TreeExplainer)...")
explainer   = shap.TreeExplainer(model)
shap_values = explainer.shap_values(sample)

mean_abs_shap = np.abs(shap_values).mean(axis=0)
importance_df = (
    pd.DataFrame({"feature": FEATURE_COLS, "mean_abs_shap": mean_abs_shap})
    .sort_values("mean_abs_shap", ascending=False)
    .head(20)
)

print("\nTop 20 features by SHAP:")
print(importance_df.to_string(index=False))

fig, ax = plt.subplots(figsize=(10, 7))
ax.barh(importance_df["feature"][::-1], importance_df["mean_abs_shap"][::-1])
ax.set_xlabel("Mean |SHAP value|")
ax.set_title("Top 20 Feature Importances (SHAP) — LightGBM Demand Forecaster")
plt.tight_layout()
plt.savefig(OUT_PATH, dpi=150)
plt.close()
print(f"\nSaved plot to {OUT_PATH}")

client = mlflow.tracking.MlflowClient()
champion = client.get_model_version_by_alias("demand_forecaster", "champion")
run_id   = champion.run_id

with mlflow.start_run(run_id=run_id):
    mlflow.log_artifact(OUT_PATH, artifact_path="shap")
    mlflow.log_dict(
        {row.feature: round(row.mean_abs_shap, 6) for _, row in importance_df.iterrows()},
        "shap/top20_shap_values.json"
    )

print(f"Logged SHAP artifacts to MLflow run {run_id}")
