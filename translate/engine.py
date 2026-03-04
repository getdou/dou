"""Translation engine backed by DeepSeek API with async Redis caching.

Design goals:
- Low latency: cache aggressively, batch when possible
- High quality: use DeepSeek (trained on Chinese internet data) not Google Translate
- Slang-aware: pre-process known Douyin slang before API call
- Graceful degradation: return raw text if translation fails
"""

from __future__ import annotations

import asyncio
import hashlib
import logging
import os
from typing import Optional

import httpx

from .slang import DOUYIN_SLANG

logger = logging.getLogger("dou.translate")

DEEPSEEK_CHAT_API = "https://api.deepseek.com/v1/chat/completions"

SYSTEM_PROMPT = """You are a translator for Chinese social media content from Douyin (抖音).

Rules:
- Translate Chinese to natural, casual English
- Preserve the original tone (funny, dramatic, informative, etc.)
- Translate internet slang to English equivalents (e.g. 绝了 → "fire", YYDS → "GOAT")
- Keep hashtags as-is but add (english meaning) after them
- Keep @mentions and emojis unchanged
- If text is already English or has no Chinese characters, return as-is
- Output ONLY the translation. No explanations, no quotes, no prefixes.
- Keep it concise — don't over-explain jokes or cultural references"""


class TranslationEngine:
    """Translate Chinese text using DeepSeek with Redis cache.

    Usage:
        engine = TranslationEngine()
        result = await engine.translate("你好世界")
        # -> "hello world"
    """

    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
        redis_url: str | None = None,
        cache_ttl: int | None = None,
    ):
        self.api_key = api_key or os.getenv("DEEPSEEK_API_KEY", "")
        self.model = model or os.getenv("DEEPSEEK_MODEL", "deepseek-chat")
        self.cache_ttl = cache_ttl or int(os.getenv("TRANSLATION_CACHE_TTL", "3600"))
        self._redis_url = redis_url or os.getenv("REDIS_URL", "redis://localhost:6379")
        self._redis = None
        self._redis_available = None  # tri-state: None=untested, True/False
        self._http: Optional[httpx.AsyncClient] = None
        self._semaphore = asyncio.Semaphore(10)  # max concurrent API calls

    async def _get_redis(self):
        """Lazy-init Redis connection. Returns None if unavailable."""
        if self._redis_available is False:
            return None

        if self._redis is None:
            try:
                import redis.asyncio as aioredis
                self._redis = aioredis.from_url(
                    self._redis_url,
                    decode_responses=True,
                    socket_timeout=2.0,
                    socket_connect_timeout=2.0,
                )
                await self._redis.ping()
                self._redis_available = True
                logger.info("Redis connected at %s", self._redis_url)
            except Exception as exc:
                logger.warning("Redis unavailable (%s), caching disabled", exc)
                self._redis = None
                self._redis_available = False
                return None

        return self._redis

    async def _get_http(self) -> httpx.AsyncClient:
        if self._http is None or self._http.is_closed:
            self._http = httpx.AsyncClient(
                timeout=30.0,
                limits=httpx.Limits(max_connections=20),
            )
        return self._http

    @staticmethod
    def _cache_key(text: str) -> str:
        return f"dou:tr:{hashlib.md5(text.encode()).hexdigest()}"

    @staticmethod
    def _has_chinese(text: str) -> bool:
        """Check if text contains Chinese characters."""
        return any("\u4e00" <= c <= "\u9fff" or "\u3400" <= c <= "\u4dbf" for c in text)

    def _preprocess_slang(self, text: str) -> str:
        """Replace known Douyin slang before sending to DeepSeek.

        This improves translation quality for terms that even
        DeepSeek occasionally misinterprets.
        """
        result = text
        for cn, en in DOUYIN_SLANG.items():
            if cn in result:
                result = result.replace(cn, f"[{en}]")
        return result

    async def translate(self, text: str) -> str:
        """Translate Chinese text to English.

        Returns cached result if available. Falls back to raw text
        if translation fails.
        """
        if not text or not text.strip():
            return text

        # skip if no chinese characters
        if not self._has_chinese(text):
            return text

        # check cache
        r = await self._get_redis()
        if r:
            try:
                cached = await r.get(self._cache_key(text))
                if cached:
                    return cached
            except Exception:
                pass

        # no API key = return raw text
        if not self.api_key:
            logger.warning("No DEEPSEEK_API_KEY set")
            return text

        # preprocess slang
        preprocessed = self._preprocess_slang(text)

        # call DeepSeek API with concurrency limit
        async with self._semaphore:
            translated = await self._call_deepseek(preprocessed, text)

        # cache result
        if r and translated != text:
            try:
                await r.setex(self._cache_key(text), self.cache_ttl, translated)
            except Exception:
                pass

        return translated

    async def _call_deepseek(self, preprocessed: str, original: str) -> str:
        """Make DeepSeek API call for translation."""
        client = await self._get_http()

        try:
            resp = await client.post(
                DEEPSEEK_CHAT_API,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": self.model,
                    "messages": [
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": preprocessed},
                    ],
                    "temperature": 0.2,
                    "max_tokens": 2048,
                    "stream": False,
                },
            )
            resp.raise_for_status()
            data = resp.json()

            translated = (
                data.get("choices", [{}])[0]
                .get("message", {})
                .get("content", "")
                .strip()
            )

            if translated:
                return translated
            return original

        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 429:
                logger.warning("DeepSeek rate limited, returning raw text")
                await asyncio.sleep(1.0)
            else:
                logger.error("DeepSeek API error %s: %s", exc.response.status_code, exc)
            return original

        except Exception as exc:
            logger.error("Translation failed: %s", exc)
            return original

    async def translate_batch(self, texts: list[str]) -> list[str]:
        """Translate multiple texts concurrently.

        Uses cache for hits, fires concurrent API calls for misses.
        """
        if not texts:
            return []

        results: list[str | None] = [None] * len(texts)
        to_translate: list[tuple[int, str]] = []

        # first pass: check cache and skip non-chinese
        r = await self._get_redis()
        for i, text in enumerate(texts):
            if not text or not text.strip() or not self._has_chinese(text):
                results[i] = text
                continue

            if r:
                try:
                    cached = await r.get(self._cache_key(text))
                    if cached:
                        results[i] = cached
                        continue
                except Exception:
                    pass

            to_translate.append((i, text))

        # second pass: concurrent translation for cache misses
        if to_translate:
            tasks = [self.translate(text) for _, text in to_translate]
            translated = await asyncio.gather(*tasks, return_exceptions=True)

            for (idx, original), result in zip(to_translate, translated):
                if isinstance(result, Exception):
                    logger.error("Batch translation error for index %d: %s", idx, result)
                    results[idx] = original
                else:
                    results[idx] = result

        return results

    async def translate_to_chinese(self, text: str) -> str:
        """Translate English text to Chinese (for search query translation)."""
        if self._has_chinese(text):
            return text  # already chinese

        if not self.api_key:
            return text

        client = await self._get_http()
        try:
            resp = await client.post(
                DEEPSEEK_CHAT_API,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": self.model,
                    "messages": [
                        {
                            "role": "system",
                            "content": "Translate the following English text to Chinese. "
                                       "Output ONLY the Chinese translation, nothing else. "
                                       "Use natural Chinese that would be used on Douyin.",
                        },
                        {"role": "user", "content": text},
                    ],
                    "temperature": 0.2,
                    "max_tokens": 512,
                },
            )
            resp.raise_for_status()
            data = resp.json()
            result = data["choices"][0]["message"]["content"].strip()
            return result if result else text
        except Exception as exc:
            logger.error("EN->CN translation failed: %s", exc)
            return text

    async def close(self):
        if self._http and not self._http.is_closed:
            await self._http.aclose()
        if self._redis:
            await self._redis.close()
