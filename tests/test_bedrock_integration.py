import os
import base64
import pytest
from src.backend.bedrock_client import analyze_image
from src.backend.config import get_settings

def test_bedrock_analyze_real_image_basic():
    """Integration test to verify Bedrock analysis with a real dog image (Basic)."""
    settings = get_settings()
    
    if not settings.aws_access_key_id or not settings.aws_secret_access_key:
        pytest.skip("AWS credentials not configured in environment")
        
    fixture_path = os.path.join(os.path.dirname(__file__), "fixtures", "dog_sleep.jpg")
    with open(fixture_path, "rb") as f:
        image_bytes = f.read()
        
    result = analyze_image(
        region_name=settings.bedrock_region,
        model_id=settings.bedrock_model_id,
        image_bytes=image_bytes,
        mime_type="image/jpeg",
        aws_access_key_id=settings.aws_access_key_id,
        aws_secret_access_key=settings.aws_secret_access_key,
        tone="calm"
    )
    
    assert "explanation" in result
    assert "confidence" in result
    assert isinstance(result["explanation"], str)
    assert len(result["explanation"]) > 0
    print(f"\nResult: {result['explanation']}")

@pytest.mark.parametrize("tone", ["playful", "trainer", "default"])
def test_bedrock_analyze_tones(tone):
    """Verify that different tones change the output style/content."""
    settings = get_settings()
    
    if not settings.aws_access_key_id or not settings.aws_secret_access_key:
        pytest.skip("AWS credentials not configured in environment")
        
    fixture_path = os.path.join(os.path.dirname(__file__), "fixtures", "dog_sleep.jpg")
    with open(fixture_path, "rb") as f:
        image_bytes = f.read()
        
    result = analyze_image(
        region_name=settings.bedrock_region,
        model_id=settings.bedrock_model_id,
        image_bytes=image_bytes,
        mime_type="image/jpeg",
        aws_access_key_id=settings.aws_access_key_id,
        aws_secret_access_key=settings.aws_secret_access_key,
        tone=None if tone == "default" else tone
    )
    
    assert "explanation" in result
    assert len(result["explanation"]) > 0
    print(f"\nTone: {tone}\nResult: {result['explanation'][:100]}...")

def test_bedrock_error_handling_invalid_model():
    """Verify system handles invalid model ID gracefully."""
    settings = get_settings()
    
    if not settings.aws_access_key_id or not settings.aws_secret_access_key:
        pytest.skip("AWS credentials not configured in environment")
        
    with pytest.raises(Exception):
        analyze_image(
            region_name=settings.bedrock_region,
            model_id="invalid-model-id",
            image_bytes=b"fake-image",
            mime_type="image/jpeg",
            aws_access_key_id=settings.aws_access_key_id,
            aws_secret_access_key=settings.aws_secret_access_key
        )
