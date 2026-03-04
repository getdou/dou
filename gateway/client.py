"""Core async HTTP client for Douyin's internal API.

Handles:
- Request signing via DeviceAuth
- Automatic endpoint failover across API hosts
- Retry with exponential backoff
- Cookie/session persistence
- Optional proxy support for enhanced geo-bypass
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Optional
from urllib.parse import urlencode

import httpx

from .auth import DeviceAuth

logger = logging.getLogger("dou.gateway.client")

# primary and fallback API hosts
DOUYIN_HOSTS = [
    "https://api-ly.amemv.com",
    "https://api.amemv.com",
    "https://api-hl.amemv.com",
    "https://api-al.amemv.com",
    "https://api16-normal-c-useast2a.tiktokv.com",
]

# web API (for share links, SEO pages)
DOUYIN_WEB_API = "https://www.douyin.com"


class DouyinClient:
    """Async HTTP client for Douyin's API with automatic signing and failover.

    Usage:
        async with DouyinClient() as client:
            data = await client.get("/aweme/v1/feed/", {"count": "20"})
    """

    def __init__(
        self,
        auth: DeviceAuth | None = None,
        timeout: float = 20.0,
        max_retries: int = 2,
    ):
        self.auth = auth or DeviceAuth()
        self.timeout = timeout
        self.max_retries = max_retries
        self._client: Optional[httpx.AsyncClient] = None
        self._host_index = 0
        self._registered = False

    @property
    def _current_host(self) -> str:
        return DOUYIN_HOSTS[self._host_index % len(DOUYIN_HOSTS)]

    def _next_host(self):
        self._host_index = (self._host_index + 1) % len(DOUYIN_HOSTS)
        logger.info("Failing over to %s", self._current_host)

    async def _ensure_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            transport_kwargs = {}
            if self.auth.proxy:
                transport_kwargs["proxy"] = self.auth.proxy

            self._client = httpx.AsyncClient(
                timeout=self.timeout,
                http2=False,
                follow_redirects=True,
                limits=httpx.Limits(
                    max_connections=100,
                    max_keepalive_connections=30,
                    keepalive_expiry=30.0,
                ),
                **transport_kwargs,
            )
        return self._client

    async def _ensure_registered(self):
        """Register device on first request if needed."""
        if self._registered:
            return
        client = await self._ensure_client()
        result = await self.auth.register_device(client)
        if result:
            logger.info("Device registered: %s", self.auth.fingerprint.device_id[:12])
        self._registered = True  # don't retry registration even if it fails

    async def get(
        self,
        endpoint: str,
        params: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        """Make authenticated GET request to Douyin API.

        Automatically signs the request, handles failover across hosts,
        and retries on transient failures.
        """
        await self._ensure_registered()

        merged_params = {**self.auth.get_common_params(), **(params or {})}
        headers = self.auth.sign_request(endpoint, merged_params)
        client = await self._ensure_client()

        last_error: Exception | None = None

        for host_attempt in range(len(DOUYIN_HOSTS)):
            host = DOUYIN_HOSTS[(self._host_index + host_attempt) % len(DOUYIN_HOSTS)]

            for retry in range(self.max_retries + 1):
                try:
                    url = f"{host}{endpoint}"
                    resp = await client.get(
                        url, params=merged_params, headers=headers
                    )

                    # update cookies from response
                    if resp.cookies:
                        self.auth.update_cookies(dict(resp.cookies))

                    if resp.status_code == 200:
                        try:
                            data = resp.json()
                        except Exception:
                            logger.warning("Non-JSON response from %s", url)
                            break

                        status = data.get("status_code", -1)
                        if status == 0 or "aweme_list" in data or "data" in data:
                            # success — update preferred host
                            self._host_index = (self._host_index + host_attempt) % len(DOUYIN_HOSTS)
                            return data

                        logger.warning(
                            "API error status=%s from %s%s",
                            status, host, endpoint,
                        )
                        last_error = ValueError(f"API status {status}")
                        break  # don't retry same host for API-level errors

                    elif resp.status_code == 429:
                        # rate limited — wait and retry
                        wait = min(2 ** retry * 0.5, 8.0)
                        logger.warning("Rate limited, waiting %.1fs", wait)
                        await asyncio.sleep(wait)
                        continue

                    else:
                        logger.warning(
                            "HTTP %s from %s%s",
                            resp.status_code, host, endpoint,
                        )
                        last_error = httpx.HTTPStatusError(
                            f"HTTP {resp.status_code}",
                            request=resp.request,
                            response=resp,
                        )
                        break

                except httpx.TimeoutException as exc:
                    logger.warning(
                        "Timeout on %s%s (attempt %d/%d)",
                        host, endpoint, retry + 1, self.max_retries + 1,
                    )
                    last_error = exc
                    if retry < self.max_retries:
                        await asyncio.sleep(0.5 * (retry + 1))

                except httpx.ConnectError as exc:
                    logger.warning("Connection failed to %s: %s", host, exc)
                    last_error = exc
                    break  # try next host immediately

        raise ConnectionError(
            f"All {len(DOUYIN_HOSTS)} hosts exhausted for {endpoint}: {last_error}"
        )

    async def post(
        self,
        endpoint: str,
        data: dict | None = None,
        json_data: dict | None = None,
        params: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        """Make authenticated POST request to Douyin API."""
        await self._ensure_registered()

        merged_params = {**self.auth.get_common_params(), **(params or {})}
        body = None
        if data:
            body = urlencode(data).encode()
        elif json_data:
            import json as json_mod
            body = json_mod.dumps(json_data).encode()

        headers = self.auth.sign_request(endpoint, merged_params, body=body)
        if data:
            headers["Content-Type"] = "application/x-www-form-urlencoded"
        elif json_data:
            headers["Content-Type"] = "application/json"

        client = await self._ensure_client()
        url = f"{self._current_host}{endpoint}"

        resp = await client.post(
            url,
            content=body,
            params=merged_params,
            headers=headers,
        )

        if resp.cookies:
            self.auth.update_cookies(dict(resp.cookies))

        resp.raise_for_status()
        return resp.json()

    async def get_web(
        self,
        url: str,
        params: dict[str, str] | None = None,
    ) -> httpx.Response:
        """Make request to Douyin web (for share links, embeds)."""
        client = await self._ensure_client()
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                          "AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Referer": "https://www.douyin.com/",
        }
        return await client.get(url, params=params, headers=headers)

    async def close(self):
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        await self.close()
