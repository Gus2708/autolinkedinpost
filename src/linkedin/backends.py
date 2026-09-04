"""Backend selector for LinkedIn publication (Publora, Pixfaro, Tier 0 Draft)."""
from __future__ import annotations

import os
from typing import Any, Dict, List, Optional
from src.linkedin.clients.publora import PubloraClient
from src.linkedin.clients.pixfaro import PixfaroClient


class BackendSelector:
    """Detects available publishing backends and dispatches publication requests."""

    def __init__(
        self,
        env: Optional[Dict[str, str]] = None,
        publora_client: Optional[PubloraClient] = None,
        pixfaro_client: Optional[PixfaroClient] = None,
    ) -> None:
        self._env = os.environ if env is None else env
        self.publora_client = publora_client
        self.pixfaro_client = pixfaro_client

    @property
    def active_backend(self) -> str:
        if self._env.get("PUBLORA_API_KEY") and self._env.get("LINKEDIN_PLATFORM_ID"):
            return "publora"
        pix_key = self._env.get("PIXFARO_API_KEY") or self._env.get("PIXFARO_TOKEN")
        pix_acc = self._env.get("PIXFARO_ACCOUNT_ID")
        if pix_key and pix_acc:
            return "pixfaro"
        return "draft"

    def publish(
        self,
        text: str,
        media_urls: Optional[List[str]] = None,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Publish post or format draft if in Tier 0."""
        backend = self.active_backend
        if backend == "publora":
            client = self.publora_client or PubloraClient(
                api_key=self._env.get("PUBLORA_API_KEY"),
                platform_id=self._env.get("LINKEDIN_PLATFORM_ID"),
            )
            res = client.create_post(text=text, media_urls=media_urls, **kwargs)
            post_id = res.get("id") or res.get("postGroupId")
            return {
                "status": "published",
                "backend": "publora",
                "id": post_id,
                "raw": res,
            }
        elif backend == "pixfaro":
            client = self.pixfaro_client or PixfaroClient(
                api_key=self._env.get("PIXFARO_API_KEY"),
                account_id=self._env.get("PIXFARO_ACCOUNT_ID"),
            )
            res = client.create_post(text=text, media_urls=media_urls)
            return {
                "status": "published",
                "backend": "pixfaro",
                "id": res.get("id"),
                "raw": res,
            }
        else:
            return {
                "status": "draft",
                "backend": "draft",
                "content": text,
                "media_urls": media_urls or [],
                "message": "Tier 0 (Draft mode active). Copy and paste the draft manually into LinkedIn.",
            }

    def create_draft(
        self,
        text: str,
        media_urls: Optional[List[str]] = None,
        pdf_bytes: Optional[bytes] = None,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Create a draft post without scheduling immediate publication."""
        backend = self.active_backend
        if backend == "publora":
            client = self.publora_client or PubloraClient(
                api_key=self._env.get("PUBLORA_API_KEY"),
                platform_id=self._env.get("LINKEDIN_PLATFORM_ID"),
            )
            res = client.create_post(
                text=text,
                media_urls=media_urls,
                pdf_bytes=pdf_bytes,
                draft=True,
                **kwargs,
            )
            draft_id = res.get("postGroupId") or res.get("id")
            return {
                "status": "draft",
                "backend": "publora",
                "id": draft_id,
                "raw": res,
            }
        else:
            return {
                "status": "draft",
                "backend": backend,
                "content": text,
                "media_urls": media_urls or [],
                "pdf_bytes": pdf_bytes,
                "message": f"Draft created in {backend} mode.",
            }

    def publish_draft(
        self,
        draft_id: str,
        scheduled_at: Optional[str] = None,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Publish or schedule an already pre-created draft post."""
        backend = self.active_backend
        if backend == "publora":
            client = self.publora_client or PubloraClient(
                api_key=self._env.get("PUBLORA_API_KEY"),
                platform_id=self._env.get("LINKEDIN_PLATFORM_ID"),
            )
            res = client.publish_draft(
                post_group_id=draft_id,
                scheduled_at=scheduled_at,
            )
            pub_id = res.get("id") or res.get("postGroupId") or draft_id
            return {
                "status": "published",
                "backend": "publora",
                "id": pub_id,
                "raw": res,
            }
        else:
            return {
                "status": "published",
                "backend": backend,
                "id": draft_id,
                "message": f"Draft {draft_id} published in {backend} mode.",
            }

