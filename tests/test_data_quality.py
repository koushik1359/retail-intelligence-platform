"""
Great Expectations data quality checkpoint for mart tables.

Validates schema, nulls, ranges, and uniqueness on:
  - main_mart.fct_product_performance
  - main_mart.fct_daily_demand
  - main_mart.mart_executive_kpis
  - main_mart.dim_stores
"""

import os
import sys
import duckdb
import pandas as pd
import great_expectations as gx
from great_expectations.core import ExpectationSuite
import great_expectations.expectations as gxe

DUCKDB_PATH = os.getenv("DUCKDB_PATH", "data/warehouse.duckdb")


def load(table: str) -> pd.DataFrame:
    con = duckdb.connect(DUCKDB_PATH, read_only=True)
    df = con.execute(f"SELECT * FROM {table}").df()
    con.close()
    return df


def validate(context, df: pd.DataFrame, name: str, expectations: list) -> dict:
    suite = ExpectationSuite(name=name)
    for exp in expectations:
        suite.add_expectation(exp)
    suite = context.suites.add(suite)

    ds = context.data_sources.add_pandas(f"ds_{name}")
    asset = ds.add_dataframe_asset(name="asset")
    batch_def = asset.add_batch_definition_whole_dataframe("batch")
    vd = context.validation_definitions.add(
        gx.ValidationDefinition(name=f"vd_{name}", data=batch_def, suite=suite)
    )
    result = vd.run(batch_parameters={"dataframe": df})
    return result


def print_results(name: str, result) -> bool:
    stats = result["statistics"]
    passed = stats["successful_expectations"]
    total = stats["evaluated_expectations"]
    failed_checks = [
        r for r in result["results"] if not r["success"]
    ]
    status = "PASS" if result["success"] else "FAIL"
    print(f"\n{'='*55}")
    print(f"  {name:<40} [{status}]")
    print(f"  {passed}/{total} expectations passed")
    for f in failed_checks:
        exp_type = f["expectation_config"]["type"]
        col = f["expectation_config"]["kwargs"].get("column", "")
        obs = f["result"].get("observed_value", "")
        print(f"  ✗ {exp_type}({col}) — observed: {obs}")
    return result["success"]


def main():
    context = gx.get_context(mode="ephemeral")
    all_passed = True

    # ── fct_product_performance ──────────────────────────────
    df = load("main_mart.fct_product_performance")
    all_passed &= print_results("fct_product_performance", validate(context, df, "fct_product_performance", [
        gxe.ExpectTableRowCountToBeBetween(min_value=3_000, max_value=10_000),
        gxe.ExpectColumnValuesToNotBeNull(column="product_id"),
        gxe.ExpectColumnValuesToBeUnique(column="product_id"),
        gxe.ExpectColumnValuesToNotBeNull(column="product_name"),
        gxe.ExpectColumnValuesToBeBetween(column="total_revenue", min_value=0),
        gxe.ExpectColumnValuesToBeBetween(column="avg_unit_price", min_value=0),
        gxe.ExpectColumnValuesToBeBetween(column="total_units_sold", min_value=1),
        gxe.ExpectColumnValuesToBeBetween(column="revenue_rank", min_value=1),
        gxe.ExpectColumnValuesToNotBeNull(column="revenue_rank"),
    ]))

    # ── fct_daily_demand ─────────────────────────────────────
    df = load("main_mart.fct_daily_demand")
    all_passed &= print_results("fct_daily_demand", validate(context, df, "fct_daily_demand", [
        gxe.ExpectTableRowCountToBeBetween(min_value=100_000, max_value=500_000),
        gxe.ExpectColumnValuesToNotBeNull(column="sale_date"),
        gxe.ExpectColumnValuesToNotBeNull(column="store_id"),
        gxe.ExpectColumnValuesToBeBetween(column="total_revenue", min_value=0),
        gxe.ExpectColumnValuesToBeBetween(column="total_units", min_value=0),
        gxe.ExpectColumnValuesToBeBetween(column="avg_price", min_value=0),
        gxe.ExpectColumnValuesToBeInSet(column="state_id", value_set=["CA", "TX", "WI"]),
    ]))

    # ── mart_executive_kpis ──────────────────────────────────
    df = load("main_mart.mart_executive_kpis")
    all_passed &= print_results("mart_executive_kpis", validate(context, df, "mart_executive_kpis", [
        gxe.ExpectTableRowCountToBeBetween(min_value=500, max_value=2_000),
        gxe.ExpectColumnValuesToNotBeNull(column="kpi_date"),
        gxe.ExpectColumnValuesToBeUnique(column="kpi_date"),
        gxe.ExpectColumnValuesToBeBetween(column="total_revenue", min_value=0),
        gxe.ExpectColumnValuesToBeBetween(column="total_orders", min_value=1),
        gxe.ExpectColumnValuesToBeBetween(column="unique_customers", min_value=1),
        gxe.ExpectColumnValuesToBeBetween(column="avg_basket_size", min_value=0),
    ]))

    # ── dim_stores ───────────────────────────────────────────
    df = load("main_mart.dim_stores")
    all_passed &= print_results("dim_stores", validate(context, df, "dim_stores", [
        gxe.ExpectTableRowCountToEqual(value=10),
        gxe.ExpectColumnValuesToNotBeNull(column="store_id"),
        gxe.ExpectColumnValuesToBeUnique(column="store_id"),
        gxe.ExpectColumnValuesToBeInSet(column="state_id", value_set=["CA", "TX", "WI"]),
        gxe.ExpectColumnValuesToBeBetween(column="total_revenue_all_time", min_value=0),
    ]))

    print(f"\n{'='*55}")
    if all_passed:
        print("  ALL CHECKS PASSED")
    else:
        print("  SOME CHECKS FAILED — see details above")
    print(f"{'='*55}\n")

    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
