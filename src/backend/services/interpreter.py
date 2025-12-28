import logging
import uuid
from typing import Dict, Any, Optional

from fastapi import HTTPException

from ..config import get_settings
from ..bedrock_client import analyze_image as analyze_with_bedrock, _parse_json_fallback
from ..db.interfaces import Repository

logger = logging.getLogger(__name__)

class InterpretationService:
    def __init__(self):
        self.settings = get_settings()

    def interpret(
        self,
        image_bytes: bytes,
        mime_type: str,
        tone: Optional[str] = None,
        repo: Optional[Repository] = None,
        save: bool = False
    ) -> Dict[str, Any]:
        """
        Orchestrates the interpretation flow:
        1. Checks AWS credentials.
        2. Calls Bedrock for analysis.
        3. Parses/Sanitizes the result.
        4. Saves to database if requested.
        """
        
        # 1. Credential Check
        if not self.settings.aws_access_key_id or not self.settings.aws_secret_access_key:
             raise HTTPException(status_code=500, detail="Server misconfiguration: AWS credentials not set.")

        try:
            # 2. Call Bedrock
            result = analyze_with_bedrock(
                region_name=self.settings.bedrock_region,
                model_id=self.settings.bedrock_model_id,
                image_bytes=image_bytes,
                mime_type=mime_type,
                aws_access_key_id=self.settings.aws_access_key_id,
                aws_secret_access_key=self.settings.aws_secret_access_key,
                tone=tone,
            )
            
            # 3. Parse/Sanitize
            explanation = str(result.get("explanation", "") or "").strip()
            # If the model leaked JSON into the explanation string, try to extract it
            if "{" in explanation and "}" in explanation:
                parsed = _parse_json_fallback(explanation)
                explanation = parsed.get("explanation", explanation)
                if "confidence" not in result:
                    result["confidence"] = parsed.get("confidence", 0.5)

            confidence = float(result.get("confidence", 0.5))
            
            response: Dict[str, Any] = {
                "status": "ok",
                "explanation": explanation,
                "confidence": confidence,
                "source": "bedrock",
            }
            
            # 4. Save to DB (Persistence)
            if save and repo:
                share_id = uuid.uuid4().hex
                try:
                    repo.save_interpretation(share_id, explanation, confidence)
                    response["share_id"] = share_id
                except Exception as e:
                    logger.exception("Failed to save interpretation: %s", e)
            
            return response

        except HTTPException:
            raise
        except Exception as e:
            logger.exception("Bedrock call failed in service layer: %s", e)
            # Re-raise or return a structured error? 
            # The current server implementation returned a 502 JSONResponse.
            # Services typically shouldn't return JSONResponses (that's the controller's job).
            # We'll raise a custom exception or allow the caller to handle generic exceptions.
            # For now, to match previous behavior, we'll re-raise generic exceptions and let the controller catch them.
            raise e
