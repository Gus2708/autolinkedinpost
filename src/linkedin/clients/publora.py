"""Client for the Publora API."""
from __future__ import annotations

from datetime import datetime, timezone, timedelta
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
        pdf_bytes: Optional[bytes] = None,
        pdf_filename: str = "carrusel.pdf",
        scheduled_at: Optional[str] = None,
        draft: bool = False,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Create a LinkedIn post through Publora with optional PDF carousel upload."""
        if not self.api_key or not self.platform_id:
            raise ValueError("PUBLORA_API_KEY and LINKEDIN_PLATFORM_ID are required.")

        headers = {
            "x-publora-key": self.api_key,
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
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
                now_utc = (datetime.now(timezone.utc) + timedelta(minutes=1)).strftime("%Y-%m-%dT%H:%M:%S.000Z")
                payload["scheduledTime"] = now_utc

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
        post_group_id = post_data.get("postGroupId")

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
                if scheduled_at:
                    target_time = scheduled_at
                else:
                    target_time = (datetime.now(timezone.utc) + timedelta(minutes=1)).strftime("%Y-%m-%dT%H:%M:%S.000Z")

                up_resp = self.session.put(
                    f"{self.BASE_URL}/update-post/{post_group_id}",
                    json={
                        "status": "scheduled",
                        "scheduledTime": target_time,
                    },
                    headers=headers,
                    timeout=15,
                )
                up_resp.raise_for_status()

        return post_data
