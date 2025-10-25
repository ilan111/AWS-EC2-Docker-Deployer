import logging
from .kafka_consumer import get_kafka_consumer
from .message_processor import MessageProcessor

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("worker")

def main():
    log.info("Starting worker...")
    processor = MessageProcessor()
    consumer = get_kafka_consumer(["user_requests", "ec2_deployments"], "logic-worker")

    for message in consumer:
        try:
            topic = message.topic
            message_data = message.value
            log.info(f"Received message from topic '{topic}'")
            processor.handle_message(topic, message_data)

        except Exception as e:
            log.error(f"Failed to process message: {e}")

if __name__ == "__main__":
    main()
