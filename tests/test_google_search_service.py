"""Tests for GoogleSearchService."""
import json
from unittest.mock import MagicMock, patch
import pytest

from src.backend.services.google_search_service import (
    GoogleSearchService,
    _sanitize_query,
    MAX_QUERY_LENGTH,
)


class TestSanitizeQuery:
    """Tests for query sanitization function."""
    
    def test_strips_whitespace(self):
        assert _sanitize_query("  tail wagging  ") == "tail wagging"
    
    def test_removes_control_characters(self):
        assert _sanitize_query("tail\x00wagging\x1f") == "tailwagging"
    
    def test_limits_length(self):
        long_query = "a" * 150
        result = _sanitize_query(long_query)
        assert len(result) == MAX_QUERY_LENGTH
    
    def test_empty_query(self):
        assert _sanitize_query("") == ""
        assert _sanitize_query("   ") == ""
    
    def test_preserves_valid_characters(self):
        query = "Why does my dog bark at strangers?"
        assert _sanitize_query(query) == query


class TestGoogleSearchService:
    """Tests for GoogleSearchService."""
    
    @patch("src.backend.services.google_search_service.get_settings")
    def test_is_not_configured_when_missing_api_key(self, mock_settings):
        mock_settings.return_value = MagicMock(
            google_search_api_key="",
            google_search_engine_id="test_cx"
        )
        service = GoogleSearchService()
        assert not service._is_configured()
    
    @patch("src.backend.services.google_search_service.get_settings")
    def test_is_not_configured_when_missing_engine_id(self, mock_settings):
        mock_settings.return_value = MagicMock(
            google_search_api_key="test_key",
            google_search_engine_id=""
        )
        service = GoogleSearchService()
        assert not service._is_configured()
    
    @patch("src.backend.services.google_search_service.get_settings")
    def test_is_configured_when_both_present(self, mock_settings):
        mock_settings.return_value = MagicMock(
            google_search_api_key="test_key",
            google_search_engine_id="test_cx"
        )
        service = GoogleSearchService()
        assert service._is_configured()
    
    @patch("src.backend.services.google_search_service.get_settings")
    def test_transform_results_extracts_fields(self, mock_settings):
        mock_settings.return_value = MagicMock(
            google_search_api_key="test_key",
            google_search_engine_id="test_cx"
        )
        service = GoogleSearchService()
        
        raw_data = {
            "items": [
                {
                    "title": "Why Dogs Wag Their Tails",
                    "snippet": "Dogs wag their tails to communicate...",
                    "link": "https://example.com/article1",
                    "extra_field": "ignored"
                },
                {
                    "title": "Dog Body Language",
                    "snippet": "Understanding your dog...",
                    "link": "https://example.com/article2"
                }
            ]
        }
        
        results = service._transform_results(raw_data)
        
        assert len(results) == 2
        assert results[0] == {
            "title": "Why Dogs Wag Their Tails",
            "snippet": "Dogs wag their tails to communicate...",
            "url": "https://example.com/article1"
        }
    
    @patch("src.backend.services.google_search_service.get_settings")
    def test_transform_results_skips_incomplete_items(self, mock_settings):
        mock_settings.return_value = MagicMock(
            google_search_api_key="test_key",
            google_search_engine_id="test_cx"
        )
        service = GoogleSearchService()
        
        raw_data = {
            "items": [
                {"title": "Valid Title", "link": "https://example.com"},
                {"title": "", "link": "https://example.com"},  # Empty title
                {"title": "No URL"},  # Missing link
            ]
        }
        
        results = service._transform_results(raw_data)
        assert len(results) == 1
        assert results[0]["title"] == "Valid Title"
    
    @patch("src.backend.services.google_search_service.get_settings")
    def test_transform_results_handles_empty_response(self, mock_settings):
        mock_settings.return_value = MagicMock(
            google_search_api_key="test_key",
            google_search_engine_id="test_cx"
        )
        service = GoogleSearchService()
        
        results = service._transform_results({})
        assert results == []
        
        results = service._transform_results({"items": []})
        assert results == []


@pytest.mark.asyncio
class TestSearchPetBehaviorAsync:
    """Async tests for search_pet_behavior method."""
    
    @patch("src.backend.services.google_search_service.requests.get")
    @patch("src.backend.services.google_search_service.get_settings")
    async def test_search_success(self, mock_settings, mock_get):
        mock_settings.return_value = MagicMock(
            google_search_api_key="test_key",
            google_search_engine_id="test_cx"
        )
        
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "items": [
                {
                    "title": "Test Result",
                    "snippet": "Test snippet",
                    "link": "https://example.com"
                }
            ]
        }
        mock_get.return_value = mock_response
        
        service = GoogleSearchService()
        results = await service.search_pet_behavior("tail wagging")
        
        assert len(results) == 1
        assert results[0]["title"] == "Test Result"
        
        # Verify SafeSearch was enabled
        call_args = mock_get.call_args
        assert call_args[1]["params"]["safe"] == "active"
    
    @patch("src.backend.services.google_search_service.get_settings")
    async def test_search_not_configured_raises_503(self, mock_settings):
        mock_settings.return_value = MagicMock(
            google_search_api_key="",
            google_search_engine_id=""
        )
        
        service = GoogleSearchService()
        
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc_info:
            await service.search_pet_behavior("test")
        
        assert exc_info.value.status_code == 503
    
    @patch("src.backend.services.google_search_service.get_settings")
    async def test_search_empty_query_raises_400(self, mock_settings):
        mock_settings.return_value = MagicMock(
            google_search_api_key="test_key",
            google_search_engine_id="test_cx"
        )
        
        service = GoogleSearchService()
        
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc_info:
            await service.search_pet_behavior("   ")
        
        assert exc_info.value.status_code == 400
