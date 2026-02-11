from fastapi import FastAPI, Depends, HTTPException, status, Request, Response
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
import random
import string
import uvicorn

from app.db import SHARD_ENGINES, get_session, Base
from app.models import URL
from app.utils.hashing import get_shard_for_key
from app.utils.keygen import encode_base62

app = FastAPI()

# Event handler to create tables on startup
@app.on_event("startup")
async def startup_event():
    for shard_name, engine in SHARD_ENGINES.items():
        async with engine.begin() as conn:
            # Drop and create tables for development purposes
            await conn.run_sync(Base.metadata.drop_all)
            await conn.run_sync(Base.metadata.create_all)
        print(f"Database tables created for {shard_name}")

class ShortenURLRequest:
    def __init__(self, long_url: str):
        self.long_url = long_url

@app.post("/shorten")
async def shorten_url(request: ShortenURLRequest):
    # Generate a random 6-character short code
    short_code = ''.join(random.choices(string.ascii_letters + string.digits, k=6))
    
    shard_name = get_shard_for_key(short_code)
    async for session in get_session(shard_name):
        new_url = URL(short_code=short_code, long_url=request.long_url)
        session.add(new_url)
        await session.commit()
        await session.refresh(new_url)
    return {"short_url": f"/{new_url.short_code}"}

@app.get("/{short_code}")
async def redirect_to_long_url(short_code: str):
    shard_name = get_shard_for_key(short_code)
    async for session in get_session(shard_name):
        result = await session.execute(
            select(URL).filter(URL.short_code == short_code)
        )
        url_entry = result.scalar_one_or_none()

        if url_entry:
            return RedirectResponse(url=url_entry.long_url)
        else:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Short URL not found")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
