import logging
import os
import shutil
import tempfile
from typing import List, Optional
from auth.user import get_current_user_with_subscription
from schema.file_schema import DocumentCategory, DocumentUploadResponse
from crud.research_crud import extract_content_from_url, extract_text_from_pdf, insert_article_from_pdf_to_supabase, insert_article_from_url_to_supabase, validate_file_size, validate_pdf_file
from schema.pydantic_models import AnswerResponse, QuestionAnswerInput, QuestionResponse, TextInput, URLImportRequest, URLImportResponse
from utility.ingest import answer_question_from_text, chunk_text, create_embeddings, create_faiss_index, generate_questions_from_chunks, retrieve_relevant_chunks
from utility.llm_utils import get_available_llm, load_huggingface_llm
import trafilatura
import json
from datetime import datetime
from fastembed import TextEmbedding
from fastapi import FastAPI, HTTPException, Depends, File, UploadFile, Form, BackgroundTasks,APIRouter
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, HttpUrl
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/research",
    tags=['Research']
)

@router.post("/import-article", response_model=URLImportResponse)
async def import_article_from_url(
    request: URLImportRequest,
    user = Depends(get_current_user_with_subscription)
):
    """
    Extract content from a URL and save it as an article
    
    - **url**: The URL to extract content from
    - Returns the created article ID and details
    """
    try:
        url_str = str(request.url)
        logger.info(f"Processing URL import request: {url_str} for user: {user.id}")
        
        # Extract content from URL
        try:
            extracted_data = extract_content_from_url(url_str)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        
        # Prepare article data for Supabase
        article_data = {
            "title": extracted_data.get('title', 'Untitled Article'),
            "content": extracted_data.get('text', ''),
            "author_id": str(user.id),  # Convert to string for UUID
            "url": url_str,
            "is_published": False,  
            "saved": True,
            "category_id": None,
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
        }
        
        # FIXED: Added await keyword
        result = await insert_article_from_url_to_supabase(article_data)
        
        return result
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in import_article_from_url: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"An unexpected error occurred: {str(e)}"
        )
    

@router.post("/generate-questions", response_model=QuestionResponse)
async def generate_questions(input_data: TextInput, user = Depends(get_current_user_with_subscription)):
    """
    Generate possible questions from the provided text using RAG.
    
    This endpoint:
    1. Chunks the input text
    2. Creates embeddings using FastEmbed
    3. Builds an in-memory FAISS vector index
    4. Retrieves relevant chunks
    5. Uses an LLM to generate questions based on the chunks
    """
    try:
        try:
            llm, model_name = get_available_llm()
        except ValueError as e:
            raise HTTPException(
                status_code=503,
                detail=f"LLM service unavailable: {str(e)}"
            )
        
        embedding_model = TextEmbedding(model_name="BAAI/bge-small-en-v1.5")
        
        chunks = chunk_text(
            input_data.text,
            chunk_size=input_data.chunk_size,
            overlap=input_data.chunk_overlap
        )
        
        if not chunks:
            raise HTTPException(status_code=400, detail="Failed to chunk the text")
        
        embeddings = create_embeddings(chunks, embedding_model)
        
        faiss_index = create_faiss_index(embeddings)
        
        top_k = min(3, len(chunks))
        query = "What questions can be asked about this content?"
        relevant_chunks = retrieve_relevant_chunks(
            query, chunks, faiss_index, embedding_model, top_k=top_k
        )
        
        questions = generate_questions_from_chunks(
            relevant_chunks,
            llm,
            num_questions=input_data.num_questions
        )
        
        if not questions:
            raise HTTPException(
                status_code=500,
                detail="No questions were generated. Please try again or provide different text."
            )
        
        return QuestionResponse(
            questions=questions,
            chunks_used=len(relevant_chunks),
            model=model_name,
            metadata={
                "total_chunks": len(chunks),
                "embedding_dimension": embeddings.shape[1]
            }
        )
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")



