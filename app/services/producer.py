from aiokafka import AIOKafkaProducer
import json
import asyncio
import os

# Kafka broker (Redpanda) configuration
# KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
# For local development with docker-compose, the service name is 'redpanda'
KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "redpanda:9092")


producer = AIOKafkaProducer(bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS)

async def start_kafka_producer():
    await producer.start()

async def stop_kafka_producer():
    await producer.stop()

async def send_click_event(short_code: str):
    """
    Sends a click event to the Kafka 'clicks' topic.
    """
    event_data = {"short_code": short_code, "timestamp": asyncio.current_task()._loop.time()} # Using loop.time() for simplicity
    await producer.send_and_wait("clicks", json.dumps(event_data).encode("utf-8"))
