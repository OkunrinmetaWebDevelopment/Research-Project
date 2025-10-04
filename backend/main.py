import asyncio
import logging
import random
import string
import time

from utility.llm_utils import get_available_llm, load_huggingface_llm
from utility.redis_util import get_redis_client, sync_redis_to_supabase_background_worker
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware


logger = logging.getLogger()


def get_application():
    app = FastAPI(title="", version=1.0)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    return app


app = get_application()


@app.get("/")
async def root():
    logger.info("logging from the root logger")
    msg = "hi"
    return {"status": "alive"}


# Optional: Add a startup function to begin the background worker
async def start_background_sync():
    """Start the background sync worker as a background task"""
    task = asyncio.create_task(sync_redis_to_supabase_background_worker())
    logger.info("Background sync worker started")
    return task

@app.on_event("shutdown")
async def shutdown_event():
    """Gracefully close Redis connection and dispose DB engine on app shutdown."""
    try:
        redis_client = await get_redis_client()
        if redis_client:
            await redis_client.close()
            logger.info("Redis connection closed successfully.")

        logger.info("Database engine disposed successfully.")
    except Exception as e:
        logger.error(f"Error during shutdown: {str(e)}")


@app.on_event("shutdown")
async def flush_redis_on_shutdown():
    """Flush Redis database on app shutdown (Optional)."""
    try:
        redis_client = await get_redis_client()
        if redis_client:
            await redis_client.flushdb()
            logger.info("Redis database flushed on shutdown.")
    except Exception as e:
        logger.error(f"Error flushing Redis database: {str(e)}")

@app.get("/health")
async def health_check():
    """
    Health check endpoint with system status.
    """
    llm_available = False
    llm_type = None
    
    try:
        _, llm_type = get_available_llm()
        llm_available = True
    except Exception as e:
        llm_type = f"Error: {str(e)}"
    
    return {
        "status": "healthy" if llm_available else "degraded",
        "llm_available": llm_available,
        "llm_type": llm_type,
        "embedding_model": "BAAI/bge-small-en-v1.5"
    }

@app.get("/")
async def root():
    """
    Health check endpoint.
    """
    return {
        "message": "RAG Question Generator API is running",
        "endpoints": {
            "/generate-questions": "POST - Generate questions from text",
            "/docs": "GET - API documentation"
        }
    }