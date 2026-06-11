import pytest
import duckdb
import os
from dotenv import load_dotenv

load_dotenv()

DUCKDB_PATH  = os.getenv("DUCKDB_PATH", "data/warehouse.duckdb")
CHROMA_PATH  = "data/chromadb"

@pytest.mark.integration
def test_chroma_collection_populated():
    import chromadb
    client = chromadb.PersistentClient(path=CHROMA_PATH)
    col = client.get_collection("product_catalog")
    assert col.count() >= 100, f"ChromaDB has only {col.count()} docs"

@pytest.mark.integration
def test_chroma_query_returns_results():
    import chromadb
    client = chromadb.PersistentClient(path=CHROMA_PATH)
    col = client.get_collection("product_catalog")
    results = col.query(query_texts=["snack food for kids"], n_results=5)
    assert len(results["documents"][0]) == 5

@pytest.mark.integration
def test_agent_alerts_table_exists():
    con = duckdb.connect(DUCKDB_PATH, read_only=True)
    rows = con.execute("""
        SELECT table_schema, table_name
        FROM information_schema.tables
        WHERE table_name LIKE '%alert%'
    """).fetchall()
    con.close()
    assert len(rows) > 0, f"No alert tables found in any schema"

@pytest.mark.integration
def test_agent_reports_table_exists():
    con = duckdb.connect(DUCKDB_PATH, read_only=True)
    tables = con.execute("""
        SELECT table_name FROM information_schema.tables
        WHERE table_schema = 'main_mart'
    """).fetchdf()["table_name"].tolist()
    con.close()
    assert "agent_reports" in tables

@pytest.mark.integration
def test_mart_executive_kpis_has_data():
    con = duckdb.connect(DUCKDB_PATH, read_only=True)
    count = con.execute("SELECT COUNT(*) FROM main_mart.mart_executive_kpis").fetchone()[0]
    con.close()
    assert count > 0

@pytest.mark.integration
def test_product_descriptions_parquet_exists():
    assert os.path.exists("data/processed/product_descriptions.parquet")

@pytest.mark.integration
def test_product_descriptions_has_content():
    import pandas as pd
    df = pd.read_parquet("data/processed/product_descriptions.parquet")
    assert len(df) >= 100
    assert "description" in df.columns
    assert df["description"].str.len().mean() > 50
