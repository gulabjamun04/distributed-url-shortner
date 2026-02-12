from aiokafka import AIOKafkaConsumer
import asyncio
import json
import os
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.future import select
from sqlalchemy import update
from app.db import SHARD_ENGINES, get_session, Base
from app.models import URL
from app.utils.hashing import get_shard_for_key


# Kafka broker (Redpanda) configuration
KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "redpanda:9092")
TOPIC = "clicks"
GROUP_ID = "analytics-group"

async def consume_click_events():
    consumer = AIOKafkaConsumer(
        TOPIC,
        bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
        group_id=GROUP_ID,
        auto_offset_reset="earliest"
    )
    await consumer.start()
    try:
        async for msg in consumer:
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
    finally:
        await consumer.stop()

if __name__ == "__main__":
    asyncio.run(consume_click_events())
