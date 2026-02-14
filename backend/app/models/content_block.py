from typing import Literal, Optional
from pydantic import BaseModel, Field


class MediaBlock(BaseModel):
    kind: Literal["url", "gridfs", "bindata", "base64"] = "url"
    url: Optional[str] = None
    gridfs_file_id: Optional[str] = None
    base64: Optional[str] = None
    mime: Optional[str] = None


class ContentBlock(BaseModel):
    """Text and/or image content. Supports Arabic and English. Use both text and media for text with image."""

    text: Optional[str] = Field(None, description="Optional text (fallback when text_ar/text_en not set)")
    text_ar: Optional[str] = Field(None, description="Arabic text")
    text_en: Optional[str] = Field(None, description="English text")
    media: Optional[MediaBlock] = Field(None, description="Optional image or other media")

    def get_text_for_lang(self, lang: Literal["ar", "en"]) -> Optional[str]:
        """Return text for the given language (ar/en). Prefers text_ar/text_en, falls back to text."""
        if lang == "ar" and self.text_ar is not None:
            return self.text_ar
        if lang == "en" and self.text_en is not None:
            return self.text_en
        return self.text


def content_block_for_lang(block: dict, lang: Literal["ar", "en"]) -> dict:
    """
    Resolve a ContentBlock dict to a single language. Returns a dict with 'text' set
    from text_ar/text_en or fallback 'text', and same 'media' if present.
    """
    if not block:
        return block
    text = block.get("text_ar") if lang == "ar" else block.get("text_en")
    if text is None:
        text = block.get("text")
    out = {"text": text}
    if block.get("media"):
        out["media"] = block["media"]
    return out
