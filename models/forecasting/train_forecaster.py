import pandas as pd
import numpy as np
import lightgbm as lgb
import mlflow
import os
from sklearn.metrics import mean_absolute_error
from sklearn.preprocessing import LabelEncoder
from dotenv import load_dotenv

load_dotenv()

MLFLOW_URI   = os.getenv("MLFLOW_TRACKING_URI", "http://localhost:5001")
FEATURE_PATH = "data/processed/m5_item_features.parquet"

mlflow.set_tracking_uri(MLFLOW_URI)
mlflow.set_experiment("demand_forecasting")

# ── Load features ──────────────────────────────────────────────────────────────
print("Loading item-level features...")
df = pd.read_parquet(FEATURE_PATH)
df["sale_date"] = pd.to_datetime(df["sale_date"])
print(f"Loaded {len(df):,} rows | {df['item_id'].nunique():,} items × {df['store_id'].nunique()} stores")

# ── Keep original IDs for metric (before label encoding) ──────────────────────
df["_store"] = df["store_id"]
df["_item"]  = df["item_id"]

# ── Encode categoricals ────────────────────────────────────────────────────────
cat_cols = ["item_id", "store_id", "dept_id", "cat_id", "state_id"]
for col in cat_cols:
    le = LabelEncoder()
    df[col] = le.fit_transform(df[col].astype(str))

FEATURE_COLS = [c for c in df.columns if c not in
                ["sale_date", "unit_sales", "sell_price",
                 "snap_CA", "snap_TX", "snap_WI", "_store", "_item"]]
TARGET = "unit_sales"
print(f"Features: {len(FEATURE_COLS)} | Target: {TARGET}")
print(f"Date range: {df['sale_date'].min().date()} → {df['sale_date'].max().date()}")


# ── M5-style per-series RMSSE ──────────────────────────────────────────────────
def rmsse_m5(df_full, val_df, val_pred, val_start):
    """
    Correct M5 RMSSE:
      - Scale denominator = mean|diff| using ALL data before val_start (full history).
      - Only series with scale >= 0.1 are included (active items with real demand).
      - RMSSE = mean(RMSE_series / scale_series) across active series.
    """
    pre_val = df_full[df_full["sale_date"] < val_start]

    # Scale: naive 1-day error per series across full pre-val history
    scale = (
        pre_val.groupby(["_store", "_item"])["unit_sales"]
        .apply(lambda s: float(np.mean(np.abs(np.diff(s.values)))))
        .rename("scale")
    )

    # Per-series RMSE on validation
    tmp = val_df[["_store", "_item", "unit_sales"]].copy()
    tmp["pred"] = val_pred
    rmse_s = (
        tmp.groupby(["_store", "_item"])
        .apply(lambda g: float(np.sqrt(np.mean((g["unit_sales"].values - g["pred"].values) ** 2))))
        .rename("rmse")
    )

    combined = pd.DataFrame({"rmse": rmse_s, "scale": scale}).dropna()
    # Exclude zero-/near-zero-demand items (sporadic items with no real signal)
    combined = combined[combined["scale"] >= 0.1]
    print(f"    → {len(combined):,} active series evaluated (scale ≥ 0.1)")
    return float((combined["rmse"] / combined["scale"]).mean())


def bias(y_true, y_pred):
    return float((y_pred - y_true).mean())


# ── LightGBM params ────────────────────────────────────────────────────────────
params = {
    "objective":              "tweedie",
    "tweedie_variance_power": 1.5,
    "metric":                 "rmse",
    "n_estimators":           1500,
    "learning_rate":          0.05,
    "num_leaves":             127,
    "max_depth":              -1,
    "min_child_samples":      20,
    "subsample":              0.8,
    "subsample_freq":         1,
    "colsample_bytree":       0.8,
    "reg_alpha":              0.1,
    "reg_lambda":             0.5,
    "random_state":           42,
    "n_jobs":                 -1,
    "verbose":                -1,
}

