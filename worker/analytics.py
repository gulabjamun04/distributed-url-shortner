from aiokafka import AIOKafkaConsumer
import asyncio
import json
import os
import time
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.future import select
from sqlalchemy import update
from app.db import SHARD_ENGINES, get_session, Base
from app.models import URL
from app.utils.hashing import get_shard_for_key

from prometheus_client import generate_latest, Counter, Histogram, CONTENT_TYPE_LATEST, start_http_server

# Kafka broker (Redpanda) configuration
KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "redpanda:9092")
TOPIC = "clicks"
GROUP_ID = "analytics-group"

# Prometheus Metrics for Worker
WORKER_CONSUMED_MESSAGES_TOTAL = Counter(
    "worker_consumed_messages_total", "Total messages consumed by worker", ["topic"]
)
WORKER_MESSAGE_PROCESSING_ERRORS_TOTAL = Counter(
    "worker_message_processing_errors_total", "Total errors processing messages by worker", ["topic"]
)
WORKER_MESSAGE_PROCESSING_DURATION_SECONDS = Histogram(
    "worker_message_processing_duration_seconds", "Duration of message processing by worker", ["topic"]
)

async def consume_click_events():
    consumer = AIOKafkaConsumer(
        TOPIC,
        bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
        group_id=GROUP_ID,
        auto_offset_reset="earliest"
    )

    # Retry mechanism for Kafka connection
    retries = 5
    delay = 5
    for i in range(retries):
        try:
            print(f"Attempting to connect to Kafka (attempt {i+1}/{retries})...")
            await consumer.start()
            print("Successfully connected to Kafka.")
            break
        except Exception as e:
            print(f"Failed to connect to Kafka: {e}")
            if i < retries - 1:
                print(f"Retrying in {delay} seconds...")
                await asyncio.sleep(delay)
            else:
                print("Max retries reached. Exiting.")
                raise

    try:
        async for msg in consumer:
            with WORKER_MESSAGE_PROCESSING_DURATION_SECONDS.labels(topic=TOPIC).time():
                try:
                    event_data = json.loads(msg.value.decode("utf-8"))
                    short_code = event_data["short_code"]
                    print(f"Received click event for short_code: {short_code}")

                    # Determine shard and update click count
                    shard_name = get_shard_for_key(short_code)
                    async for session in get_session(shard_name):
                        # Increment click_count
                        stmt = (
                            update(URL)
                            .where(URL.short_code == short_code)
                            .values(click_count=URL.click_count + 1)
                        )
                        await session.execute(stmt)
                        await session.commit()
                        print(f"Updated click count for {short_code} in {shard_name}")
                    WORKER_CONSUMED_MESSAGES_TOTAL.labels(topic=TOPIC).inc()
                except Exception as e:
                    WORKER_MESSAGE_PROCESSING_ERRORS_TOTAL.labels(topic=TOPIC).inc()
                    print(f"Error processing message: {e}")
    finally:
        await consumer.stop()

async def main():
    # Start Prometheus metrics server for the worker
    start_http_server(8001) # Worker metrics will be on port 8001

    await consume_click_events()

if __name__ == "__main__":
    asyncio.run(main())
