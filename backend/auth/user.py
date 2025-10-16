import logging
import os
from supabase import create_client, Client
from fastapi import HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

# Load environment variables
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
# Use your service role key here (keep it secret!)
supabase: Client = create_client(
    "https://tbtjwrklpnonueytzbsx.supabase.co",  # Update this
    SUPABASE_SERVICE_ROLE_KEY
)
security = HTTPBearer()

async def get_current_user_with_subscription(credentials: HTTPAuthorizationCredentials = Depends(security)):
    try:
        token = credentials.credentials
        print(token)
        user = supabase.auth.get_user(token)
        print(user)
        if not user or not user.user:
            raise HTTPException(status_code=401, detail="Invalid token")
        return user.user
    except Exception as e:
        raise HTTPException(status_code=401, detail="Invalid token")
