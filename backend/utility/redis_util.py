import asyncio
import json
import logging
import os
from datetime import datetime

import asyncio
import logging

from crud.conversation_history import conversation_service

# Configure logging
logger = logging.getLogger(__name__)

from upstash_redis import Redis as UpstashRedis
from redis.asyncio import Redis
from redis.exceptions import RedisError
from dotenv import load_dotenv


# Load environment variables (only needed locally)
load_dotenv()

# Setup logger
logger = logging.getLogger(__name__)

# Configuration
REDIS_URL ="https://guiding-satyr-18677.upstash.io"
REDIS_TOKEN = os.getenv("REDIS_TOKEN")


# REDIS_SERVER = os.getenv("REDIS_SERVER", "localhost")  # Default to localhost
# REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))  # Default Redis po
# REDIS_SERVER = os.getenv("REDIS_SERVER", "localhost")  # Default to localhost
# REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))  # Default Redis port
# REDIS_AUTH = os.getenv("REDIS_KEY")  # None for local development
# USE_SSL = os.getenv("REDIS_SSL", "false").lower() == "true"  # Default to False

# Global Redis client instance
redis_client: UpstashRedis = None

print(REDIS_URL)

def get_redis_client() -> UpstashRedis:
    """
    Returns an active Upstash Redis client instance for dependency injection.
    Only sets up the client once (singleton pattern).
    """
    global redis_client

    if redis_client is None:
        try:
            if not REDIS_URL or not REDIS_TOKEN:
                raise ValueError("REDIS_URL and REDIS_TOKEN must be set for Upstash Redis.")

            redis_client = UpstashRedis(
                url="https://direct-gannet-10624.upstash.io",
                token=REDIS_TOKEN
            )

            # Test connection by setting and getting a dummy value
            redis_client.set("connection_test", "ok")
            value = redis_client.get("connection_test")
            if value != "ok":
                raise RuntimeError("Failed Upstash Redis connection test.")

            logger.info(f"Connected to Upstash Redis at {REDIS_URL}")

        except Exception as e:
            logger.error(f"Failed to connect to Upstash Redis: {e}")
            raise RuntimeError("Could not establish Upstash Redis connection") from e

    return redis_client


# ✅ Test Redis connection at startup (Non-blocking)
async def test_redis_connection():
    try:
        client = get_redis_client()
        client.ping()
        logger.info("Redis connection verified successfully!")
    except Exception as e:
        logger.error(f"Redis connection test failed: {e}")

# ✅ Schedule connection test on startup
try:
    loop = asyncio.get_running_loop()
    loop.create_task(test_redis_connection())  # Run in event loop
except RuntimeError:
    asyncio.run(test_redis_connection())  # Fallback for synchronous startup


def get_from_redis(redis_client: UpstashRedis, redis_key: str):
    """
    Retrieve conversation metadata from Redis.

    Args:
        redis_client (Redis): Redis async client instance.
        redis_key (str): The Redis key to retrieve data.

    Returns:
        dict or None: Parsed dictionary if data exists, otherwise None.
    """
    try:
        data = redis_client.get(redis_key)
        if data:
            return json.loads(data)  # Convert JSON string back to a Python dictionary
        return None
    except RedisError as e:
        logger.error(f"Redis read error for key {redis_key}: {str(e)}")
        return None

def save_to_redis(redis_client: UpstashRedis, redis_key: str, conversation_data: dict) -> bool:
    try:
        conversation_data["last_updated"] = datetime.utcnow().isoformat()
        redis_data = json.dumps(conversation_data)
        redis_client.setex(redis_key, 3600, redis_data)
        logger.info(f"Saved conversation {redis_key} to Redis")
        return True
    except RedisError as e:
        logger.error(f"Redis save error for key {redis_key}: {str(e)}")
        return False



def save_current_convo_to_redis(redis_client: UpstashRedis, user_id: int, conversation_id: str, redis_metadata: dict):
    """
    Save conversation metadata (conversation_id, conversation_name, last_updated) to Redis with expiration.

    Args:
        redis_client (Redis): Redis async client instance.
        user_id (int): User's ID.
        conversation_id (str): Unique conversation ID.
        redis_metadata (dict): Metadata containing conversation_id, conversation_name, and last_updated.

    Returns:
        bool: True if save was successful, False otherwise.
    """
    try:
        redis_key = f"current_conv:{user_id}:{conversation_id}"  # Redis key format
        redis_metadata["last_updated"] = datetime.utcnow().isoformat()  # Ensure timestamp is updated

        # Convert metadata to JSON
        redis_metadata_json = json.dumps(redis_metadata)

        # Save metadata to Redis with a 1-hour expiration
        redis_client.setex(redis_key, 3600, redis_metadata_json)

        logger.info(f"Saved conversation metadata to Redis: {redis_key}")
        return True
    except RedisError as e:
        logger.error(f"Redis save error for key {redis_key}: {str(e)}")
        return False
    



async def sync_redis_to_supabase_background_worker():
    """
    Background worker that periodically syncs Redis data to Supabase.
    This replaces your original sync_redis_to_db_background_worker function.
    """
    logger.info("Starting Redis to Supabase background sync worker")
    
    while True:
        try:
            # Get Redis client
            redis_client = get_redis_client()
            
            if not redis_client:
                logger.error("Redis client is not available, skipping sync")
                await asyncio.sleep(1800)  # Wait 30 minutes before retrying
                continue
            
            # Perform the sync using our Supabase service
            await conversation_service.sync_redis_to_supabase(redis_client)
            
            logger.info("Background sync to Supabase completed successfully")
            
        except Exception as e:
            logger.error(f"Error in Supabase background worker: {str(e)}")
        
        # Wait 30 minutes before next sync
        await asyncio.sleep(1800)

async def sync_user_redis_to_supabase(user_id: int):
    """
    Sync a specific user's Redis conversations to Supabase.
    Useful for on-demand syncing or user-specific operations.
    """
    try:
        redis_client = get_redis_client()
        
        if not redis_client:
            logger.error("Redis client is not available")
            return False
        
        await conversation_service.sync_redis_to_supabase(redis_client, user_id)
        logger.info(f"Successfully synced user {user_id} conversations to Supabase")
        return True
        
    except Exception as e:
        logger.error(f"Error syncing user {user_id} to Supabase: {str(e)}")
        return False


# For manual trigger - you can add this as an admin endpoint
async def manual_sync_trigger():
    """
    Manually trigger a sync operation.
    Can be useful for testing or admin operations.
    """
    try:
        redis_client = get_redis_client()
        if redis_client:
            await conversation_service.sync_redis_to_supabase(redis_client)
            return {"status": "success", "message": "Manual sync completed"}
        else:
            return {"status": "error", "message": "Redis client not available"}
    except Exception as e:
        logger.error(f"Manual sync failed: {str(e)}")
        return {"status": "error", "message": f"Sync failed: {str(e)}"}
