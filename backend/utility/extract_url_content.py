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
  
   


