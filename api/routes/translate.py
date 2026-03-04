"""Standalone translation endpoint."""

from __future__ import annotations

from fastapi import APIRouter, Request, Query

router = APIRouter()


@router.get("/")
async def translate_text(
    request: Request,
    text: str = Query(..., min_length=1, max_length=5000, description="Chinese text to translate"),
):
    """Translate Chinese text to English using DeepSeek.

    Can also be used as a general Chinese social media translator.
    """
    translator = request.app.state.translator
    translated = await translator.translate(text)
    return {
        "original": text,
        "translated": translated,
        "engine": "deepseek",
    }


@router.get("/to-chinese")
async def translate_to_chinese(
    request: Request,
    text: str = Query(..., min_length=1, max_length=2000, description="English text to translate to Chinese"),
):
    """Translate English text to Chinese (useful for search)."""
    translator = request.app.state.translator
    translated = await translator.translate_to_chinese(text)
    return {
        "original": text,
        "translated": translated,
    }
