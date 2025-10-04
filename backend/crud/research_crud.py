
import logging
import os
from schema.pydantic_models import URLImportResponse
import trafilatura
import json
from datetime import datetime
from fastapi import FastAPI, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, HttpUrl
from supabase import create_client, Client
from dotenv import load_dotenv


logger = logging.getLogger()

# Supabase setup
SUPABASE_URL = os.getenv("SUPABASE_URL", "https://tbtjwrklpnonueytzbsx.supabase.co")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

if not SUPABASE_SERVICE_ROLE_KEY:
    raise ValueError("SUPABASE_SERVICE_ROLE_KEY environment variable is required")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)


async def insert_article_from_url_to_supabase(article_data:dict):
    """
    Extract content from a URL and save it as an article
    
    - **url**: The URL to extract content from
    - Returns the created article ID and details
    """
        
        # Insert into Supabase
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
            
