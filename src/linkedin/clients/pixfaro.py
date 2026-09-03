"""Client for the Pixfaro API."""
from __future__ import annotations

import os
from typing import Any, Dict, List, Optional
import requests


class PixfaroClient:
    """Client for publishing to LinkedIn via Pixfaro."""

    BASE_URL = "https://api.pixfaro.com/v1"

    def __init__(
        self,
        api_key: Optional[str] = None,
        account_id: Optional[str] = None,
        session: Optional[requests.Session] = None,
    ) -> None:
        self.api_key = api_key or os.environ.get("PIXFARO_API_KEY", "")
        self.account_id = account_id or os.environ.get("PIXFARO_ACCOUNT_ID", "")
        self.session = session or requests.Session()

    def create_post(
        self,
        text: str,
        media_urls: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Create a LinkedIn post through Pixfaro."""
        if not self.api_key or not self.account_id:
            raise ValueError("PIXFARO_API_KEY and PIXFARO_ACCOUNT_ID are required.")

        headers = {
            "X-Api-Key": self.api_key,
            "Content-Type": "application/json",
        }
        payload: Dict[str, Any] = {
            "accountId": self.account_id,
            "text": text,
        }
        if media_urls:
            payload["media"] = media_urls

        resp = self.session.post(
            f"{self.BASE_URL}/linkedin/posts",
            json=payload,
            headers=headers,
            timeout=15,
        )
        resp.raise_for_status()
        return resp.json()
