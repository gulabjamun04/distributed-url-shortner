from aiokafka import AIOKafkaConsumer
import asyncio
import json
import os
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.future import select
from sqlalchemy import update
from huggingface_hub import InferenceClient
from dotenv import load_dotenv

from app.db import SHARD_ENGINES, get_session, Base
from app.models import URL
from app.utils.hashing import get_shard_for_key

load_dotenv() # Load environment variables from .env file

# Kafka broker (Redpanda) configuration
KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "redpanda:9092")
TOPIC = "new_urls"
GROUP_ID = "classifier-group"

# Hugging Face Inference Client
# You might need to set your HF_TOKEN environment variable for some models
HF_INFERENCE_API_URL = "https://router.huggingface.co/hf-inference/models/facebook/bart-large-mnli"
HF_TOKEN = os.getenv("HF_TOKEN") # Optional, but good practice for rate limits
inference_client = InferenceClient(HF_INFERENCE_API_URL, token=HF_TOKEN)

# Labels for zero-shot classification
CANDIDATE_LABELS = [
    "news", "social media", "shopping", "tech", "finance", "entertainment",
    "sports", "health", "education", "travel", "blog", "personal", "malicious",
    "gambling", "adult", "spam", "utility", "business", "coding", "documentation"
]

async def classify_url_content(text: str) -> str:
    """
    Performs zero-shot classification on the given text to categorize the URL.
    """
    # For a real application, you'd fetch the content of the URL here.
    # For now, we'll just classify based on the URL itself or a placeholder.
    # A more robust solution would involve fetching meta tags or actual content.

    # Simulating content for classification with the URL itself
    # A real classifier would fetch content from long_url
    classification_input = f"This URL is about: {text}" 

    result = inference_client.zero_shot_classification(
        classification_input,
        candidate_labels=CANDIDATE_LABELS,
        multi_label=False # Assuming single category for simplicity
    )
    # The result is a list of dictionaries if multi_label is True, or a dictionary if False
    # Given the TypeError, it seems to return a list even for multi_label=False.
    print(f"Hugging Face Inference Result: {result}")
    if result and isinstance(result, list) and result[0] and hasattr(result[0], 'label'):
        return result[0].label
    elif result and isinstance(result, dict) and "labels" in result: # Fallback for dict case, though not expected here
        return result["labels"][0]
    return "uncategorized"

async def consume_new_url_events():
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
            long_url = event_data["long_url"]
            print(f"Received new URL event: short_code={short_code}, long_url={long_url}")

            # Classify the long_url
            category = await classify_url_content(long_url)
            print(f"Classified '{long_url}' as: {category}")

            # Update the URL entry in the database with the category
            shard_name = get_shard_for_key(short_code)
            async for session in get_session(shard_name):
                stmt = (
                    update(URL)
                    .where(URL.short_code == short_code)
                    .values(category=category)
                )
                await session.execute(stmt)
                await session.commit()
                print(f"Updated category for {short_code} to '{category}' in {shard_name}")
    finally:
        await consumer.stop()

if __name__ == "__main__":
    asyncio.run(consume_new_url_events())
