import json
import os
from typing import Optional
import redis


class RedisClient:
    """Simple Redis client for fetching call prompts and metadata."""
    
    _client: Optional[redis.Redis] = None
    
    @classmethod
    def get_client(cls) -> redis.Redis:
        """Get or create Redis client instance."""
        if cls._client is None:
            redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
            cls._client = redis.from_url(
                redis_url,
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5
            )
        return cls._client
    
    @classmethod
    def get_call_prompt(cls, call_sid: str) -> Optional[dict]:
        """
        Retrieve call prompt and metadata from Redis.
        
        Args:
            call_sid: Twilio call SID
            
        Returns:
            Dict with agent_id, workspace_id, and prompt, or None if not found
        """
        redis_key = f"call_prompt:{call_sid}"
        try:
            client = cls.get_client()
            data = client.get(redis_key)
            
            if data:
                return json.loads(data)
            return None
        except Exception as e:
            print(f"Failed to fetch from Redis: {e}")
            return None
    
    @classmethod
    def delete_call_prompt(cls, call_sid: str) -> bool:
        """
        Delete call prompt from Redis (cleanup).
        
        Args:
            call_sid: Twilio call SID
            
        Returns:
            True if key was deleted, False if key didn't exist
        """
        redis_key = f"call_prompt:{call_sid}"
        try:
            client = cls.get_client()
            return bool(client.delete(redis_key))
        except Exception as e:
            print(f"Failed to delete from Redis: {e}")
            return False

