"""Client for the Publora API."""
from __future__ import annotations

from datetime import datetime, timezone, timedelta
import os
from typing import Any, Dict, List, Optional
import requests


_LAST_SCHEDULED_UTC: Optional[datetime] = None


def reset_scheduled_time_tracker() -> None:
    """Restablece el registro del último timestamp programado (útil para tests)."""
    global _LAST_SCHEDULED_UTC
    _LAST_SCHEDULED_UTC = None


def get_next_available_scheduled_time(min_gap_minutes: int = 3) -> str:
    """Calcula el próximo horario de publicación garantizando un espacio mínimo entre posts."""
    global _LAST_SCHEDULED_UTC
    now = datetime.now(timezone.utc)
    base_time = now + timedelta(minutes=1)
    if _LAST_SCHEDULED_UTC and _LAST_SCHEDULED_UTC > now:
        target = max(base_time, _LAST_SCHEDULED_UTC + timedelta(minutes=min_gap_minutes))
    else:
        target = base_time
    _LAST_SCHEDULED_UTC = target
    return target.strftime("%Y-%m-%dT%H:%M:%S.000Z")


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

    def _get_headers(self) -> Dict[str, str]:
        if not self.api_key or not self.platform_id:
            raise ValueError("PUBLORA_API_KEY and LINKEDIN_PLATFORM_ID are required.")
        return {
            "x-publora-key": self.api_key,
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    def publish_draft(
        self,
        post_group_id: str,
        scheduled_at: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Publish a pre-created draft post by updating its status to scheduled."""
        if not post_group_id:
            raise ValueError("post_group_id is required.")
        headers = self._get_headers()

        if scheduled_at:
            target_time = scheduled_at
        else:
            target_time = get_next_available_scheduled_time(min_gap_minutes=3)

        payload = {
            "status": "scheduled",
            "scheduledTime": target_time,
        }

        resp = self.session.put(
            f"{self.BASE_URL}/update-post/{post_group_id}",
            json=payload,
            headers=headers,
            timeout=15,
        )
        resp.raise_for_status()
        return resp.json()

    def get_post_status(self, post_group_id: str) -> Dict[str, Any]:
        """Fetch current publishing status and platform details for a post group."""
        if not post_group_id:
            raise ValueError("post_group_id is required.")
        headers = self._get_headers()

        resp = self.session.get(
            f"{self.BASE_URL}/get-post/{post_group_id}",
            headers=headers,
            timeout=15,
        )
        resp.raise_for_status()
        return resp.json()

    def create_post(
        self,
        text: str,
        media_urls: Optional[List[str]] = None,
        pdf_bytes: Optional[bytes] = None,
        pdf_filename: str = "carrusel.pdf",
        scheduled_at: Optional[str] = None,
        draft: bool = False,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Create a LinkedIn post through Publora with optional PDF carousel upload."""
        headers = self._get_headers()
        platforms = [self.platform_id] if isinstance(self.platform_id, str) else self.platform_id

        # Si hay un archivo PDF (carrusel), creamos inicialmente como borrador
        # para que Publora permita adjuntar el archivo a S3 antes de programar la entrega.
        is_immediate_publish = not draft
        initial_draft = draft or bool(pdf_bytes)

        payload: Dict[str, Any] = {
            "platforms": platforms,
            "content": text,
        }
        if initial_draft:
            payload["draft"] = True
        else:
            if scheduled_at:
                payload["scheduledTime"] = scheduled_at
            else:
                payload["scheduledTime"] = get_next_available_scheduled_time(min_gap_minutes=3)

        if media_urls:
            payload["mediaUrls"] = media_urls

        resp = self.session.post(
            f"{self.BASE_URL}/create-post",
            json=payload,
            headers=headers,
            timeout=15,
        )
        resp.raise_for_status()
        post_data = resp.json()
        post_group_id = post_data.get("postGroupId") or post_data.get("id")

        # Flujo de subida de PDF a Publora/S3 para carruseles de LinkedIn (Document Posts)
        if pdf_bytes and post_group_id:
            url_resp = self.session.post(
                f"{self.BASE_URL}/get-upload-url",
                json={
                    "fileName": pdf_filename,
                    "contentType": "application/pdf",
                    "postGroupId": post_group_id,
                },
                headers=headers,
                timeout=15,
            )
            url_resp.raise_for_status()
            upload_data = url_resp.json()
            upload_url = upload_data.get("uploadUrl")
            media_id = upload_data.get("mediaId")

            if upload_url:
                s3_resp = requests.put(
                    upload_url,
                    data=pdf_bytes,
                    headers={"Content-Type": "application/pdf"},
                    timeout=60,
                )
                s3_resp.raise_for_status()

            if media_id:
                comp_resp = self.session.post(
                    f"{self.BASE_URL}/complete-media/{media_id}",
                    json={"postGroupId": post_group_id},
                    headers=headers,
                    timeout=15,
                )
                comp_resp.raise_for_status()

            if is_immediate_publish:
                self.publish_draft(post_group_id, scheduled_at=scheduled_at)

        return post_data
