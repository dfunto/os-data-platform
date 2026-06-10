"""
Ingest Open-Meteo current weather into Kafka topic 'weather'.

Usage:
    pip install confluent-kafka requests
    python ingest_weather.py                     # one-shot
    python ingest_weather.py --interval 60       # poll every 60s
"""

import argparse
import json
import time
from datetime import datetime, timezone

import requests
from confluent_kafka import Producer

KAFKA_BOOTSTRAP = "localhost:9092"
TOPIC = "weather"

# Locations to fetch (name, lat, lon)
LOCATIONS = [
    ("New York",  40.7128, -74.0060),
    ("London",    51.5074,  -0.1278),
    ("Tokyo",     35.6762, 139.6503),
]

OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"
WEATHER_PARAMS = {
    "current": [
        "temperature_2m",
        "relative_humidity_2m",
        "wind_speed_10m",
        "weather_code",
    ],
    "wind_speed_unit": "ms",
}


def fetch_weather(name: str, lat: float, lon: float) -> dict:
    params = {**WEATHER_PARAMS, "latitude": lat, "longitude": lon}
    resp = requests.get(OPEN_METEO_URL, params=params, timeout=10)
    resp.raise_for_status()
    data = resp.json()
    current = data["current"]
    return {
        "location": name,
        "latitude": lat,
        "longitude": lon,
        "timestamp": current["time"],
        "ingested_at": datetime.now(timezone.utc).isoformat(),
        "temperature_c": current["temperature_2m"],
        "humidity_pct": current["relative_humidity_2m"],
        "wind_speed_ms": current["wind_speed_10m"],
        "weather_code": current["weather_code"],
    }


def delivery_report(err, msg):
    if err:
        print(f"[ERROR] delivery failed: {err}")
    else:
        print(f"[OK] {msg.topic()} partition={msg.partition()} offset={msg.offset()}")


def ingest_once(producer: Producer):
    for name, lat, lon in LOCATIONS:
        try:
            record = fetch_weather(name, lat, lon)
            producer.produce(
                TOPIC,
                key=name.lower().replace(" ", "_"),
                value=json.dumps(record),
                callback=delivery_report,
            )
            print(f"[QUEUED] {name}: {record['temperature_c']}°C")
        except Exception as e:
            print(f"[ERROR] {name}: {e}")
    producer.flush()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--interval", type=int, default=0,
                        help="Poll interval in seconds (0 = one-shot)")
    parser.add_argument("--bootstrap", default=KAFKA_BOOTSTRAP,
                        help="Kafka bootstrap server")
    parser.add_argument("--topic", default=TOPIC,
                        help="Kafka topic name")
    args = parser.parse_args()

    global TOPIC
    TOPIC = args.topic

    producer = Producer({"bootstrap.servers": args.bootstrap})
    print(f"Connected to Kafka at {args.bootstrap}, topic={TOPIC}")

    if args.interval > 0:
        print(f"Polling every {args.interval}s. Ctrl+C to stop.")
        while True:
            ingest_once(producer)
            time.sleep(args.interval)
    else:
        ingest_once(producer)


if __name__ == "__main__":
    main()