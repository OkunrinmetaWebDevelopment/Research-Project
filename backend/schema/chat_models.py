from datetime import datetime

from pydantic import BaseModel, Field, ConfigDict
from typing import Any, Dict, List, Union
from uuid import UUID
from typing import Optional
from langchain_community.vectorstores import FAISS
from langchain_core.messages import AIMessage, HumanMessage




class Message(BaseModel):
    role: str  # e.g., "user", "assistant", "system"
    content: str  # The actual content of the message

class ConversationHistoryEntry(BaseModel):
    conversation_history: List[Message]
    timestamp: datetime

class ConversationResponse(BaseModel):
    conversation_id: str
    title: str
    last_updated: datetime
    messages: List[ConversationHistoryEntry]

class ConversationBasicInfo(BaseModel):
    conversation_id: str
    title: str
    last_updated: datetime

class ConversationsListResponse(BaseModel):
    conversations: List[ConversationBasicInfo]
    total_conversations: int

class QueryRequest(BaseModel):
    user_question: Union[str, None]
    conversation_history: List  # List of Message objects
    convo_type:str = None  # Optional description

    class Config:
        from_attributes = True  # Optional if you're loading from ORM attributes
        json_schema_extra = {
            "example": {
                "user_question": "What is the Economic Development Board?",
                "conversation_history": [
                    {
                        "role": "user",
                        "content": "Tell me about the Economic Development Board."
                    },
                    {
                        "role": "assistant",
                        "content": "The Economic Development Board is a government agency that helps promote economic growth."
                    },
                    {
                        "role": "user",
                        "content": "Can you give more details?"
                    }
                ],
                "convo_type":"temp"
            }
        }

class ChatRequest(BaseModel):
    user_question: str
    conversation_history: List = []

class ChatRequestWeb(BaseModel):
    url: Union[str, None]
    user_question: Union[str, None]
    conversation_history: List  # List of Message objects

    class Config:
        from_attributes = True  # Optional if you're loading from ORM attributes
        json_schema_extra = {
            "example": {
                "url":"https://www.nyulawglobal.org/globalex/Mauritius.html",
                "user_question": "What are the Branches of Law in Mauritius?",
                "conversation_history": [
                    {
                        "role": "assistant",
                        "content": "How can i help you today?."
                    },
                    {
                        "role": "user",
                        "content": "Can you give more information on Mauritian Law"
                    }
                ]
            }
        }


class SummarizeRequest(BaseModel):
    url: Union[str, None]

    class Config:
        from_attributes = True  # Optional if you're loading from ORM attributes
        json_schema_extra = {
            "example": {
                "url": "https://www.mauritius.net/the-birdwatchers-guide-to-mauritius/",
            }
        }


class ConversationHistoryRequest(BaseModel):
    conversation_history: List[dict]

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "user_id": 1,
                "conversation_history": [
                    {
                        "role": "user",
                        "content": "Tell me about the Economic Development Board."
                    },
                    {
                        "role": "assistant",
                        "content": "The Economic Development Board is a government agency..."
                    }
                ]
            }
        }

class ConversationHistoryDbRequest(ConversationHistoryRequest):
    conversation_id: str

    class Config:
        from_attributes = True

# class ConversationHistoryRequest(BaseModel):
#     conversation_history: List[Union[AIMessage, HumanMessage]]

class ModelBase(BaseModel):
    name: str
    description: str = None  # Optional description

class CreateModel(ModelBase):
    pass

    

class ModelInDB(ModelBase):
    id: int

    class Config:
        from_attributes = True


class UpdateCurrentModel(BaseModel):
    current_model_name: Optional[str]  # Optional to allow partial updates



class CurrentUsedModelCreate(BaseModel):
    model_id: int

    class Config:
        orm_mode = True

class CurrentUsedModelInDB(BaseModel):
    model_id: int

    class Config:
        orm_mode = True


class ConversationData(BaseModel):
    user_id: int
    conversation_id: Optional[str] = None
    conversation_name:Optional[str] = None
    redis_conversation_id: str
    conversation_history: List[Dict[str, Any]]
    last_updated:Optional[datetime] = None

class CurrentConversationResponse(BaseModel):
    conversation_id: Optional[str]
    conversation_name: Optional[str]
    last_updated: Optional[datetime]

    class Config:
        from_attributes = True

class VectorStoreResult(BaseModel):
    vector_store: Optional[FAISS] = None
    message: str
    success: bool

    model_config = ConfigDict(arbitrary_types_allowed=True)