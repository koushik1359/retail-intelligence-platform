import pandas as pd
import json
import time
from kafka import KafkaProducer
from datetime import datetime

TOPIC    = "raw.transactions"
BROKER   = "localhost:9092"
TXN_RATE = 50  # transactions per second

producer = KafkaProducer(
    bootstrap_servers=[BROKER],
    value_serializer=lambda v: json.dumps(v, default=str).encode("utf-8"),
)

print("Loading transactions...")
df = pd.read_parquet("data/raw/online_retail/transactions.parquet")
df = df.dropna(subset=["customer_id", "product_id"]).reset_index(drop=True)
print(f"Loaded {len(df):,} transactions. Streaming to '{TOPIC}' at {TXN_RATE} txns/sec...")
print("Press Ctrl+C to stop.\n")

sent = 0
try:
    for _, row in df.iterrows():
        event = {
            "txn_id":      str(row["invoice_id"]),
            "customer_id": int(row["customer_id"]),
            "product_id":  str(row["product_id"]),
            "description": str(row["description"]),
            "quantity":    int(row["quantity"]),
            "unit_price":  float(row["unit_price"]),
            "revenue":     float(row["revenue"]),
            "country":     str(row["country"]),
            "timestamp":   datetime.utcnow().isoformat(),
        }
        producer.send(TOPIC, value=event)
        sent += 1
        if sent % 500 == 0:
            print(f"  Sent {sent:,} transactions...")
        time.sleep(1 / TXN_RATE)
except KeyboardInterrupt:
    print(f"\nStopped. Sent {sent:,} transactions.")
finally:
    producer.flush()
    producer.close()
