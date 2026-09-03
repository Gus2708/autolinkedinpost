"""LinkedIn URL → URN parser.

Extracts canonical activity URNs, post IDs, and comment IDs from LinkedIn URLs.
"""
from __future__ import annotations

import re
from typing import Optional, TypedDict
from urllib.parse import unquote


class ParsedLinkedInUrl(TypedDict, total=False):
    post_activity_id: Optional[str]
    post_urn: Optional[str]
    comment_id: Optional[str]
    comment_urn: Optional[str]
    url_type: str


ACTIVITY_SLUG_RE = re.compile(r"activity[-:](\d{18,25})")
SHARE_SLUG_RE = re.compile(r"share[-:](\d{18,25})")
UGCPOST_SLUG_RE = re.compile(r"ugcPost[-:](\d{18,25})")
COMMENT_URN_RE = re.compile(
    r"urn:li:comment:\("
    r"(?:urn:li:)?(activity|ugcPost|share):(\d+)"
    r"\s*,\s*(\d+)"
    r"\)"
)


def parse_linkedin_url(url: str) -> ParsedLinkedInUrl:
    """Parse any LinkedIn post or comment URL into structured URNs."""
    if not isinstance(url, str) or not url.strip():
        return {
            "post_activity_id": None,
            "post_urn": None,
            "comment_id": None,
            "comment_urn": None,
            "url_type": "unknown",
        }

    decoded = unquote(url)
    out: ParsedLinkedInUrl = {
        "post_activity_id": None,
        "post_urn": None,
        "comment_id": None,
        "comment_urn": None,
        "url_type": "unknown",
    }

    # Try comment URN first (commentUrn=... query param or path)
    m = COMMENT_URN_RE.search(decoded)
    if m:
        kind, post_id, comment_id = m.groups()
        out["comment_id"] = comment_id
        if kind == "activity":
            out["post_urn"] = f"urn:li:activity:{post_id}"
            out["post_activity_id"] = post_id
        elif kind == "ugcPost":
            out["post_urn"] = f"urn:li:ugcPost:{post_id}"
        elif kind == "share":
            out["post_urn"] = f"urn:li:share:{post_id}"
        out["comment_urn"] = f"urn:li:comment:({out['post_urn']},{comment_id})"
        out["url_type"] = "comment"
        return out

    # Post URL variants
    for pattern, kind in [
        (UGCPOST_SLUG_RE, "ugcPost"),
        (SHARE_SLUG_RE, "share"),
        (ACTIVITY_SLUG_RE, "activity"),
    ]:
        m = pattern.search(decoded)
        if m:
            pid = m.group(1)
            out["post_urn"] = f"urn:li:{kind}:{pid}"
            if kind == "activity":
                out["post_activity_id"] = pid
            out["url_type"] = "post"
            return out

    return out


def build_parent_comment_urn(post_urn: str, parent_comment_id: str) -> str:
    """Format a parentComment URN given a post URN and the top-level comment id."""
    return f"urn:li:comment:({post_urn},{parent_comment_id})"