# ── 3-Fold Time-Series CV ──────────────────────────────────────────────────────
folds = [
    ("fold_1", "2015-06-01", "2015-09-01", "2015-09-01", "2015-12-01"),
    ("fold_2", "2015-06-01", "2015-12-01", "2015-12-01", "2016-03-01"),
    ("fold_3", "2015-06-01", "2016-01-01", "2016-01-01", "2016-05-22"),
]

cv_rmsse    = []
best_rmsse  = float("inf")
best_version = None

print("\n=== 3-Fold Time-Series Cross-Validation ===")

for fold_name, train_start, train_end, val_start, val_end in folds:
    train = df[(df["sale_date"] >= train_start) & (df["sale_date"] < train_end)]
    val   = df[(df["sale_date"] >= val_start)   & (df["sale_date"] < val_end)]

    X_train, y_train = train[FEATURE_COLS], train[TARGET]
    X_val,   y_val   = val[FEATURE_COLS],   val[TARGET]

    print(f"\n{fold_name}: train {train_start}→{train_end} ({len(train):,} rows)"
          f" | val {val_start}→{val_end} ({len(val):,} rows)")

    with mlflow.start_run(run_name=f"lgb_tweedie_{fold_name}"):
        mlflow.log_params({**params, "fold": fold_name,
                           "train_start": train_start, "train_end": train_end,
                           "val_start":   val_start,   "val_end":   val_end})

        model = lgb.LGBMRegressor(**params)
        model.fit(
            X_train, y_train,
            eval_set=[(X_val, y_val)],
            callbacks=[lgb.early_stopping(50, verbose=False),
                       lgb.log_evaluation(100)],
        )

        val_pred   = np.clip(model.predict(X_val),   0, None)
        train_pred = np.clip(model.predict(X_train), 0, None)

        print("  Computing M5 per-series RMSSE...")
        fold_rmsse = rmsse_m5(df, val, val_pred, pd.Timestamp(val_start))

        metrics = {
            "val_mae":   mean_absolute_error(y_val, val_pred),
            "val_rmsse": fold_rmsse,
            "val_bias":  bias(y_val.values, val_pred),
            "train_mae": mean_absolute_error(y_train, train_pred),
            "best_iter": model.best_iteration_,
        }
        mlflow.log_metrics(metrics)
        cv_rmsse.append(fold_rmsse)

        print(f"  val_mae={metrics['val_mae']:.4f}  val_rmsse={metrics['val_rmsse']:.4f}"
              f"  val_bias={metrics['val_bias']:.4f}  best_iter={metrics['best_iter']}")

        # Save + register
        os.makedirs("models/forecasting/artifacts", exist_ok=True)
        model_path = f"models/forecasting/artifacts/lgb_tweedie_{fold_name}.txt"
        model.booster_.save_model(model_path)
        mlflow.log_artifact(model_path, artifact_path="model")

        run_id = mlflow.active_run().info.run_id
        client = mlflow.tracking.MlflowClient()
        try:
            client.create_registered_model("demand_forecaster")
        except Exception:
            pass
        version = client.create_model_version(
            name="demand_forecaster",
            source=f"runs:/{run_id}/model/{os.path.basename(model_path)}",
            run_id=run_id,
        )

        if fold_rmsse < best_rmsse:
            best_rmsse   = fold_rmsse
            best_version = version.version

# ── Promote best fold to @champion ────────────────────────────────────────────
client = mlflow.tracking.MlflowClient()
client.set_registered_model_alias("demand_forecaster", "champion", best_version)

print(f"\n{'='*50}")
print(f"CV RMSSE (per-series): {[round(s, 4) for s in cv_rmsse]}")
print(f"Mean CV RMSSE:         {np.mean(cv_rmsse):.4f} ± {np.std(cv_rmsse):.4f}")
print(f"Best fold RMSSE:       {best_rmsse:.4f}")
print(f"Champion:              demand_forecaster v{best_version} @champion")
print(f"MLflow:                {MLFLOW_URI}/#/experiments")
