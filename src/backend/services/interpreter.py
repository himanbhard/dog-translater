from __future__ import annotations
import logging
import uuid
import asyncio
from typing import Dict, Any, Optional
from ..db.interfaces import Repository

from fastapi import HTTPException

from ..config import get_settings
from ..gemini_client import analyze_image_with_gemini

logger = logging.getLogger(__name__)

class InterpretationService:
    def __init__(self):
        self.settings = get_settings()

    async def interpret(
        self,
        image_bytes: bytes,
        mime_type: str,
        tone: Optional[str] = None,
        repo: Optional['Repository'] = None,
        save: bool = False,
        user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Orchestrates the interpretation flow:
        1. Calls Gemini for analysis.
        2. Parses/Sanitizes the result.
        3. Saves to database if requested.
        """
        

        try:
            # Gemini call is synchronous, so we run it in a thread to avoid blocking the event loop.
            result = await asyncio.to_thread(
                analyze_image_with_gemini,
                image_bytes=image_bytes,
                mime_type=mime_type,
                tone=tone,
            )
            
            # 3. Parse/Sanitize
            explanation = str(result.get("explanation", "") or "").strip()

            confidence = float(result.get("confidence", 0.5))
            has_pet = result.get("has_pet", True)
            
            response: Dict[str, Any] = {
                "status": "ok",
                "explanation": explanation,
                "confidence": confidence,
                "has_pet": has_pet,
                "source": "vertex_gemini",
            }
            
            # 4. Save to DB (Persistence)
            # Only save if a pet was actually detected, or if we want to log failures too?
            # Let's save everything for now, but maybe flag it.
            if save and repo:
                share_id = uuid.uuid4().hex
                try:
                    repo.save_interpretation(share_id, explanation, confidence, user_id=user_id)
                    response["share_id"] = share_id
                except Exception as e:
                    logger.exception("Failed to save interpretation: %s", e)
            
            return response

        except HTTPException:
            raise
        except Exception as e:
            logger.exception("Vertex AI call failed in service layer: %s", e)
            raise e
