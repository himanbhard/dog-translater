import logging
import os
from typing import Any, Dict

from fastapi import FastAPI, File, UploadFile, HTTPException, Form, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles

from .config import get_settings
from .bedrock_client import analyze_image as analyze_with_bedrock, _parse_json_fallback
from .storage import init_db  # legacy init for backward compat
from .db.deps import get_repo
from .db.interfaces import Repository
import uuid

# Basic logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

app = FastAPI(title="Dog Body Language Interpreter")

# Dev CORS (adjust origins for production)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def index() -> FileResponse:
    # Serve the frontend directly from the backend container.
    return FileResponse("src/frontend/index.html")

# Optional: serve static assets if added later
app.mount("/static", StaticFiles(directory="src/frontend"), name="static")

@app.get("/health")
def health() -> Dict[str, Any]:
    return {"status": "ok"}

@app.on_event("startup")
def startup_event() -> None:
    # Initialize legacy SQLite storage (no-op if not present) and apply new DAL migrations
    try:
        init_db()
    except Exception:
        pass
    # Ensure DB repo exists and migrations are applied
    try:
        repo = get_repo()
        repo.apply_migrations()
        
        # Test User Initialization
        test_email = "test@example.com"
        if not repo.get_user_by_email(test_email):
            from .auth import get_password_hash
            repo.create_user(test_email, get_password_hash("password123"))
            logger.info("Test user created: %s", test_email)
            
    except Exception as e:
        logger.exception("DB init/migrations failed: %s", e)

# --- Services ---
from .services.interpreter import InterpretationService
from .auth import Token, create_access_token, get_current_user, TokenData, get_password_hash, verify_password
from fastapi.security import OAuth2PasswordRequestForm
from datetime import timedelta
from pydantic import BaseModel

interpreter_service = InterpretationService()

# --- Auth Models ---
class LoginRequest(BaseModel):
    email: str
    password: str

class UserResponse(BaseModel):
    id: str
    email: str
    is_verified: bool

class AuthResponse(BaseModel):
    user: UserResponse
    access_token: str
    token_type: str = "bearer"

# --- Auth Endpoints (V1) ---

@app.post("/auth/login", response_model=AuthResponse)
async def login(req: LoginRequest, repo: Repository = Depends(get_repo)):
    """
    Hybrid Flow:
    - If user exists -> Verify Password
    - If user does not exist -> Create User (Sign Up)
    """
    user = repo.get_user_by_email(req.email)
    
    if user:
        # Authenticate
        if not verify_password(req.password, user.password_hash):
            raise HTTPException(status_code=400, detail="Incorrect password")
    else:
        # Sign Up
        dashed = get_password_hash(req.password)
        # Create user with verified=True by default for now
        user = repo.create_user(email=req.email, password_hash=dashed)

    # Generate Token
    access_token_expires = timedelta(minutes=60 * 24) # 24 hours
    access_token = create_access_token(
        data={"sub": user.email, "uid": user.id}, expires_delta=access_token_expires
    )
    
    return {
        "user": {
            "id": user.id,
            "email": user.email,
            "is_verified": user.is_verified
        },
        "access_token": access_token,
        "token_type": "bearer"
    }

@app.get("/auth/google")
async def google_auth():
    """
    TODO: Implement Google Social Login.
    Likely usage: Redirect to Google OAuth URL, handle callback,
    exchange code for token, upsert user in DB.
    """
    return {"status": "todo", "message": "Google Auth not implemented yet"}

# Keep this for Swagger UI compatibility if needed, distinct from the app login
@app.post("/api/v1/auth/token", response_model=Token)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), repo: Repository = Depends(get_repo)):
    user = repo.get_user_by_email(form_data.username)
    if not user:
         # Auto-signup for Swagger simply? No, let's just fail or auto-create if we want consistency.
         # For safety, let's fail standard oauth flow if user doesn't exist, to discourage accidental signups
         # OR, stick to the hybrid logic if we want consistency.
         # Let's fail secure for the strict OAuth endpoint.
        raise HTTPException(status_code=400, detail="Incorrect username or password")
    
    if not verify_password(form_data.password, user.password_hash):
        raise HTTPException(status_code=400, detail="Incorrect username or password")

    access_token_expires = timedelta(minutes=60)
    access_token = create_access_token(
        data={"sub": user.email, "uid": user.id}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}


@app.get("/api/v1/me", response_model=TokenData)
async def read_users_me(current_user: TokenData = Depends(get_current_user)):
    return current_user


# --- V1 API (Mobile Ready) ---

@app.post("/api/v1/interpret")
async def interpret_dog_body_language_v1(
    image: UploadFile = File(...),
    tone: str | None = Form(None),
    save: bool = Form(False),
    repo: Repository = Depends(get_repo),
    current_user: TokenData = Depends(get_current_user), # Require Auth for V1
) -> JSONResponse:
    return await _handle_interpret(image, tone, save, repo)


# --- Legacy API (Web Compatibility) ---

