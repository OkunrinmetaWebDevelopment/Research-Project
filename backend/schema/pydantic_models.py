from pydantic import BaseModel, HttpUrl,Field, field_validator
from datetime import datetime, time, timedelta
from uuid import UUID
import os
from typing import List, Optional

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