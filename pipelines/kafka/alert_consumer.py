import json
from kafka import KafkaConsumer
from datetime import datetime

BROKER = "localhost:9092"

consumer = KafkaConsumer(
    "alerts.inventory",
    "alerts.revenue",
    bootstrap_servers=[BROKER],
    value_deserializer=lambda m: json.loads(m.decode("utf-8")),
    auto_offset_reset="earliest",
    group_id="alert-consumer",
)

print("Listening for alerts on alerts.inventory and alerts.revenue...")
print("Press Ctrl+C to stop.\n")

SEVERITY = {
    "high_volume_order":      "⚠️  INVENTORY",
    "high_value_transaction": "💰 REVENUE",
}

try:
    for msg in consumer:
        alert     = msg.value
        topic     = msg.topic
        atype     = alert.get("alert_type", "unknown")
        label     = SEVERITY.get(atype, "🔔 ALERT")
        timestamp = alert.get("timestamp", datetime.utcnow().isoformat())

        print(f"[{timestamp[:19]}] {label} | topic={topic}")
        for k, v in alert.items():
            if k != "alert_type":
                print(f"    {k}: {v}")
        print()

except KeyboardInterrupt:
    print("Stopped.")
finally:
    consumer.close()
