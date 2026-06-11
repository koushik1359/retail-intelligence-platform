import json
import duckdb
import os
from kafka import KafkaConsumer, KafkaProducer
from dotenv import load_dotenv

load_dotenv()

DUCKDB_PATH = os.getenv("DUCKDB_PATH", "data/warehouse.duckdb")
BROKER      = "localhost:9092"

consumer = KafkaConsumer(
    "raw.transactions",
    bootstrap_servers=[BROKER],
    value_deserializer=lambda m: json.loads(m.decode("utf-8")),
    auto_offset_reset="earliest",
    group_id="stream-processor",
)
producer = KafkaProducer(
    bootstrap_servers=[BROKER],
    value_serializer=lambda v: json.dumps(v, default=str).encode("utf-8"),
)

# Load product metadata into memory for fast lookup
con = duckdb.connect(DUCKDB_PATH, read_only=True)
products = con.execute("""
    SELECT product_id, product_name, total_revenue, revenue_rank, total_units_sold
    FROM main_mart.fct_product_performance
""").fetchdf().set_index("product_id")
con.close()
print(f"Loaded {len(products):,} products into lookup table.")
print("Consuming from raw.transactions... Press Ctrl+C to stop.\n")

processed = 0
alerts_sent = 0

try:
    for msg in consumer:
        txn = msg.value

        # Enrich with product metadata
        pid  = txn.get("product_id", "")
        meta = products.loc[pid] if pid in products.index else None

        enriched = {
            **txn,
            "category":     str(meta["product_name"]) if meta is not None else "unknown",
            "revenue_rank": int(meta["revenue_rank"]) if meta is not None else -1,
            "is_top_seller": bool(meta["revenue_rank"] <= 100) if meta is not None else False,
        }
        producer.send("enriched.transactions", value=enriched)

        # Inventory alert: high-velocity item ordered in large quantity
        if meta is not None and txn["quantity"] >= 10:
            avg_qty = meta["total_units_sold"] / max(meta["revenue_rank"], 1)
            if txn["quantity"] > avg_qty * 5:
                alert = {
                    "alert_type":  "high_volume_order",
                    "store_id":    txn["country"],
                    "product_id":  pid,
                    "quantity":    txn["quantity"],
                    "threshold":   round(avg_qty * 5, 1),
                    "timestamp":   txn["timestamp"],
                }
                producer.send("alerts.inventory", value=alert)
                alerts_sent += 1

        # Revenue alert: single transaction revenue > £500
        if txn["revenue"] > 500:
            alert = {
                "alert_type": "high_value_transaction",
                "txn_id":     txn["txn_id"],
                "customer_id": txn["customer_id"],
                "revenue":    txn["revenue"],
                "product_id": pid,
                "timestamp":  txn["timestamp"],
            }
            producer.send("alerts.revenue", value=alert)
            alerts_sent += 1

        processed += 1
        if processed % 1000 == 0:
            print(f"  Processed {processed:,} | Alerts sent: {alerts_sent}")

except KeyboardInterrupt:
    print(f"\nStopped. Processed {processed:,} transactions, sent {alerts_sent} alerts.")
finally:
    consumer.close()
    producer.flush()
    producer.close()
