"""Google Custom Search API service for pet behavior explanations."""
from __future__ import annotations

import logging
import re
import asyncio
from typing import Dict, List, Any, Optional

import requests
from fastapi import HTTPException

from ..config import get_settings

logger = logging.getLogger(__name__)

# Google Custom Search API endpoint
GOOGLE_SEARCH_API_URL = "https://www.googleapis.com/customsearch/v1"

# Maximum query length after sanitization
MAX_QUERY_LENGTH = 100


def _sanitize_query(query: str) -> str:
    """
    Sanitize the search query to prevent injection and ensure safe input.
    
    - Strips leading/trailing whitespace
    - Removes control characters
    - Limits length to MAX_QUERY_LENGTH
    - Adds pet-related context for better results
    """
    if not query:
        return ""
    
    # Strip whitespace
    cleaned = query.strip()
    
    # Remove control characters (anything not printable except spaces)
    cleaned = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', cleaned)
    
    # Limit length
    if len(cleaned) > MAX_QUERY_LENGTH:
        cleaned = cleaned[:MAX_QUERY_LENGTH]
    
    return cleaned


class GoogleSearchService:
    """Service for querying Google Custom Search API for pet behavior insights."""
    
    def __init__(self):
        self.settings = get_settings()
    
    def _is_configured(self) -> bool:
        """Check if API credentials are configured."""
        return bool(
            self.settings.google_search_api_key and 
            self.settings.google_search_engine_id
        )
    
    async def search_pet_behavior(
        self, 
        query: str, 
        num_results: int = 5
    ) -> List[Dict[str, str]]:
        """
        Search for pet behavior information using Google Custom Search API.
        
        Args:
            query: The pet behavior to search for
            num_results: Number of results to return (max 10)
            
        Returns:
            List of dicts with title, snippet, and url
            
        Raises:
            HTTPException: If API is not configured or request fails
        """
        if not self._is_configured():
            raise HTTPException(
                status_code=503,
                detail="Google Search API is not configured. Please set GOOGLE_SEARCH_API_KEY and GOOGLE_SEARCH_ENGINE_ID."
            )
        
        # Sanitize and enhance query
        sanitized_query = _sanitize_query(query)
        if not sanitized_query:
            raise HTTPException(
                status_code=400,
                detail="Invalid or empty behavior query."
            )
        
        # Add pet context to improve result relevance
        search_query = f"pet dog cat behavior {sanitized_query}"
        
        # Prepare API request parameters
        params = {
            "key": self.settings.google_search_api_key,
            "cx": self.settings.google_search_engine_id,
            "q": search_query,
            "num": min(num_results, 10),  # API max is 10
            "safe": "active",  # Enable SafeSearch to filter NSFW content
        }
        
        try:
            # Run blocking request in thread pool
            response = await asyncio.to_thread(
                requests.get,
                GOOGLE_SEARCH_API_URL,
                params=params,
                timeout=10
            )
            
            if response.status_code != 200:
                logger.error(
                    "Google Search API error: status=%d body=%s",
                    response.status_code,
                    response.text[:500]
                )
                raise HTTPException(
                    status_code=502,
                    detail="Failed to fetch search results from Google."
                )
            
            data = response.json()
            return self._transform_results(data)
            
        except requests.RequestException as e:
            logger.exception("Google Search API request failed: %s", e)
            raise HTTPException(
                status_code=502,
                detail="Unable to connect to Google Search API."
            )
    
    def _transform_results(self, data: Dict[str, Any]) -> List[Dict[str, str]]:
        """
        Transform raw Google API response to clean result format.
        
        Returns only essential fields: title, snippet, url
        """
        items = data.get("items", [])
        results = []
        
        for item in items:
            result = {
                "title": item.get("title", "").strip(),
                "snippet": item.get("snippet", "").strip(),
                "url": item.get("link", "").strip(),
            }
            # Only include results with all required fields
            if result["title"] and result["url"]:
                results.append(result)
        
        return results
