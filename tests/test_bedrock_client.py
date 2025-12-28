import json
from unittest.mock import MagicMock, patch
import pytest
from src.backend.bedrock_client import _parse_json_fallback, analyze_image

def test_parse_json_fallback_valid_json():
    text = json.dumps({"explanation": "Dog looks happy.", "confidence": 0.95})
    result = _parse_json_fallback(text)
    assert result["explanation"] == "Dog looks happy."
    assert abs(result["confidence"] - 0.95) < 1e-6

def test_parse_json_fallback_plain_text():
    text = "The dog is wagging its tail."
    result = _parse_json_fallback(text)
    assert result["explanation"] == "The dog is wagging its tail."
    assert result["confidence"] == 0.5

def test_parse_json_fallback_fenced_json():
    text = """```json
    {"explanation": "I'm ready to play!", "confidence": 0.88}
    ```"""
    result = _parse_json_fallback(text)
    assert "ready to play" in result["explanation"].lower()
    assert abs(result["confidence"] - 0.88) < 1e-6

@patch("boto3.client")
def test_analyze_image_success(mock_boto_client):
    # Mock Bedrock client and response
    mock_bedrock = MagicMock()
    mock_boto_client.return_value = mock_bedrock
    
    # Mock response body
    mock_body = MagicMock()
    mock_body.read.return_value = json.dumps({
        "generation": '{"explanation": "I am a happy dog!", "confidence": 0.9}'
    }).encode("utf-8")
    
    mock_bedrock.invoke_model.return_value = {
        "body": mock_body
    }
    
    result = analyze_image(
        region_name="us-east-1",
        model_id="meta.llama3-2-11b-instruct-v1:0",
        image_bytes=b"fake_image_data",
        mime_type="image/jpeg",
        aws_access_key_id="fake_key",
        aws_secret_access_key="fake_secret"
    )
    
    assert result["explanation"] == "I am a happy dog!"
    assert result["confidence"] == 0.9
    mock_bedrock.invoke_model.assert_called_once()

@patch("boto3.client")
def test_analyze_image_client_error(mock_boto_client):
    mock_bedrock = MagicMock()
    mock_boto_client.return_value = mock_bedrock
    mock_bedrock.invoke_model.side_effect = Exception("Bedrock error")
    
    with pytest.raises(Exception, match="Bedrock error"):
        analyze_image(
            region_name="us-east-1",
            model_id="meta.llama3-2-11b-instruct-v1:0",
            image_bytes=b"fake_image_data",
            mime_type="image/jpeg"
        )
