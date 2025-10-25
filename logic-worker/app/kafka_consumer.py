import json
import os
from kafka import KafkaConsumer

def get_kafka_consumer(topics: str, group_id: str = "default_group"):
    """
    topics: str or list of str
    """
    if isinstance(topics, str):
        topic_list = [topics]
    else:
        topic_list = topics

    bootstrap_servers = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
    return KafkaConsumer(
        *topic_list,
        bootstrap_servers=[bootstrap_servers],
        group_id=group_id,
        value_deserializer=lambda x: json.loads(x.decode('utf-8'))
    )