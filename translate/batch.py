"""Batch translation utilities for Douyin API response objects.

These functions take raw API response dicts and add translated
fields in-place, so the rest of the application can access both
original Chinese and translated English text.
"""

from __future__ import annotations

import logging
from typing import Any

from .engine import TranslationEngine

logger = logging.getLogger("dou.translate.batch")


async def translate_feed(
    engine: TranslationEngine,
    feed_data: dict[str, Any],
) -> dict[str, Any]:
    """Translate all video descriptions in a feed response.

    Adds 'desc_translated' field to each aweme object.
    """
    aweme_list = feed_data.get("aweme_list", [])
    if not aweme_list:
        return feed_data

    descriptions = [a.get("desc", "") for a in aweme_list]
    translations = await engine.translate_batch(descriptions)

    for aweme, translated in zip(aweme_list, translations):
        aweme["desc_translated"] = translated

        # also translate author signature if present
        sig = aweme.get("author", {}).get("signature", "")
        if sig and engine._has_chinese(sig):
            aweme["author"]["signature_translated"] = await engine.translate(sig)

    return feed_data


async def translate_comments(
    engine: TranslationEngine,
    comments_data: dict[str, Any],
) -> dict[str, Any]:
    """Translate comment texts in a comment list response.

    Handles both top-level comments and nested replies.
    """
    comments = comments_data.get("comments") or []
    if not comments:
        return comments_data

    # translate top-level comments
    texts = [c.get("text", "") for c in comments]
    translations = await engine.translate_batch(texts)

    for comment, translated in zip(comments, translations):
        comment["text_translated"] = translated

        # translate reply comments if any
        replies = comment.get("reply_comment") or comment.get("reply_comment_total") or []
        if isinstance(replies, list) and replies:
            reply_texts = [r.get("text", "") for r in replies]
            reply_translations = await engine.translate_batch(reply_texts)
            for reply, reply_tr in zip(replies, reply_translations):
                reply["text_translated"] = reply_tr

    return comments_data


async def translate_user_profile(
    engine: TranslationEngine,
    user_data: dict[str, Any],
) -> dict[str, Any]:
    """Translate user profile fields (nickname, signature)."""
    user = user_data.get("user", {})
    if not user:
        return user_data

    for field in ("signature", "nickname"):
        value = user.get(field, "")
        if value and engine._has_chinese(value):
            user[f"{field}_translated"] = await engine.translate(value)

    return user_data


async def translate_search_results(
    engine: TranslationEngine,
    search_data: dict[str, Any],
) -> dict[str, Any]:
    """Translate search result items (can be mixed types)."""
    # search results may come as aweme_list or data
    if "aweme_list" in search_data:
        return await translate_feed(engine, search_data)

    data_list = search_data.get("data", [])
    if not data_list:
        return search_data

    for item in data_list:
        aweme = item.get("aweme", {})
        if aweme:
            desc = aweme.get("desc", "")
            if desc:
                aweme["desc_translated"] = await engine.translate(desc)

    return search_data


async def translate_hot_search(
    engine: TranslationEngine,
    hot_data: dict[str, Any],
) -> dict[str, Any]:
    """Translate hot search keywords."""
    word_list = hot_data.get("data", {}).get("word_list") or hot_data.get("word_list") or []

    if word_list:
        words = [w.get("word", "") for w in word_list]
        translations = await engine.translate_batch(words)
        for item, translated in zip(word_list, translations):
            item["word_translated"] = translated

    return hot_data
