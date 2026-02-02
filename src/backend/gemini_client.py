import asyncio
import logging
from typing import Dict, Any, Optional

import vertexai
from vertexai.preview.generative_models import GenerativeModel, Part, Image
import io

from .config import get_settings

logger = logging.getLogger(__name__)

# Initialize Vertex AI globally (or per-request if context varies)
_settings = get_settings()
vertexai.init(project=_settings.vertex_ai_project_id, location=_settings.vertex_ai_location)

_model = GenerativeModel("gemini-pro-vision")

async def analyze_image_with_gemini(
    image_bytes: bytes,
    mime_type: str,
    tone: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Analyzes a dog image using Google Gemini Pro Vision via Vertex AI.
    """
    try:
        # Prepare the image for Gemini
        # Vertex AI Image Part requires a GCS path or raw bytes/PIL Image
        # Since we have bytes, we'll wrap it.

        # Determine prompt based on tone
        if tone == "playful":
            tone_prompt = "Respond in a playful, first-person tone as if you are the dog. Be very enthusiastic."
        elif tone == "calm":
            tone_prompt = "Respond in a calm, reassuring, first-person tone as if you are the dog. Focus on gentle observations."
        elif tone == "trainer":
            tone_prompt = "Respond as an objective dog trainer, describing the dog's body language and offering a brief, actionable tip. Use a professional but friendly tone."
        else:
            tone_prompt = "Respond in a friendly, first-person tone as if you are the dog."

        prompt_parts = [
            Part.from_text(f"Analyze the body language of the dog in this image. {tone_prompt}."),
            Part.from_data(data=image_bytes, mime_type=mime_type),
            Part.from_text("Explain what the dog is feeling or trying to communicate. Also provide a confidence score between 0.0 and 1.0 (e.g., {\"explanation\": \"...\", \"confidence\": 0.8})."),
        ]

        logger.info("Sending image to Gemini Pro Vision...")
        responses = _model.generate_content(prompt_parts)
        await asyncio.sleep(5) # User-requested delay for rate limiting

        # --- Detailed Error Logging Start ---
        if not responses or not responses.candidates:
            logger.error("Gemini returned no valid candidates. Raw response: %s", responses)
            raise Exception("Gemini API returned no content.")

        text_response = responses.candidates[0].content.text
        if not text_response:
            logger.error("Gemini candidate content is empty. Raw response: %s", responses)
            raise Exception("Gemini API returned empty content.")
        # --- Detailed Error Logging End ---
        logger.info(f"Gemini raw response: {text_response}")

        # Try to parse the structured JSON from Gemini's response
        try:
            import json
            start = text_response.find('{')
            end = text_response.rfind('}')
            if start != -1 and end != -1 and start < end:
                json_str = text_response[start : end + 1]
                parsed_data = json.loads(json_str)
                explanation = parsed_data.get("explanation", text_response)
                confidence = float(parsed_data.get("confidence", 0.5))
            else:
                explanation = text_response
                confidence = 0.5 # Default if no structured JSON is found
        except json.JSONDecodeError:
            explanation = text_response
            confidence = 0.5 # Default if JSON parsing fails

        return {
            "status": "ok",
            "explanation": explanation,
            "confidence": confidence,
            "source": "vertex_gemini",
        }

    except Exception as e:
        logger.exception("Error calling Gemini Pro Vision via Vertex AI: %s", e)
        # Re-raise to be caught by the service layer
        raise