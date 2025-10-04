import logging
import os
from auth.user import get_current_user_with_subscription
from crud.research_crud import insert_article_from_url_to_supabase
from schema.pydantic_models import QuestionResponse, TextInput, URLImportRequest, URLImportResponse
from utility.ingest import chunk_text, create_embeddings, create_faiss_index, generate_questions_from_chunks, retrieve_relevant_chunks
from utility.llm_utils import get_available_llm, load_huggingface_llm
from utility.extract_url_content import extract_content_from_url
import trafilatura
import json
from datetime import datetime
from fastembed import TextEmbedding
from fastapi import FastAPI, HTTPException, Depends,APIRouter
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
        
         # Optional: Add extracted metadata if available
        if extracted_data.get('date'):
            print("yes")
            pass
        
        # Prepare article data for Supabase
        article_data = {
            "title": extracted_data.get('title', 'Untitled Article'),
            "content": extracted_data.get('text', ''),
            "author_id": user.id,
            "url": url_str,
            "is_published": False,  
            "saved": True,
            "category_id": None,
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
        }
        
       

        result = insert_article_from_url_to_supabase(article_data)

        if not result.data:
                raise HTTPException(
                    status_code=500, 
                    detail="Failed to insert article into database"
                )
        article = result.data[0]
        logger.info(f"Successfully imported article: {article['id']}")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in import_article_from_url: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"An unexpected error occurred: {str(e)}"
        )
    
@router.post("/generate-questions", response_model=QuestionResponse)
async def generate_questions(input_data: TextInput):
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

