# Enums for file categories
from datetime import datetime
from enum import Enum
from typing import List, Optional, Dict

from pydantic import BaseModel, Field


class DocumentCategory(str, Enum):
    LEGAL = "legal"
    POLICY = "policy"
    RESEARCH = "research"
    REPORT = "report"
    CONTRACT = "contract"
    PRESENTATION = "presentation"
    SPREADSHEET = "spreadsheet"
    IMAGE = "image"
    VIDEO = "video"
    AUDIO = "audio"
    ARCHIVE = "archive"
    OTHER = "other"

class FileType(str, Enum):
    PDF = "pdf"
    DOC = "doc"
    DOCX = "docx"
    TXT = "txt"
    XLS = "xls"
    XLSX = "xlsx"
    PPT = "ppt"
    PPTX = "pptx"
    JPG = "jpg"
    JPEG = "jpeg"
    PNG = "png"
    GIF = "gif"
    MP4 = "mp4"
    AVI = "avi"
    MP3 = "mp3"
    WAV = "wav"
    ZIP = "zip"
    RAR = "rar"
    OTHER = "other"

# Pydantic Models
class FilePathBase(BaseModel):
    user_id: str = Field(..., description="User ID who owns the file")
    file_id: str = Field(..., description="Unique file identifier")
    file_name: str = Field(..., min_length=1, max_length=255, description="Original file name")

class FilePathCreate(FilePathBase):
    """Model for creating a new file path record"""
    pass

class FilePathUpdate(BaseModel):
    """Model for updating file path record"""
    file_name: Optional[str] = Field(None, min_length=1, max_length=255)
    # Note: user_id and file_id typically shouldn't be updated after creation

class FilePathResponse(FilePathBase):
    """Model for file path responses"""
    id: str = Field(..., description="Database record ID")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")

    class Config:
        from_attributes = True

class FilePathListResponse(BaseModel):
    """Model for paginated file path list responses"""
    data: List[FilePathResponse]
    count: Optional[int] = None
    total_pages: Optional[int] = None
    current_page: int
    page_size: int

# Extended models for document upload (matching your existing structure)
class DocumentUploadRequest(BaseModel):
    """Model for document upload requests"""
    title: str = Field(..., min_length=1, max_length=255, description="Document title")
    description: Optional[str] = Field(None, max_length=1000, description="Document description")
    category: DocumentCategory = Field(..., description="Document category")
    tags: Optional[List[str]] = Field(None, description="Document tags")
    original_file_name: Optional[str] = Field(None, description="Original filename")

class DocumentUploadResponse(BaseModel):
    """Model for document upload responses"""
    title: str
    category: DocumentCategory
    tags: Optional[List[str]]
    document_s3_url: Optional[str] = None
    original_file_name: str
    document_id: str
    file_path_record: Optional[FilePathResponse] = None

class FileMetadata(BaseModel):
    """Model for file metadata"""
    file_size: Optional[int] = Field(None, description="File size in bytes")
    file_type: Optional[str] = Field(None, description="File type/extension")
    mime_type: Optional[str] = Field(None, description="MIME type")
    checksum: Optional[str] = Field(None, description="File checksum")

class FileStatsResponse(BaseModel):
    """Model for file statistics"""
    total_files: int
    files_by_user: Dict[str, int]
    files_by_extension: Dict[str, int]
    total_storage_used: Optional[int] = None
    recent_uploads: List[FilePathResponse]