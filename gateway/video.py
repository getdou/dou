"""Video metadata extraction, comment fetching, and stream URL resolution.

Handles no-watermark download URL extraction by manipulating Douyin's
CDN URLs to bypass watermark injection.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Any, Optional

from .client import DouyinClient

logger = logging.getLogger("dou.gateway.video")


@dataclass
class VideoMeta:
    """Structured video metadata extracted from Douyin aweme object."""

    aweme_id: str = ""
    description: str = ""
    create_time: int = 0

    # author
    author_id: str = ""
    author_sec_uid: str = ""
    author_name: str = ""
    author_avatar: str = ""
    author_signature: str = ""

    # video
    play_url: str = ""
    play_url_no_wm: str = ""
    cover_url: str = ""
    dynamic_cover: str = ""
    duration: int = 0  # milliseconds
    width: int = 0
    height: int = 0
    ratio: str = ""

    # stats
    like_count: int = 0
    comment_count: int = 0
    share_count: int = 0
    collect_count: int = 0
    play_count: int = 0

    # music
    music_id: str = ""
    music_title: str = ""
    music_author: str = ""
    music_url: str = ""

    # hashtags
    hashtags: list[str] = field(default_factory=list)

    # misc
    is_image_post: bool = False
    image_urls: list[str] = field(default_factory=list)

    @classmethod
    def from_aweme(cls, aweme: dict) -> "VideoMeta":
        """Parse raw Douyin aweme object into structured VideoMeta."""
        video = aweme.get("video", {})
        author = aweme.get("author", {})
        stats = aweme.get("statistics", {})
        music = aweme.get("music", {})

        # extract play URL
        play_addr = video.get("play_addr", {})
        play_url = ""
        if play_addr.get("url_list"):
            # prefer the last URL (usually highest quality)
            play_url = play_addr["url_list"][-1]

        # extract cover
        cover = video.get("cover", {})
        cover_url = cover.get("url_list", [""])[0] if cover.get("url_list") else ""

        # dynamic cover (animated)
        dyn_cover = video.get("dynamic_cover", {})
        dynamic_cover = dyn_cover.get("url_list", [""])[0] if dyn_cover.get("url_list") else ""

        # author avatar
        avatar = author.get("avatar_thumb", {})
        avatar_url = avatar.get("url_list", [""])[0] if avatar.get("url_list") else ""

        # music play URL
        music_play = music.get("play_url", {})
        music_url = ""
        if isinstance(music_play, dict):
            music_url = music_play.get("url_list", [""])[0] if music_play.get("url_list") else ""
        elif isinstance(music_play, str):
            music_url = music_play

        # hashtags
        hashtags = []
        for tag_info in aweme.get("text_extra", []):
            name = tag_info.get("hashtag_name", "")
            if name:
                hashtags.append(name)

        # image post detection
        images = aweme.get("images") or aweme.get("image_post_info", {}).get("images", [])
        is_image_post = bool(images)
        image_urls = []
        if is_image_post:
            for img in images:
                url_list = img.get("url_list", []) if isinstance(img, dict) else []
                if url_list:
                    image_urls.append(url_list[-1])

        # no-watermark URL
        play_url_no_wm = _extract_no_watermark_url(play_url, video)

        return cls(
            aweme_id=aweme.get("aweme_id", ""),
            description=aweme.get("desc", ""),
            create_time=aweme.get("create_time", 0),
            author_id=author.get("uid", ""),
            author_sec_uid=author.get("sec_uid", ""),
            author_name=author.get("nickname", ""),
            author_avatar=avatar_url,
            author_signature=author.get("signature", ""),
            play_url=play_url,
            play_url_no_wm=play_url_no_wm,
            cover_url=cover_url,
            dynamic_cover=dynamic_cover,
            duration=video.get("duration", 0),
            width=video.get("width", 0),
            height=video.get("height", 0),
            ratio=video.get("ratio", ""),
            like_count=stats.get("digg_count", 0),
            comment_count=stats.get("comment_count", 0),
            share_count=stats.get("share_count", 0),
            collect_count=stats.get("collect_count", 0),
            play_count=stats.get("play_count", 0),
            music_id=str(music.get("mid", "")),
            music_title=music.get("title", ""),
            music_author=music.get("author", ""),
            music_url=music_url,
            hashtags=hashtags,
            is_image_post=is_image_post,
            image_urls=image_urls,
        )

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dict for JSON response."""
        return {
            "aweme_id": self.aweme_id,
            "description": self.description,
            "create_time": self.create_time,
            "author": {
                "uid": self.author_id,
                "sec_uid": self.author_sec_uid,
                "nickname": self.author_name,
                "avatar": self.author_avatar,
                "signature": self.author_signature,
            },
            "video": {
                "play_url": self.play_url,
                "play_url_no_watermark": self.play_url_no_wm,
                "cover": self.cover_url,
                "dynamic_cover": self.dynamic_cover,
                "duration_ms": self.duration,
                "width": self.width,
                "height": self.height,
                "ratio": self.ratio,
            },
            "stats": {
                "likes": self.like_count,
                "comments": self.comment_count,
                "shares": self.share_count,
                "collects": self.collect_count,
                "plays": self.play_count,
            },
            "music": {
                "id": self.music_id,
                "title": self.music_title,
                "author": self.music_author,
                "url": self.music_url,
            },
            "hashtags": self.hashtags,
            "is_image_post": self.is_image_post,
            "image_urls": self.image_urls,
        }


