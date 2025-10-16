import logging
import os
from schema.pydantic_models import URLImportResponse
import trafilatura
import json
from datetime import datetime
from fastapi import HTTPException
from supabase import create_client, Client
from dotenv import load_dotenv
import PyPDF2
from io import BytesIO

load_dotenv()

logger = logging.getLogger()

# Supabase setup
SUPABASE_URL = os.getenv("SUPABASE_URL", "https://tbtjwrklpnonueytzbsx.supabase.co")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

if not SUPABASE_SERVICE_ROLE_KEY:
    raise ValueError("SUPABASE_SERVICE_ROLE_KEY environment variable is required")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)


def extract_content_from_url(url: str) -> dict:
    """
    Extract article content from URL using trafilatura
    
    Args:
        url: The URL to extract content from
        
    Returns:
        dict: Extracted content with metadata
        
    Raises:
        ValueError: If extraction fails
    """
    try:
        # Download the content
        downloaded = trafilatura.fetch_url(url)
        
        if not downloaded:
            raise ValueError(f"Failed to download content from URL: {url}")
        
        # Extract content with metadata
        result = trafilatura.extract(
            downloaded,
            include_comments=False,
            include_tables=True,
            output_format='json',
            with_metadata=True
        )
        
        if not result:
            raise ValueError("Failed to extract content from the downloaded page")
        
        # Parse JSON result
        data = json.loads(result)
        
        # Validate required fields
        if not data.get('title'):
            data['title'] = data.get('sitename', 'Untitled Article')
        
        if not data.get('text'):
            raise ValueError("No text content could be extracted from the URL")
        
        logger.info(f"Successfully extracted content from {url}")
        return data
        
    except json.JSONDecodeError as e:
        logger.error(f"JSON parsing error: {str(e)}")
        raise ValueError("Failed to parse extracted content")
    except Exception as e:
        logger.error(f"Content extraction error: {str(e)}")
        raise ValueError(f"Content extraction failed: {str(e)}")


def extract_text_from_pdf(file_content: bytes) -> str:
    """
    Extract text content from PDF file
    
    Args:
        file_content: PDF file content as bytes
        
    Returns:
        str: Extracted text content
        
    Raises:
        ValueError: If extraction fails
    """
    try:
        pdf_file = BytesIO(file_content)
        pdf_reader = PyPDF2.PdfReader(pdf_file)
        
        if len(pdf_reader.pages) == 0:
            raise ValueError("PDF file has no pages")
        
        # Extract text from all pages
        text_content = []
        for page_num, page in enumerate(pdf_reader.pages):
            try:
                text = page.extract_text()
                if text.strip():
                    text_content.append(text)
            except Exception as e:
                logger.warning(f"Failed to extract text from page {page_num}: {str(e)}")
                continue
        
        if not text_content:
            raise ValueError("No text content could be extracted from PDF")
        
        full_text = "\n\n".join(text_content)
        logger.info(f"Successfully extracted {len(full_text)} characters from PDF")
        
        return full_text
        
    except PyPDF2.errors.PdfReadError as e:
        logger.error(f"PDF reading error: {str(e)}")
        raise ValueError("Invalid or corrupted PDF file")
    except Exception as e:
        logger.error(f"PDF extraction error: {str(e)}")
        raise ValueError(f"PDF extraction failed: {str(e)}")


def validate_file_size(size: int, max_size_mb: int = 10) -> bool:
    """Validate file size doesn't exceed limit"""
    max_bytes = max_size_mb * 1024 * 1024
    return size <= max_bytes


def validate_pdf_file(filename: str) -> bool:
    """Validate file is a PDF"""
    return filename.lower().endswith('.pdf')


async def insert_article_from_url_to_supabase(article_data: dict):
    """
    Extract content from a URL and save it as an article
    
    Args:
        article_data: Dictionary containing article fields
        
    Returns:
        URLImportResponse with article details
        
    Raises:
        HTTPException: If database insertion fails
    """
    try:
        result = supabase.table('articles').insert(article_data).execute()
        
        if not result.data:
            raise HTTPException(
                status_code=500, 
                detail="Failed to insert article into database"
            )
        
        article = result.data[0]
        logger.info(f"Successfully imported article: {article['id']}")
        
        return URLImportResponse(
            success=True,
            article_id=article['id'],
            title=article['title'],
            message="Article imported successfully"
        )
        
    except Exception as e:
        logger.error(f"Database insertion error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to save article: {str(e)}"
        )


async def insert_article_from_pdf_to_supabase(article_data: dict):
    """
    Insert article data into Supabase articles table
    
    Args:
        article_data: Dictionary containing article fields
        
    Returns:
        dict: Inserted article data
        
    Raises:
        HTTPException: If database insertion fails
    """
    try:
        result = supabase.table('articles').insert(article_data).execute()
        
        if not result.data:
            raise HTTPException(
                status_code=500,
                detail="Failed to insert article into database"
            )
        
        article = result.data[0]
        logger.info(f"Successfully inserted article: {article['id']}")
        
        return article
        
    except Exception as e:
        logger.error(f"Database insertion error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to save article: {str(e)}"
        )