@app.post("/api/interpret")
async def interpret_dog_body_language(
    image: UploadFile = File(...),
    tone: str | None = Form(None),
    save: bool = Form(False),
    repo: Repository = Depends(get_repo),
) -> JSONResponse:
    # Legacy endpoint does not require Auth
    return await _handle_interpret(image, tone, save, repo)


async def _handle_interpret(image: UploadFile, tone: str | None, save: bool, repo: Repository) -> JSONResponse:
    logger.info("Received upload: filename=%s content_type=%s", image.filename, image.content_type)

    if image.content_type not in {"image/jpeg", "image/png"}:
        raise HTTPException(status_code=400, detail="Unsupported file type. Please upload JPEG or PNG.")

    settings = get_settings()
    data = await image.read()

    if len(data) > settings.max_upload_bytes:
        raise HTTPException(status_code=413, detail=f"Image too large. Max {settings.max_upload_bytes} bytes.")

    try:
        # Use Service Layer
        result = interpreter_service.interpret(
            image_bytes=data,
            mime_type=image.content_type,
            tone=tone,
            repo=repo,
            save=save
        )
        
        logger.info("Responding with success (source=%s): confidence=%.2f", result["source"], result["confidence"])
        return JSONResponse(content=result, headers={"X-LLM-Source": result["source"]})
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Service call failed: %s", e)
        return JSONResponse(
            status_code=502,
            content={
                "status": "error",
                "explanation": "Unable to interpret the image right now.",
                "confidence": 0.0,
                "error": "upstream_failure",
            },
        )

@app.get("/api/share/{share_id}")
def get_shared_interpretation(share_id: str) -> JSONResponse:
    repo = get_repo()
    inter = repo.get_interpretation(share_id)
    if not inter:
        raise HTTPException(status_code=404, detail="Not found")
    _id = inter.id
    explanation = inter.explanation
    confidence = inter.confidence
    created_at = inter.created_at
    return JSONResponse(
        content={
            "id": _id,
            "explanation": explanation,
            "confidence": confidence,
            "created_at": created_at,
        }
    )

@app.get("/share/{share_id}")
def share_page(share_id: str) -> HTMLResponse:
    repo = get_repo()
    inter = repo.get_interpretation(share_id)
    if not inter:
        raise HTTPException(status_code=404, detail="Not found")
    _id = inter.id
    explanation = inter.explanation
    confidence = inter.confidence
    created_at = inter.created_at
    pct = round(float(confidence) * 100)
    html = f"""
    <!doctype html>
    <html><head><meta charset='utf-8'><title>Shared Dog Interpretation</title>
    <meta name='viewport' content='width=device-width, initial-scale=1'>
    <style>body{{font-family: -apple-system, ui-sans-serif; margin:20px; color:#0b1220}} .card{{max-width:720px;margin:0 auto;border:1px solid #ddd;border-radius:12px;padding:16px}} .muted{{color:#555}}</style>
    </head><body>
      <div class='card'>
        <h2>Dog says:</h2>
        <div style='white-space: pre-wrap'>{explanation}</div>
        <div class='muted' style='margin-top:8px'>Confidence: {pct}% &middot; Created: {created_at}</div>
        <div class='muted' style='margin-top:12px'>Share ID: {_id}</div>
      </div>
    </body></html>
    """
    return HTMLResponse(content=html)

@app.get("/api/registry")
def api_registry() -> JSONResponse:
    """Return structured, searchable API documentation for this service."""
    registry: Dict[str, Any] = {
        "service": {
            "name": "Dog Body Language Interpreter",
            "version": "1.1",
        },
        "endpoints": [
            {
                "name": "Root",
                "path": "/",
                "methods": ["GET"],
                "summary": "Serves the single-page frontend.",
                "params": [],
                "response_example": {
                    "type": "html",
                    "description": "index.html"
                },
                "tags": ["frontend"],
            },
            {
                "name": "Health",
                "path": "/health",
                "methods": ["GET"],
                "summary": "Basic health check.",
                "params": [],
                "response_example": {"status": "ok"},
                "tags": ["ops"],
            },
            {
                "name": "Interpret Image (Legacy)",
                "path": "/api/interpret",
                "methods": ["POST"],
                "summary": "Legacy endpoint. Use /api/v1/interpret for mobile.",
                "deprecated": True,
            },
             {
                "name": "Interpret Image (V1)",
                "path": "/api/v1/interpret",
                "methods": ["POST"],
                "summary": "Uploads a dog image and returns a friendly first-person explanation (Requires Auth).",
                "params": [
                    {
                        "name": "image",
                        "in": "formData",
                        "type": "file",
                        "required": True,
                        "mime": ["image/jpeg", "image/png"],
                    },
                    {
                        "name": "tone",
                        "in": "formData",
                        "type": "string",
                        "required": False,
                        "enum": ["playful", "calm", "trainer"],
                    },
                ],
                "tags": ["interpretation", "mobile"],
            },
            {
                "name": "Get Token",
                "path": "/api/v1/auth/token",
                "methods": ["POST"],
                "summary": "Exchange credentials for JWT.",
            },
        ],
    }
    return JSONResponse(content=registry)
