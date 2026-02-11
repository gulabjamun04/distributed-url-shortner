from aiokafka import AIOKafkaProducer
import json
import asyncio
import os

# Kafka broker (Redpanda) configuration
KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")

producer: AIOKafkaProducer | None = None

async def start_kafka_producer():
    global producer
    producer = AIOKafkaProducer(bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS)
    await producer.start()

async def stop_kafka_producer():
    if producer:
        await producer.stop()

async def send_click_event(short_code: str):
    """
    Sends a click event to the Kafka 'clicks' topic.
    """
    if producer:
        event_data = {"short_code": short_code, "timestamp": asyncio.current_task()._loop.time()}
        await producer.send_and_wait("clicks", json.dumps(event_data).encode("utf-8"))

async def send_new_url_event(short_code: str, long_url: str):
    """
    Sends a new URL event to the Kafka 'new_urls' topic for classification.
    """
    if producer:
        event_data = {"short_code": short_code, "long_url": long_url}
        await producer.send_and_wait("new_urls", json.dumps(event_data).encode("utf-8"))
