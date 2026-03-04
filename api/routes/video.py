"""Video endpoints — detail, comments, download, related."""

from __future__ import annotations

from fastapi import APIRouter, Request, Query, HTTPException
from fastapi.responses import RedirectResponse

from gateway import VideoService
from translate.batch import translate_comments

router = APIRouter()


def _services(request: Request):
    return (
        VideoService(request.app.state.douyin_client),
        request.app.state.translator,
    )


@router.get("/{aweme_id}")
async def get_video(
    request: Request,
    aweme_id: str,
    translate: bool = Query(True),
):
    """Get full metadata for a single video."""
    video_svc, translator = _services(request)

    try:
        meta = await video_svc.get_video(aweme_id)
    except ValueError:
        raise HTTPException(404, detail="Video not found")

    result = meta.to_dict()

    if translate and meta.description:
        result["description_translated"] = await translator.translate(meta.description)

    if translate and meta.author_signature:
        result["author"]["signature_translated"] = await translator.translate(
            meta.author_signature
        )

    return result


@router.get("/{aweme_id}/comments")
async def get_comments(
    request: Request,
    aweme_id: str,
    count: int = Query(20, ge=1, le=50),
    cursor: int = Query(0, ge=0),
    translate: bool = Query(True),
):
    """Get video comments with optional translation."""
    video_svc, translator = _services(request)
    data = await video_svc.get_comments(aweme_id, count=count, cursor=cursor)
    if translate:
        data = await translate_comments(translator, data)
    return data


@router.get("/{aweme_id}/comments/{comment_id}/replies")
async def get_comment_replies(
    request: Request,
    aweme_id: str,
    comment_id: str,
    count: int = Query(20, ge=1, le=50),
    cursor: int = Query(0, ge=0),
    translate: bool = Query(True),
):
    """Get replies to a specific comment."""
    video_svc, translator = _services(request)
    data = await video_svc.get_comment_replies(
        comment_id=comment_id,
        aweme_id=aweme_id,
        count=count,
        cursor=cursor,
    )
    if translate:
        data = await translate_comments(translator, data)
    return data


@router.get("/{aweme_id}/download")
async def download_video(request: Request, aweme_id: str):
    """Redirect to no-watermark video download URL."""
    video_svc, _ = _services(request)

    try:
        meta = await video_svc.get_video(aweme_id)
    except ValueError:
        raise HTTPException(404, detail="Video not found")

    url = meta.play_url_no_wm or meta.play_url
    if not url:
        raise HTTPException(404, detail="No video URL available")

    return RedirectResponse(url=url, status_code=302)


@router.get("/{aweme_id}/related")
async def get_related(
    request: Request,
    aweme_id: str,
    count: int = Query(10, ge=1, le=30),
):
    """Get related/recommended videos."""
    video_svc, _ = _services(request)
    return await video_svc.get_related(aweme_id, count=count)


@router.get("/resolve/share")
async def resolve_share_url(
    request: Request,
    url: str = Query(..., description="Douyin share URL (v.douyin.com/...)"),
):
    """Resolve a Douyin share URL to a video ID and metadata."""
    video_svc, translator = _services(request)
    aweme_id = await video_svc.resolve_share_url(url)
    if not aweme_id:
        raise HTTPException(400, detail="Could not resolve share URL")

    meta = await video_svc.get_video(aweme_id)
    result = meta.to_dict()
    result["description_translated"] = await translator.translate(meta.description)
    return result
