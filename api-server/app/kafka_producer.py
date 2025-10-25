import json
import os
from kafka import KafkaProducer

def get_kafka_producer():
    bootstrap_servers = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
    return KafkaProducer(
        bootstrap_servers=[bootstrap_servers],
        value_serializer=lambda v: json.dumps(v).encode('utf-8')
    )

def send_message(topic: str, message: dict):
    producer = get_kafka_producer()
    producer.send(topic, message)
    producer.flush()