def _extract_no_watermark_url(play_url: str, video: dict) -> str:
    """Extract or construct no-watermark video URL.

    Douyin embeds watermarks via a specific CDN path. We can get the
    clean version by:
    1. Using play_addr_265 or play_addr_h264 if available (often no-wm)
    2. Replacing 'playwm' with 'play' in the URL path
    3. Stripping watermark query params
    """
    # try alternative codec URLs first (often watermark-free)
    for key in ("play_addr_265", "play_addr_h264", "download_addr"):
        addr = video.get(key, {})
        if isinstance(addr, dict) and addr.get("url_list"):
            candidate = addr["url_list"][-1]
            if candidate and "playwm" not in candidate:
                return candidate

    if not play_url:
        return ""

    # strip watermark from URL
    clean = play_url.replace("/playwm/", "/play/")
    clean = clean.replace("playwm", "play")

    # remove watermark-related query params
    clean = re.sub(r"[&?]watermark=\d+", "", clean)
    clean = re.sub(r"[&?]logo_name=[^&]*", "", clean)
    clean = re.sub(r"[&?]ratio=\d+p?", "", clean)

    return clean


class VideoService:
    """Fetch individual video data and resolve stream URLs."""

    def __init__(self, client: DouyinClient):
        self.client = client

    async def get_video(self, aweme_id: str) -> VideoMeta:
        """Get full metadata for a single video by ID."""
        data = await self.client.get(
            "/aweme/v1/aweme/detail/",
            params={"aweme_id": aweme_id},
        )
        aweme = data.get("aweme_detail", {})
        if not aweme:
            raise ValueError(f"Video not found: {aweme_id}")
        return VideoMeta.from_aweme(aweme)

    async def get_comments(
        self,
        aweme_id: str,
        count: int = 20,
        cursor: int = 0,
    ) -> dict[str, Any]:
        """Get comment thread for a video."""
        return await self.client.get(
            "/aweme/v1/comment/list/",
            params={
                "aweme_id": aweme_id,
                "count": str(min(count, 50)),
                "cursor": str(cursor),
            },
        )

    async def get_comment_replies(
        self,
        comment_id: str,
        aweme_id: str,
        count: int = 20,
        cursor: int = 0,
    ) -> dict[str, Any]:
        """Get replies to a specific comment."""
        return await self.client.get(
            "/aweme/v1/comment/list/reply/",
            params={
                "comment_id": comment_id,
                "item_id": aweme_id,
                "count": str(min(count, 50)),
                "cursor": str(cursor),
            },
        )

    async def get_related(
        self,
        aweme_id: str,
        count: int = 10,
    ) -> dict[str, Any]:
        """Get related/recommended videos."""
        return await self.client.get(
            "/aweme/v1/aweme/related/",
            params={
                "aweme_id": aweme_id,
                "count": str(min(count, 30)),
            },
        )

    async def resolve_share_url(self, share_url: str) -> Optional[str]:
        """Resolve a Douyin share URL to an aweme_id.

        Share URLs look like: https://v.douyin.com/xxxxx/
        """
        try:
            resp = await self.client.get_web(share_url)
            # follow redirects to get the canonical URL with aweme_id
            final_url = str(resp.url)
            match = re.search(r"/video/(\d+)", final_url)
            if match:
                return match.group(1)

            # try extracting from page content
            match = re.search(r'"awemeId":"(\d+)"', resp.text)
            if match:
                return match.group(1)

        except Exception as exc:
            logger.warning("Failed to resolve share URL %s: %s", share_url, exc)

        return None
