"""Shared review-comment model and AI-friendly Markdown rendering.

Comments extracted from Word documents and PDF annotations are rendered as
explicit, self-describing callouts placed right next to the text they refer to,
so an AI can unambiguously associate each comment with its context.

The precise span a comment refers to is wrapped inline with the markers
``ANCHOR_OPEN`` / ``ANCHOR_CLOSE`` followed by a superscript index that matches
the callout (for example ``⟦grew by 12%⟧¹``). The callout itself restates the
anchored text, the author, the date, the status, and any nested replies.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

# Inline markers delimiting the exact span a comment refers to (precise anchoring).
ANCHOR_OPEN = "\u27e6"  # ⟦
ANCHOR_CLOSE = "\u27e7"  # ⟧

# Callout label used as the first token of every rendered comment block.
CALLOUT_TAG = "[!COMMENT]"

# Anchor quotes longer than this are trimmed to keep callouts readable.
_MAX_ANCHOR_CHARS = 280

_SUPERSCRIPT_DIGITS = str.maketrans(
    "0123456789",
    "\u2070\u00b9\u00b2\u00b3\u2074\u2075\u2076\u2077\u2078\u2079",
)


def superscript(number: int) -> str:
    """Return ``number`` rendered with Unicode superscript digits (12 -> ¹²)."""
    return str(number).translate(_SUPERSCRIPT_DIGITS)


def _collapse_whitespace(text: str) -> str:
    normalized = (text or "").replace("\r\n", "\n").replace("\r", "\n")
    return re.sub(r"\s+", " ", normalized).strip()


def shorten_anchor(text: str) -> str:
    """Normalize whitespace and trim the anchor text shown in the ``About`` field."""
    collapsed = _collapse_whitespace(text)
    if len(collapsed) > _MAX_ANCHOR_CHARS:
        return collapsed[: _MAX_ANCHOR_CHARS - 1].rstrip() + "\u2026"
    return collapsed


@dataclass
class Comment:
    """A single review comment (or reply) with an optional context anchor."""

    index: int = 0
    author: str = ""
    date: str = ""
    anchor_text: str = ""
    text: str = ""
    location: str = ""
    resolved: bool = False
    replies: list[Comment] = field(default_factory=list)


def _meta_suffix(comment: Comment) -> str:
    bits: list[str] = []
    author = comment.author.strip()
    date = comment.date.strip()
    if author and date:
        bits.append(f"{author} ({date})")
    elif author:
        bits.append(author)
    elif date:
        bits.append(f"({date})")
    if comment.location.strip():
        bits.append(comment.location.strip())
    if comment.resolved:
        bits.append("resolved")
    return " \u00b7 ".join(bits)


def _note_lines(text: str, prefix: str, continuation: str) -> list[str]:
    normalized = (text or "").replace("\r\n", "\n").replace("\r", "\n")
    paragraphs = [line.strip() for line in normalized.split("\n") if line.strip()]
    if not paragraphs:
        return [f"{prefix}(no text)"]
    lines = [f"{prefix}{paragraphs[0]}"]
    lines.extend(f"{continuation}{paragraph}" for paragraph in paragraphs[1:])
    return lines


def render_comment_callout(comment: Comment) -> str:
    """Render a comment (with nested replies) as an AI-friendly blockquote callout."""
    suffix = _meta_suffix(comment)
    header = f"Comment {comment.index}"
    if suffix:
        header = f"{header} \u2014 {suffix}"
    lines = [f"> {CALLOUT_TAG} {header}"]

    anchor = shorten_anchor(comment.anchor_text)
    if anchor:
        lines.append(f'> **About:** "{anchor}"')

    lines.extend(_note_lines(comment.text, prefix="> **Note:** ", continuation="> "))

    for reply in comment.replies:
        lines.append(">")
        reply_suffix = _meta_suffix(reply)
        reply_header = f"Reply \u2014 {reply_suffix}" if reply_suffix else "Reply"
        lines.append(f"> > **{reply_header}**")
        lines.extend(_note_lines(reply.text, prefix="> > ", continuation="> > "))

    return "\n".join(lines)