@router.post("/upload-pdf-article")
async def upload_pdf_article(
    file: UploadFile = File(...),
    title: Optional[str] = Form(None),
    category_id: Optional[str] = Form(None),
    is_published: bool = Form(False),
    current_user = Depends(get_current_user_with_subscription)
):
    """
    Upload a PDF file, extract content, and save as an article
    
    - **file**: PDF file to upload
    - **title**: Optional title (if not provided, uses filename)
    - **category_id**: Optional category UUID
    - **is_published**: Whether to publish the article immediately
    - Returns the created article details
    """
    try:
        # Validate filename
        if not file.filename:
            raise HTTPException(status_code=400, detail="Filename missing")
        
        # Validate file type
        if not validate_pdf_file(file.filename):
            raise HTTPException(
                status_code=400,
                detail="Only PDF files are supported"
            )
        
        # Read file content
        file_content = await file.read()
        
        # Validate file size
        if not validate_file_size(len(file_content)):
            raise HTTPException(
                status_code=400,
                detail="File exceeds size limit (10MB)"
            )
        
        # Extract text from PDF
        try:
            extracted_text = extract_text_from_pdf(file_content)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        
        # Use provided title or derive from filename
        article_title = title if title else os.path.splitext(file.filename)[0]
        
        # Prepare article data for Supabase
        article_data = {
            "title": article_title,
            "content": extracted_text,
            "author_id": str(current_user.id),
            "category_id": category_id,
            "is_published": is_published,
            "saved": True,
            "url": None,
            "published_at": datetime.utcnow().isoformat() if is_published else None,
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
            "upvotes": 0,
            "downvotes": 0
        }
        
        # Insert into database
        article = await insert_article_from_pdf_to_supabase(article_data)
        
        return {
            "success": True,
            "article_id": article['id'],
            "title": article['title'],
            "content_length": len(extracted_text),
            "message": "PDF article uploaded and saved successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in upload_pdf_article: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"An unexpected error occurred: {str(e)}"
        )


@router.post("/upload-pdf-articles-batch")
async def upload_pdf_articles_batch(
    files: List[UploadFile] = File(...),
    category_id: Optional[str] = Form(None),
    is_published: bool = Form(False),
    current_user = Depends(get_current_user_with_subscription)
):
    """
    Upload multiple PDF files and save each as a separate article
    
    - **files**: List of PDF files to upload
    - **category_id**: Optional category UUID (applied to all articles)
    - **is_published**: Whether to publish articles immediately
    - Returns list of created article details
    """
    results = []
    errors = []
    
    for file in files:
        try:
            # Validate file
            if not file.filename or not validate_pdf_file(file.filename):
                errors.append({
                    "filename": file.filename or "unknown",
                    "error": "Invalid file type"
                })
                continue
            
            # Read and validate size
            file_content = await file.read()
            if not validate_file_size(len(file_content)):
                errors.append({
                    "filename": file.filename,
                    "error": "File exceeds size limit"
                })
                continue
            
            # Extract text
            try:
                extracted_text = extract_text_from_pdf(file_content)
            except ValueError as e:
                errors.append({
                    "filename": file.filename,
                    "error": str(e)
                })
                continue
            
            # Prepare article data
            article_title = os.path.splitext(file.filename)[0]
            article_data = {
                "title": article_title,
                "content": extracted_text,
                "author_id": str(current_user.id),
                "category_id": category_id,
                "is_published": is_published,
                "saved": True,
                "url": None,
                "published_at": datetime.utcnow().isoformat() if is_published else None,
                "created_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat(),
                "upvotes": 0,
                "downvotes": 0
            }
            
            # Insert into database
            article = await insert_article_from_pdf_to_supabase(article_data)
            
            results.append({
                "success": True,
                "filename": file.filename,
                "article_id": article['id'],
                "title": article['title'],
                "content_length": len(extracted_text)
            })
            
        except Exception as e:
            logger.error(f"Error processing {file.filename}: {str(e)}")
            errors.append({
                "filename": file.filename,
                "error": str(e)
            })
    
    return {
        "successful": len(results),
        "failed": len(errors),
        "results": results,
        "errors": errors
    }