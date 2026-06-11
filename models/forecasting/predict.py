import pandas as pd
import numpy as np
import lightgbm as lgb
import duckdb
import os
import pickle
from sklearn.preprocessing import LabelEncoder
from dotenv import load_dotenv

load_dotenv()

DUCKDB_PATH  = os.getenv("DUCKDB_PATH", "data/warehouse.duckdb")
FEATURE_PATH = "data/processed/m5_item_features.parquet"
MODEL_PATH   = "models/forecasting/artifacts/lgb_tweedie_fold_3.txt"
HORIZON      = 28


def load_model():
    return lgb.Booster(model_file=MODEL_PATH)


def get_feature_cols(df):
    return [c for c in df.columns if c not in
            ["sale_date", "unit_sales", "sell_price",
             "snap_CA", "snap_TX", "snap_WI"]]


def forecast(store_id: str, item_id: str, horizon: int = HORIZON) -> dict:
    df = pd.read_parquet(FEATURE_PATH)
    df["sale_date"] = pd.to_datetime(df["sale_date"])

    series = df[(df["store_id"] == store_id) & (df["item_id"] == item_id)].copy()
    if series.empty:
        return {"error": f"No data found for store={store_id}, item={item_id}"}

    # Encode categoricals using same mapping as training
    cat_cols = ["item_id", "store_id", "dept_id", "cat_id", "state_id"]
    full_df = df.copy()
    for col in cat_cols:
        le = LabelEncoder()
        full_df[col] = le.fit_transform(full_df[col].astype(str))
        if col in series.columns:
            series[col] = le.transform(series[col].astype(str))

    feature_cols = get_feature_cols(full_df)

    # Use last known row as seed — roll forward horizon days
    last_row    = series.sort_values("sale_date").iloc[-1].copy()
    last_date   = last_row["sale_date"]
    model       = load_model()

    forecasts   = []
    dates       = []
    recent_vals = list(series.sort_values("sale_date")["unit_sales"].values[-28:])

    for day in range(1, horizon + 1):
        pred_date = last_date + pd.Timedelta(days=day)

        row = last_row.copy()
        row["sale_date"]    = pred_date
        row["day_of_week"]  = pred_date.dayofweek
        row["day_of_month"] = pred_date.day
        row["week_of_year"] = pred_date.isocalendar().week
        row["month"]        = pred_date.month
        row["is_weekend"]   = int(pred_date.dayofweek >= 5)

        # Update lag features from rolling window
        row["units_lag_1"]  = recent_vals[-1] if recent_vals else 0
        row["units_lag_7"]  = recent_vals[-7] if len(recent_vals) >= 7 else 0
        row["units_lag_14"] = recent_vals[-14] if len(recent_vals) >= 14 else 0
        row["units_lag_28"] = recent_vals[-28] if len(recent_vals) >= 28 else 0

        tail7  = recent_vals[-7:]  if len(recent_vals) >= 7  else recent_vals
        tail14 = recent_vals[-14:] if len(recent_vals) >= 14 else recent_vals
        tail28 = recent_vals[-28:] if len(recent_vals) >= 28 else recent_vals

        row["units_roll_mean_7"]  = float(np.mean(tail7))
        row["units_roll_mean_14"] = float(np.mean(tail14))
        row["units_roll_mean_28"] = float(np.mean(tail28))
        row["units_roll_std_7"]   = float(np.std(tail7)  if len(tail7)  > 1 else 0)
        row["units_roll_std_28"]  = float(np.std(tail28) if len(tail28) > 1 else 0)

        X    = pd.DataFrame([row[feature_cols]])
        pred = float(np.clip(model.predict(X)[0], 0, None))

        forecasts.append(round(pred, 2))
        dates.append(pred_date.strftime("%Y-%m-%d"))
        recent_vals.append(pred)
        if len(recent_vals) > 28:
            recent_vals.pop(0)

    return {
        "store_id":  store_id,
        "item_id":   item_id,
        "horizon":   horizon,
        "dates":     dates,
        "forecast":  forecasts,
        "total_forecast_units": round(sum(forecasts), 1),
    }


if __name__ == "__main__":
    result = forecast("CA_1", "FOODS_3_001", horizon=28)
    if "error" in result:
        print(result["error"])
    else:
        print(f"Store: {result['store_id']}  Item: {result['item_id']}")
        print(f"28-day total forecast: {result['total_forecast_units']} units")
        print("\nDaily forecast:")
        for d, v in zip(result["dates"], result["forecast"]):
            print(f"  {d}: {v}")
