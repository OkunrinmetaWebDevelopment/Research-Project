from typing import List, Dict, Union, Optional
import json
import os
import uuid
import logging
from datetime import datetime
from dotenv import load_dotenv
from supabase import create_client, Client
from schema.chat_models import Message

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

# Initialize Supabase client
supabase: Client = create_client(
    os.getenv("SUPABASE_URL"),
    os.getenv("SUPABASE_SERVICE_ROLE_KEY")
)

class ConversationHistoryService:
    """
    Supabase-based conversation history service that maintains your existing design patterns
    """
    
    def __init__(self):
        self.supabase = supabase
        self.table_name = 'conversation_history'
    
    def generate_unique_id_conversation_history(self) -> str:
        """Generate unique conversation ID"""
        return str(uuid.uuid4())
    
    def extract_title_from_messages_safe(self, conversation_history: Union[List[Dict], Dict, str, List[Message]]) -> str:
        """Extract title from the first user message - SAFELY handle different formats"""
        try:
            messages_to_check = []

            if isinstance(conversation_history, list):
                for msg in conversation_history:
                    if isinstance(msg, Message):
                        messages_to_check.append({"role": msg.role, "content": msg.content})
                    elif isinstance(msg, dict):
                        messages_to_check.append(msg)
            elif isinstance(conversation_history, dict):
                if 'messages' in conversation_history:
                    messages_to_check = conversation_history['messages']
                elif 'role' in conversation_history and 'content' in conversation_history:
                    messages_to_check = [conversation_history]
            elif isinstance(conversation_history, str):
                try:
                    parsed = json.loads(conversation_history)
                    if isinstance(parsed, list):
                        messages_to_check = parsed
                    elif isinstance(parsed, dict):
                        if 'messages' in parsed:
                            messages_to_check = parsed['messages']
                        else:
                            messages_to_check = [parsed]
                except json.JSONDecodeError:
                    return "Untitled Conversation"

            # Find first user message
            for message in messages_to_check:
                if isinstance(message, dict) and message.get("role") == "user":
                    content = message.get("content", "")
                    if content and isinstance(content, str):
                        return content[:50] + "..." if len(content) > 50 else content

        except Exception as e:
            logger.error(f"Error extracting title: {e}")

        return "Untitled Conversation"
    
    def prepare_conversation_data_for_db(self, conversation_data: dict) -> dict:
        """Prepare conversation data for database storage"""
        # Convert Message objects to dicts for JSONB storage
        if 'conversation_history' in conversation_data:
            history = conversation_data['conversation_history']
            if isinstance(history, list) and len(history) > 0 and isinstance(history[0], Message):
                conversation_data['conversation_history'] = [
                    {"role": msg.role, "content": msg.content} for msg in history
                ]

        # Ensure datetime is properly formatted for Supabase
        if 'last_updated' in conversation_data and conversation_data['last_updated']:
            if isinstance(conversation_data['last_updated'], datetime):
                conversation_data['last_updated'] = conversation_data['last_updated'].isoformat()
        else:
            conversation_data['last_updated'] = datetime.utcnow().isoformat()

        return conversation_data
    
    async def save_conversation(self, conversation_data: dict) -> tuple[bool, str]:
        """
        Save conversation to Supabase - equivalent to your save_to_database function
        """
        try:
            # Prepare data for Supabase
            prepared_data = self.prepare_conversation_data_for_db(conversation_data)
            
            # Check if conversation already exists by redis_conversation_id
            existing_query = self.supabase.table(self.table_name)\
                .select("*")\
                .eq("redis_conversation_id", prepared_data.get("redis_conversation_id"))
            
            existing_response = existing_query.execute()
            
            if existing_response.data:
                logger.info(f"Skipping save - conversation already exists: {prepared_data.get('redis_conversation_id')}")
                return True, "Conversation already exists"
            
            # Insert new conversation
            insert_response = self.supabase.table(self.table_name)\
                .insert(prepared_data)\
                .execute()
            
            if insert_response.data:
                logger.info(f"Successfully saved conversation: {prepared_data.get('conversation_id')}")
                return True, "Conversation saved successfully"
            else:
                logger.error(f"Failed to save conversation: {insert_response}")
                return False, "Failed to save conversation"
                
        except Exception as e:
            logger.error(f"Error saving conversation to Supabase: {e}")
            return False, f"Error: {str(e)}"
    
    async def get_conversations_for_user(self, user_id: int, skip: int = 0, limit: int = 20) -> dict:
        """
        Get paginated list of conversations for a user - equivalent to your get_conversations endpoint
        """
        try:
            # Get latest conversation per conversation_id using Supabase RPC or complex query
            # Since Supabase doesn't support window functions directly in the client,
            # we'll fetch and process in Python (or create a database function)
            
            all_conversations_response = self.supabase.table(self.table_name)\
                .select("conversation_id, conversation_name, last_updated")\
                .eq("user_id", user_id)\
                .order("last_updated", desc=True)\
                .execute()
            
            if not all_conversations_response.data:
                return {"conversations": [], "total_conversations": 0}
            
            # Group by conversation_id and get the latest
            conversation_groups = {}
            for conv in all_conversations_response.data:
                conv_id = conv['conversation_id']
                if conv_id not in conversation_groups or conv['last_updated'] > conversation_groups[conv_id]['last_updated']:
                    conversation_groups[conv_id] = conv
            
            # Convert to list and apply pagination
            unique_conversations = list(conversation_groups.values())
            unique_conversations.sort(key=lambda x: x['last_updated'], reverse=True)
            
            paginated_conversations = unique_conversations[skip:skip + limit]
            
            conversations_list = [
                {
                    "conversation_id": conv['conversation_id'],
                    "title": conv['conversation_name'] or "Untitled Conversation",
                    "last_updated": conv['last_updated']
                }
                for conv in paginated_conversations
            ]
            
            return {
                "conversations": conversations_list,
                "total_conversations": len(conversations_list)
            }
            
        except Exception as e:
            logger.error(f"Error retrieving conversations for user {user_id}: {str(e)}")
            raise Exception("Failed to retrieve conversations")
    
    async def get_conversation_by_id(self, conversation_id: str, user_id: int) -> dict:
        """
        Get specific conversation by ID - equivalent to your get_conversation endpoint
        """
        try:
            conversation_response = self.supabase.table(self.table_name)\
                .select("*")\
                .eq("user_id", user_id)\
                .eq("conversation_id", conversation_id)\
                .order("last_updated")\
                .execute()
            
            if not conversation_response.data:
                raise Exception("Conversation not found")
            
            messages = []
            for entry in conversation_response.data:
                message_objects = [
                    {"role": msg["role"], "content": msg["content"]}
                    for msg in entry['conversation_history']
                ]
                messages.append({
                    "conversation_history": message_objects,
                    "timestamp": entry['last_updated']
                })
            
            title = self.extract_title_from_messages_safe(conversation_response.data[0]['conversation_history'])
            
            return {
                "conversation_id": conversation_id,
                "title": title,
                "last_updated": max(entry['last_updated'] for entry in conversation_response.data),
                "messages": messages
            }
            
        except Exception as e:
            logger.error(f"Error retrieving conversation {conversation_id}: {str(e)}")
            raise Exception("Failed to retrieve conversation")
    
    async def get_current_conversation(self, user_id: int) -> Optional[dict]:
        """
        Get the most recent conversation for a user
        """
        try:
            current_conversation_response = self.supabase.table(self.table_name)\
                .select("conversation_id, conversation_name, last_updated")\
                .eq("user_id", user_id)\
                .order("last_updated", desc=True)\
                .limit(1)\
                .execute()
            
            if current_conversation_response.data:
                conv = current_conversation_response.data[0]
                logger.info(f"Retrieved current conversation for user {user_id}: conversation_id={conv['conversation_id']}")
                return {
                    "conversation_id": conv['conversation_id'],
                    "conversation_name": conv['conversation_name'],
                    "last_updated": conv['last_updated']
                }
            else:
                logger.info(f"No conversation found for user {user_id}")
                return None
                
        except Exception as e:
            logger.error(f"Error retrieving current conversation for user {user_id}: {str(e)}")
            raise Exception("Failed to retrieve current conversation")
    
    async def sync_redis_to_supabase(self, redis_client, user_id: Optional[int] = None):
        """
        Sync conversations from Redis to Supabase - equivalent to your sync_redis_to_db function
        """
        try:
            if not redis_client:
                logger.error("Redis client is not initialized!")
                return

            # Get Redis keys - filter by user if provided
            key_pattern = f"conv:{user_id}:*" if user_id else "conv:*:*"
            all_keys = redis_client.keys(key_pattern)
            
            if not all_keys:
                logger.info("No conversation data found in Redis for sync.")
                return

            sync_count = 0

            for key in all_keys:
                try:
                    data = redis_client.get(key)
                    if not data:
                        continue

                    try:
                        conversation_data = json.loads(data)
                    except json.JSONDecodeError:
                        logger.error(f"Invalid JSON data in Redis key {key}")
                        continue

                    # Validate required fields
                    required_fields = ["user_id", "conversation_id", "conversation_name", 
                                     "redis_conversation_id", "conversation_history", "last_updated"]
                    
                    if not all(field in conversation_data for field in required_fields):
                        logger.warning(f"Skipping invalid Redis entry: {key}")
                        continue

                    # Save to Supabase
                    success, message = await self.save_conversation(conversation_data)
                    if success:
                        sync_count += 1

                except Exception as e:
                    logger.error(f"Error syncing conversation {key}: {str(e)}")
                    continue

            logger.info(f"Successfully synced {sync_count} conversations to Supabase")

        except Exception as e:
            logger.error(f"Error in sync process: {str(e)}")

# Create a global instance to maintain your existing pattern
conversation_service = ConversationHistoryService()