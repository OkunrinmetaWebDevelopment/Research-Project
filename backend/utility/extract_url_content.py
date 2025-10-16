import trafilatura
import json
import logging
import os
import json
from datetime import datetime
from fastapi import FastAPI, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, HttpUrl
from supabase import create_client, Client
from dotenv import load_dotenv
load_dotenv()

logger = logging.getLogger()



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
    

def store_files_in_temp_path_lc_dir(files,user,db):
    logger.info("Creating a temporary directory")
    upload_directory = tempfile.mkdtemp()

    for file in files:
        file_upload = FileUplodBase(file_name=file.filename, file_id=generate_unique_id())
        # insert_file_path(file_upload, user, db)
        file_location = os.path.join(upload_directory, file.filename)
        with open(file_location, "wb+") as file_object:
            shutil.copyfileobj(file.file, file_object)

    return upload_directory
  
   


