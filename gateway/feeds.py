"""Feed retrieval — trending, search, hashtag, user, hot search.

Each method returns raw Douyin API response dicts. Translation is
handled separately by the translate layer.
"""

from __future__ import annotations

import logging
from typing import Any

from .client import DouyinClient

logger = logging.getLogger("dou.gateway.feeds")


class FeedService:
    """Fetch Douyin content feeds through the gateway."""

    def __init__(self, client: DouyinClient):
        self.client = client

    async def trending(
        self,
        count: int = 20,
        cursor: int = 0,
        feed_type: int = 0,
    ) -> dict[str, Any]:
        """Get trending/recommended feed.

        Args:
            count: Number of videos (1-50)
            cursor: Pagination cursor (max_cursor from previous response)
            feed_type: 0=recommended, 1=following (requires auth)
        """
        return await self.client.get(
            "/aweme/v1/feed/",
            params={
                "count": str(min(count, 50)),
                "max_cursor": str(cursor),
                "pull_type": "1" if cursor == 0 else "2",
                "type": str(feed_type),
                "address_book_access": "1",
                "gps_access": "1",
                "is_cold_start": "1" if cursor == 0 else "0",
                "filter_warn": "0",
            },
        )

    async def search(
        self,
        query: str,
        count: int = 20,
        cursor: int = 0,
        sort_type: int = 0,
        publish_time: int = 0,
    ) -> dict[str, Any]:
        """Search videos by keyword.

        Args:
            query: Search term (chinese or english — english gets auto-translated)
            count: Results per page
            cursor: Pagination offset
            sort_type: 0=comprehensive, 1=most liked, 2=newest
            publish_time: 0=all time, 1=24h, 7=week, 180=6months
        """
        return await self.client.get(
            "/aweme/v1/general/search/single/",
            params={
                "keyword": query,
                "count": str(min(count, 50)),
                "cursor": str(cursor),
                "sort_type": str(sort_type),
                "publish_time": str(publish_time),
                "search_source": "normal_search",
                "query_correct_type": "1",
                "is_filter_search": "0" if sort_type == 0 and publish_time == 0 else "1",
                "search_id": "",
                "hot_search": "0",
                "enable_history": "1",
            },
        )

    async def search_suggest(self, query: str) -> dict[str, Any]:
        """Get search autocomplete suggestions."""
        return await self.client.get(
            "/aweme/v1/general/search/sug/",
            params={
                "keyword": query,
                "count": "10",
                "source": "video_search",
            },
        )

    async def hashtag(
        self,
        hashtag_id: str,
        count: int = 20,
        cursor: int = 0,
    ) -> dict[str, Any]:
        """Get videos under a specific hashtag/challenge.

        Use hashtag_search() first to resolve a name to an ID.
        """
        return await self.client.get(
            "/aweme/v1/challenge/aweme/",
            params={
                "ch_id": hashtag_id,
                "count": str(min(count, 50)),
                "cursor": str(cursor),
                "query_type": "0",
                "type": "5",
            },
        )

    async def hashtag_search(self, name: str) -> dict[str, Any]:
        """Search for a hashtag by name, returns list with IDs."""
        return await self.client.get(
            "/aweme/v1/challenge/search/",
            params={
                "keyword": name,
                "count": "10",
                "cursor": "0",
                "source": "challenge_detail",
            },
        )

    async def hashtag_detail(self, hashtag_id: str) -> dict[str, Any]:
        """Get hashtag metadata (name, view count, description)."""
        return await self.client.get(
            "/aweme/v1/challenge/detail/",
            params={"ch_id": hashtag_id},
        )

    async def user_videos(
        self,
        sec_user_id: str,
        count: int = 20,
        cursor: int = 0,
    ) -> dict[str, Any]:
        """Get a user's posted videos."""
        return await self.client.get(
            "/aweme/v1/aweme/post/",
            params={
                "sec_user_id": sec_user_id,
                "count": str(min(count, 50)),
                "max_cursor": str(cursor),
                "has_order": "0",
            },
        )

    async def user_profile(self, sec_user_id: str) -> dict[str, Any]:
        """Get user profile information."""
        return await self.client.get(
            "/aweme/v1/user/profile/other/",
            params={"sec_user_id": sec_user_id},
        )

    async def user_liked(
        self,
        sec_user_id: str,
        count: int = 20,
        cursor: int = 0,
    ) -> dict[str, Any]:
        """Get videos a user has liked (if public)."""
        return await self.client.get(
            "/aweme/v1/aweme/favorite/",
            params={
                "sec_user_id": sec_user_id,
                "count": str(min(count, 50)),
                "max_cursor": str(cursor),
            },
        )

    async def hot_search(self) -> dict[str, Any]:
        """Get the Douyin hot search list (real-time trending keywords)."""
        return await self.client.get("/aweme/v1/hot/search/list/")

    async def hot_board(self, board_type: int = 0) -> dict[str, Any]:
        """Get hot board (leaderboard) content.

        Args:
            board_type: 0=hot videos, 1=entertainment, 2=society, 3=challenge
        """
        return await self.client.get(
            "/aweme/v1/hotsearch/aweme/billboard/",
            params={"board_type": str(board_type)},
        )

    async def discover(self) -> dict[str, Any]:
        """Get discover page with category tabs and featured content."""
        return await self.client.get(
            "/aweme/v1/category/list/",
            params={"type": "12"},
        )

    async def music_videos(
        self,
        music_id: str,
        count: int = 20,
        cursor: int = 0,
    ) -> dict[str, Any]:
        """Get videos using a specific sound/music."""
        return await self.client.get(
            "/aweme/v1/music/aweme/",
            params={
                "music_id": music_id,
                "count": str(min(count, 50)),
                "cursor": str(cursor),
            },
        )
