import base64
import json
import logging
import io
from typing import Any, Dict, Optional

import boto3
from botocore.exceptions import ClientError
from PIL import Image

logger = logging.getLogger(__name__)

def _resize_image_if_needed(image_bytes: bytes, max_dim: int = 1120) -> bytes:
    """Resize image if getting close to Llama Vision limits (approx 1120x1120)."""
    try:
        with Image.open(io.BytesIO(image_bytes)) as img:
            w, h = img.size
            if w <= max_dim and h <= max_dim:
                return image_bytes
            
            # Maintain aspect ratio
            ratio = min(max_dim / w, max_dim / h)
            new_w = int(w * ratio)
            new_h = int(h * ratio)
            
            img = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
            
            out_buffer = io.BytesIO()
            # Convert to RGB if saving as JPEG (handle RGBA PNGs)
            if img.mode in ("RGBA", "P"):
                img = img.convert("RGB")
                
            img.save(out_buffer, format="JPEG", quality=85)
            return out_buffer.getvalue()
    except Exception as e:
        logger.warning("Image resize failed, sending original: %s", e)
        return image_bytes

BASE_INSTRUCTION = (
    "You are the dog's voice. Given a single dog image, write the response "
    "as if it comes from the dog in the picture — first-person, present tense, "
    "friendly and simple (translation app style). Describe what I'm doing, how I likely feel, "
    "and gentle boundaries (e.g., I need space, I want to play), without medical claims or absolutes."
)


def build_system_instruction(tone: Optional[str]) -> str:
    # Default Base
    role = "You are the dog in the picture. Speak in the first-person ('I')."
    style = "Friendly, simple, and direct."
    content = "Describe my body language, how I feel, and what I want."
    
    t = (tone or "").strip().lower()
    
    if t == "playful":
        style = "Super excited, high-energy, happy! Use exclamation marks! Short, punchy sentences."
        content = "Focus on how much fun I'm having or want to have! Use words like 'Zoomies', 'Play', 'Fun'!"
        
    elif t == "calm":
        style = "Soft, soothing, slow, and zen-like."
        content = "Focus on my relaxation and peace. Use calming words."
        
    elif t == "trainer":
        # Hybrid approach: Smart dog + Advice
        role = "You are the dog, but you rely on professional dog behaviorist knowledge."
        style = "Analytical, clear, and instructive. Use 'I' statements but explain the 'Why'."
        content = "Analyize my specific body language signals (ears, tail, eyes, mouth). Then, conclude with a specific 'Handling Tip' for the owner on what to do next."

    return (
        f"{role}\n"
        f"Style: {style}\n"
        f"Task: {content}\n\n"
        "CORE DIRECTIVE: You are a Dog Translator. Your job is to look at the dog's body language (ears, tail, eyes, posture) and 'translate' it into human words.\n"
        "1. IGNORE the background, rug, furniture, or humans unless they directly affect my mood.\n"
        "2. DO NOT describe the image (e.g., 'I am sitting on a rug'). Instead, say 'I'm feeling relaxed and just want to chill.'\n"
        "3. Interpret signals: Ears back? I'm worried. Tail wagging? I'm happy. Teeth bared? Back off.\n"
        "4. Output format: JSON ONLY {{'explanation': '...', 'confidence': 0.9}}\n"
        "5. The 'explanation' must be ME speaking to YOU."
    )


