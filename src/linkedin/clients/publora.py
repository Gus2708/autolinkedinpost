"""Client for the Publora API."""
from __future__ import annotations

import os
from typing import Any, Dict, List, Optional
import requests


class PubloraClient:
    """Client for scheduling and publishing posts to LinkedIn via Publora."""

    BASE_URL = "https://api.publora.com/api/v1"

    def __init__(
        self,
        api_key: Optional[str] = None,
        platform_id: Optional[str] = None,
        session: Optional[requests.Session] = None,
    ) -> None:
        self.api_key = api_key or os.environ.get("PUBLORA_API_KEY", "")
        self.platform_id = platform_id or os.environ.get("LINKEDIN_PLATFORM_ID", "")
        self.session = session or requests.Session()

    def create_post(
        self,
        text: str,
        media_urls: Optional[List[str]] = None,
        scheduled_at: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Create a LinkedIn post through Publora."""
        if not self.api_key or not self.platform_id:
            raise ValueError("PUBLORA_API_KEY and LINKEDIN_PLATFORM_ID are required.")

        headers = {
            "x-publora-key": self.api_key,
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        platforms = [self.platform_id] if isinstance(self.platform_id, str) else self.platform_id
        payload: Dict[str, Any] = {
            "platforms": platforms,
            "content": text,
        }
        if media_urls:
            payload["mediaUrls"] = media_urls
        if scheduled_at:
            payload["scheduledTime"] = scheduled_at

        resp = self.session.post(
            f"{self.BASE_URL}/create-post",
            json=payload,
            headers=headers,
            timeout=15,
        )
        resp.raise_for_status()
        return resp.json()
