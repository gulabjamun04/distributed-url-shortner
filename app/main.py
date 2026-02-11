from fastapi import FastAPI, Depends, HTTPException, status, Request, Response
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
import random
import string
import uvicorn
from pydantic import BaseModel

from app.db import SHARD_ENGINES, get_session, Base
from app.models import URL
from app.utils.hashing import get_shard_for_key
from app.utils.keygen import encode_base62
from app.services.cache import get_url, set_url, set_null_url # Import caching functions

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

class ShortenURLRequest(BaseModel):
    long_url: str

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
        await set_url(new_url.short_code, new_url.long_url) # Cache the new URL
    return {"short_url": f"/{new_url.short_code}"}

@app.get("/{short_code}")
async def redirect_to_long_url(short_code: str):
    # 1. Check cache first
    cached_long_url = await get_url(short_code)
    if cached_long_url:
        return RedirectResponse(url=cached_long_url)
    
    # 2. If cache miss, fetch from DB
    shard_name = get_shard_for_key(short_code)
    async for session in get_session(shard_name):
        result = await session.execute(
            select(URL).filter(URL.short_code == short_code)
        )
        url_entry = result.scalar_one_or_none()

        if url_entry:
            # 3. If found in DB, set in cache and redirect
            await set_url(url_entry.short_code, url_entry.long_url)
            return RedirectResponse(url=url_entry.long_url)
        else:
            # 4. If not found in DB, set null entry in cache and raise 404
            await set_null_url(short_code)
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Short URL not found")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
