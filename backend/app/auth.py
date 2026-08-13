from fastapi import Request, HTTPException, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from appwrite.client import Client
from appwrite.services.account import Account
from appwrite.exception import AppwriteException
import os

security = HTTPBearer()

def get_appwrite_client(jwt_token: str):
    client = Client()
    client.set_endpoint(os.getenv("PUBLIC_APPWRITE_ENDPOINT", "https://appwrite.bogazici.app/v1"))
    client.set_project(os.getenv("PUBLIC_APPWRITE_PROJECT_ID", "boun-archive"))
    client.set_jwt(jwt_token)
    return client

async def get_current_user(credentials: HTTPAuthorizationCredentials = Security(security)):
    token = credentials.credentials
    if not token:
        raise HTTPException(status_code=401, detail="Invalid authentication credentials")
    
    client = get_appwrite_client(token)
    account = Account(client)
    
    try:
        user = account.get()
        return user
    except AppwriteException as e:
        raise HTTPException(status_code=401, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