def _parse_json_fallback(text: str) -> Dict[str, Any]:
    """Parse model text as JSON; fallback to plain text.

    Handles common formats like fenced code blocks (```json ... ```), mixed prose + JSON,
    and returns a clean English explanation string.
    """
    raw = text or ""
    s = raw.strip()

    # Strip fenced code blocks if present
    if s.startswith("```"):
        first_newline = s.find("\n")
        if first_newline != -1:
            s = s[first_newline + 1 :]
        if s.endswith("```"):
            s = s[:-3]
        s = s.strip()

    # Try to isolate JSON substring if mixed with prose
    if "{" in s and "}" in s:
        start = s.find("{")
        end = s.rfind("}")
        if start != -1 and end != -1 and end > start:
            candidate = s[start : end + 1]
            try:
                obj = json.loads(candidate)
                explanation = str(obj.get("explanation", "")).strip()
                confidence = float(obj.get("confidence", 0.5))
                if explanation:
                    if explanation.startswith('"') and explanation.endswith('"'):
                        explanation = explanation[1:-1].strip()
                    return {"explanation": explanation, "confidence": confidence}
            except Exception:
                pass

    try:
        obj = json.loads(s)
        explanation = str(obj.get("explanation", "")).strip()
        confidence = float(obj.get("confidence", 0.5))
        if explanation.startswith('"') and explanation.endswith('"'):
            explanation = explanation[1:-1].strip()
        return {"explanation": explanation, "confidence": confidence}
    except Exception:
        cleaned = s
        # Heuristic: if the text ends with something that looks like a float (e.g. "0.9")
        # try to extract it as confidence.
        lines = [line.strip() for line in cleaned.split("\n") if line.strip()]
        if lines:
            last_line = lines[-1]
            try:
                # Check if the last line is just a float or "Confidence: 0.X"
                text_to_parse = last_line
                if "confidence" in last_line.lower():
                    colon = last_line.find(":")
                    if colon != -1:
                        text_to_parse = last_line[colon + 1 :].strip()
                
                val = float(text_to_parse)
                if 0 <= val <= 1:
                    confidence = val
                    # Remove the last line from explanation
                    cleaned = "\n".join(lines[:-1]).strip()
                    return {"explanation": cleaned, "confidence": confidence}
            except ValueError:
                pass

        if "explanation" in cleaned.lower():
            try:
                lower = cleaned.lower()
                idx = lower.find("explanation")
                colon = cleaned.find(":", idx)
                if colon != -1:
                    maybe = cleaned[colon + 1 :].strip()
                    maybe = maybe.strip().strip('"').strip("'}]")
                    if maybe:
                        cleaned = maybe
            except Exception:
                pass
        return {"explanation": cleaned, "confidence": 0.5}


def analyze_image(
    region_name: str,
    model_id: str,
    image_bytes: bytes,
    mime_type: str,
    aws_access_key_id: Optional[str] = None,
    aws_secret_access_key: Optional[str] = None,
    tone: Optional[str] = None,
) -> Dict[str, Any]:
    """Call AWS Bedrock Llama 3 Vision API and return structured result."""
    
    session_kwargs = {"region_name": region_name}
    if aws_access_key_id and aws_secret_access_key:
        session_kwargs["aws_access_key_id"] = aws_access_key_id
        session_kwargs["aws_secret_access_key"] = aws_secret_access_key
    
    try:
        bedrock_runtime = boto3.client(
            service_name="bedrock-runtime",
            **session_kwargs
        )
    except Exception as e:
        logger.error("Failed to create Bedrock client: %s", e)
        raise

    instruction = build_system_instruction(tone)
    
    # Llama 3 Vision prompt format
    # See: https://docs.aws.amazon.com/bedrock/latest/userguide/model-parameters-meta.html
    
    # Resize if needed to fit model limits
    image_bytes = _resize_image_if_needed(image_bytes)

    user_prompt = "Speak for the dog in this image. Apply the persona and style defined in the system instructions. Return ONLY JSON."
    
    body = json.dumps({
        "prompt": f"<|begin_of_text|><|start_header_id|>system<|end_header_id|>\n\n{instruction}<|eot_id|><|start_header_id|>user<|end_header_id|>\n\n<|image|>\n{user_prompt}<|eot_id|><|start_header_id|>assistant<|end_header_id|>\n\n",
        "images": [base64.b64encode(image_bytes).decode("utf-8")],
    })

    try:
        response = bedrock_runtime.invoke_model(
            body=body,
            modelId=model_id,
            accept="application/json",
            contentType="application/json",
        )
        
        response_body = json.loads(response.get("body").read())
        text = response_body.get("generation") or ""
        
        if not text:
            return {"explanation": "No interpretation available.", "confidence": 0.0}
            
        return _parse_json_fallback(text)
        
    except ClientError as e:
        logger.error("Bedrock invocation failed: %s", e)
        raise
    except Exception as e:
        logger.error("Unexpected error during Bedrock call: %s", e)
        raise
