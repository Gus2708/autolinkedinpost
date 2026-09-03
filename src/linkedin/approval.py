"""Approval gate helpers and state machine for human-in-the-loop workflows."""
from __future__ import annotations

from enum import Enum
from typing import Dict, Optional


class ApprovalStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class ApprovalGate:
    """Manages human approval states for LinkedIn content actions."""

    def __init__(self) -> None:
        self._states: Dict[str, ApprovalStatus] = {}
        self._payloads: Dict[str, str] = {}

    def request_approval(self, draft_id: str, content: str) -> ApprovalStatus:
        self._states[draft_id] = ApprovalStatus.PENDING
        self._payloads[draft_id] = content
        return ApprovalStatus.PENDING

    def confirm(self, draft_id: str) -> None:
        if draft_id not in self._states:
            raise KeyError(f"Draft '{draft_id}' not found.")
        self._states[draft_id] = ApprovalStatus.APPROVED

    def reject(self, draft_id: str) -> None:
        if draft_id not in self._states:
            raise KeyError(f"Draft '{draft_id}' not found.")
        self._states[draft_id] = ApprovalStatus.REJECTED

    def is_approved(self, draft_id: str) -> bool:
        return self._states.get(draft_id) == ApprovalStatus.APPROVED

    def get_status(self, draft_id: str) -> Optional[ApprovalStatus]:
        return self._states.get(draft_id)

    def render_approval_card(
        self,
        *,
        kind: str,
        preview_text: str,
        target_url: Optional[str] = None,
        reaction_type: Optional[str] = None,
        char_count: Optional[int] = None,
        extra_context: Optional[dict] = None,
    ) -> str:
        """Format a standardized approval card for user review."""
        lines = [f"## Draft ready for approval — {kind}", ""]
        if target_url:
            lines.append(f"**Target:** {target_url}")
        if reaction_type:
            lines.append(f"**Reaction:** `{reaction_type}`")
        if char_count is None:
            char_count = len(preview_text)
        lines.append(f"**Chars:** {char_count}")
        lines.append("")
        lines.append("**Preview:**")
        lines.append("")
        for pl in preview_text.splitlines() or [""]:
            lines.append(f"> {pl}")
        lines.append("")
        if extra_context:
            lines.append("**Context:**")
            for k, v in extra_context.items():
                lines.append(f"- **{k}**: {v}")
            lines.append("")
        lines.append("Reply **post** / **yes** to publish, or suggest edits.")
        return "\n".join(lines)
