"""Feed endpoints — trending, search, hashtag, hot search."""

from __future__ import annotations

from fastapi import APIRouter, Request, Query

from gateway import FeedService
from translate.batch import translate_feed, translate_search_results, translate_hot_search

router = APIRouter()


def _services(request: Request):
    return (
        FeedService(request.app.state.douyin_client),
        request.app.state.translator,
    )


@router.get("/trending")
async def get_trending(
    request: Request,
    count: int = Query(20, ge=1, le=50, description="Number of videos"),
    cursor: int = Query(0, ge=0, description="Pagination cursor"),
    translate: bool = Query(True, description="Auto-translate to English"),
):
    """Get trending/recommended videos from Douyin."""
    feed_svc, translator = _services(request)
    data = await feed_svc.trending(count=count, cursor=cursor)
    if translate:
        data = await translate_feed(translator, data)
    return data


@router.get("/search")
async def search_videos(
    request: Request,
    q: str = Query(..., min_length=1, description="Search query (English or Chinese)"),
    count: int = Query(20, ge=1, le=50),
    cursor: int = Query(0, ge=0),
    sort: int = Query(0, description="0=relevance, 1=most liked, 2=newest"),
    time: int = Query(0, description="0=all, 1=24h, 7=week, 180=6months"),
    translate: bool = Query(True),
):
    """Search Douyin videos. English queries are auto-translated to Chinese."""
    feed_svc, translator = _services(request)

    # auto-translate english search queries to chinese
    search_query = q
    if translate and not translator._has_chinese(q):
        search_query = await translator.translate_to_chinese(q)

    data = await feed_svc.search(
        query=search_query,
        count=count,
        cursor=cursor,
        sort_type=sort,
        publish_time=time,
    )

    if translate:
        data = await translate_search_results(translator, data)

    # include original and translated query in response
    data["_query"] = {"original": q, "searched": search_query}
    return data


@router.get("/suggest")
async def search_suggest(
    request: Request,
    q: str = Query(..., min_length=1),
    translate: bool = Query(True),
):
    """Get search autocomplete suggestions."""
    feed_svc, translator = _services(request)

    search_q = q
    if translate and not translator._has_chinese(q):
        search_q = await translator.translate_to_chinese(q)

    return await feed_svc.search_suggest(search_q)


@router.get("/hashtag/{hashtag_name}")
async def get_hashtag_feed(
    request: Request,
    hashtag_name: str,
    count: int = Query(20, ge=1, le=50),
    cursor: int = Query(0, ge=0),
    translate: bool = Query(True),
):
    """Get videos under a hashtag. Accepts Chinese or English hashtag names."""
    feed_svc, translator = _services(request)

    # search for hashtag ID
    search = await feed_svc.hashtag_search(hashtag_name)
    challenge_list = search.get("challenge_list", [])
    if not challenge_list:
        return {"aweme_list": [], "has_more": False, "message": "hashtag not found"}

    hashtag_id = str(challenge_list[0].get("cid", ""))
    data = await feed_svc.hashtag(hashtag_id=hashtag_id, count=count, cursor=cursor)

    if translate:
        data = await translate_feed(translator, data)

    # include hashtag info in response
    data["_hashtag"] = {
        "id": hashtag_id,
        "name": challenge_list[0].get("cha_name", hashtag_name),
        "view_count": challenge_list[0].get("view_count", 0),
    }
    return data


@router.get("/hot")
async def get_hot_search(
    request: Request,
    translate: bool = Query(True),
):
    """Get Douyin hot search keywords (what's trending right now)."""
    feed_svc, translator = _services(request)
    data = await feed_svc.hot_search()
    if translate:
        data = await translate_hot_search(translator, data)
    return data


@router.get("/board")
async def get_hot_board(
    request: Request,
    type: int = Query(0, description="0=hot, 1=entertainment, 2=society, 3=challenge"),
    translate: bool = Query(True),
):
    """Get hot board (leaderboard) content."""
    feed_svc, translator = _services(request)
    data = await feed_svc.hot_board(board_type=type)
    if translate:
        data = await translate_feed(translator, data)
    return data
