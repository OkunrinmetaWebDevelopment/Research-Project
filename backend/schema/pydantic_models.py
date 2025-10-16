from pydantic import BaseModel, HttpUrl,Field, field_validator,ConfigDict
from datetime import datetime, time, timedelta
from uuid import UUID
from langchain_community.vectorstores import FAISS
import os
from typing import Any, Dict, List, Optional, Union

# Pydantic models
class URLImportRequest(BaseModel):
    url: HttpUrl


class URLImportResponse(BaseModel):
    success: bool
    article_id: str = None
    title: str = None
    message: str = None

class TextInput(BaseModel):
    text: str = Field(..., description="The text to generate questions from", min_length=10)
    num_questions: int = Field(default=5, description="Number of questions to generate", ge=1, le=20)
    chunk_size: int = Field(default=300, description="Size of text chunks in tokens", ge=50, le=1000)
    chunk_overlap: int = Field(default=50, description="Overlap between chunks", ge=0, le=200)
    
    @field_validator('chunk_overlap')
    @classmethod
    def validate_overlap(cls, v, info):
        chunk_size = info.data.get('chunk_size', 300)
        if v >= chunk_size:
            raise ValueError(f"chunk_overlap ({v}) must be less than chunk_size ({chunk_size}) to avoid infinite loops")
        return v


class QuestionResponse(BaseModel):
    questions: List[str]
    chunks_used: int
    model: str
    metadata: Optional[dict] = None

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
                ]
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


# New Pydantic models for Q&A
class QuestionAnswerInput(BaseModel):
    text: str = Field(..., description="The text content to search for answers", min_length=10)
    question: str = Field(..., description="The question to answer", min_length=5)
    chunk_size: int = Field(default=300, description="Size of text chunks in tokens", ge=50, le=1000)
    chunk_overlap: int = Field(default=50, description="Overlap between chunks", ge=0, le=200)
    top_k: int = Field(default=3, description="Number of relevant chunks to retrieve", ge=1, le=10)
    include_sources: bool = Field(default=True, description="Include source chunks in response")
    
    @field_validator('chunk_overlap')
    @classmethod
    def validate_overlap(cls, v, info):
        chunk_size = info.data.get('chunk_size', 300)
        if v >= chunk_size:
            raise ValueError(f"chunk_overlap ({v}) must be less than chunk_size ({chunk_size})")
        return v


class AnswerResponse(BaseModel):
    answer: str
    question: str
    chunks_used: int
    model: str
    sources: Optional[List[dict]] = None
    metadata: dict