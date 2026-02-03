from datetime import datetime, timedelta
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel
import os
import firebase_admin
from firebase_admin import auth, credentials

from .config import get_settings

# Models
class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: Optional[str] = None
    uid: Optional[str] = None

# Logic
pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/v1/auth/token")

# Initialize Firebase Admin
_settings = get_settings()
try:
    if os.path.exists(_settings.firebase_service_account_path):
        cred = credentials.Certificate(_settings.firebase_service_account_path)
        firebase_admin.initialize_app(cred)
    else:
        # Fallback to default credentials (useful for Cloud Run with Service Account)
        firebase_admin.initialize_app()
except Exception as e:
    print(f"Firebase admin initialization warning: {e}")

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    settings = get_settings()
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)
    return encoded_jwt

async def get_current_user(token: str = Depends(oauth2_scheme)):
    settings = get_settings()
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    # Try Firebase Token Verification first
    try:
        decoded_token = auth.verify_id_token(token)
        uid = decoded_token.get("uid")
        email = decoded_token.get("email")
        
        # Auto-provision user in local DB if needed
        from .db.deps import get_repo
        repo = get_repo()
        if not repo.get_user_by_email(email):
             repo.create_user(email, "firebase_auth") # Password hash irrelevant for Firebase users
        
        return TokenData(username=email, uid=uid)
    except Exception as e:
        # print(f"Firebase token verification failed: {e}")
        # If Firebase verification fails, try the custom JWT (for backward compat/legacy tests)
        try:
            payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
            username: str = payload.get("sub")
            uid: str = payload.get("uid")
            if username is None:
                raise credentials_exception
            return TokenData(username=username, uid=uid)
        except JWTError:
            raise credentials_exception
