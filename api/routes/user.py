"""User endpoints — profile, videos, liked."""

from __future__ import annotations

from fastapi import APIRouter, Request, Query

from gateway import FeedService
from translate.batch import translate_feed, translate_user_profile

router = APIRouter()


@router.get("/{sec_user_id}")
async def get_user_profile(
    request: Request,
    sec_user_id: str,
    translate: bool = Query(True),
):
    """Get user profile info by sec_user_id."""
    client = request.app.state.douyin_client
    translator = request.app.state.translator
    feed_svc = FeedService(client)

    data = await feed_svc.user_profile(sec_user_id)
    if translate:
        data = await translate_user_profile(translator, data)
    return data


@router.get("/{sec_user_id}/videos")
async def get_user_videos(
    request: Request,
    sec_user_id: str,
    count: int = Query(20, ge=1, le=50),
    cursor: int = Query(0, ge=0),
    translate: bool = Query(True),
):
    """Get a user's posted videos."""
    client = request.app.state.douyin_client
    translator = request.app.state.translator
    feed_svc = FeedService(client)

    data = await feed_svc.user_videos(
        sec_user_id=sec_user_id, count=count, cursor=cursor
    )
    if translate:
        data = await translate_feed(translator, data)
    return data


@router.get("/{sec_user_id}/liked")
async def get_user_liked(
    request: Request,
    sec_user_id: str,
    count: int = Query(20, ge=1, le=50),
    cursor: int = Query(0, ge=0),
    translate: bool = Query(True),
):
    """Get videos a user has liked (if their likes are public)."""
    client = request.app.state.douyin_client
    translator = request.app.state.translator
    feed_svc = FeedService(client)

    data = await feed_svc.user_liked(
        sec_user_id=sec_user_id, count=count, cursor=cursor
    )
    if translate:
        data = await translate_feed(translator, data)
    return data
