"""WebSocket endpoint for live feed streaming.

Clients connect and request batches of translated videos.
Useful for building real-time feed UIs without polling.

Protocol:
    Client sends: {"action": "next", "count": 5}
    Server sends: {"type": "video", "data": {...}} (one per video)
    Server sends: {"type": "batch_end", "cursor": 12345}

    Client sends: {"action": "ping"}
    Server sends: {"type": "pong", "ts": 1234567890}
"""

from __future__ import annotations

import json
import logging
import time

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from gateway import FeedService
from translate.batch import translate_feed
from gateway.video import VideoMeta

logger = logging.getLogger("dou.api.ws")
router = APIRouter()


@router.websocket("/feed")
async def live_feed(websocket: WebSocket):
    """Stream translated trending videos over WebSocket."""
    await websocket.accept()

    client_ip = websocket.client.host if websocket.client else "unknown"
    logger.info("WebSocket connected: %s", client_ip)

    client = websocket.app.state.douyin_client
    translator = websocket.app.state.translator
    feed_svc = FeedService(client)

    cursor = 0

    try:
        while True:
            raw = await websocket.receive_text()

            try:
                msg = json.loads(raw)
            except json.JSONDecodeError:
                await websocket.send_json({
                    "type": "error",
                    "message": "invalid JSON",
                })
                continue

            action = msg.get("action", "")

            if action == "next":
                count = min(msg.get("count", 5), 20)

                try:
                    feed_data = await feed_svc.trending(count=count, cursor=cursor)
                    feed_data = await translate_feed(translator, feed_data)

                    aweme_list = feed_data.get("aweme_list", [])
                    for aweme in aweme_list:
                        meta = VideoMeta.from_aweme(aweme)
                        video_data = meta.to_dict()
                        video_data["description_translated"] = aweme.get(
                            "desc_translated", ""
                        )

                        await websocket.send_json({
                            "type": "video",
                            "data": video_data,
                        })

                    cursor = feed_data.get("max_cursor", cursor + count)

                    await websocket.send_json({
                        "type": "batch_end",
                        "cursor": cursor,
                        "count": len(aweme_list),
                    })

                except Exception as exc:
                    logger.error("Feed fetch error: %s", exc)
                    await websocket.send_json({
                        "type": "error",
                        "message": "failed to fetch feed",
                    })

            elif action == "ping":
                await websocket.send_json({
                    "type": "pong",
                    "ts": int(time.time()),
                })

            else:
                await websocket.send_json({
                    "type": "error",
                    "message": f"unknown action: {action}",
                })

    except WebSocketDisconnect:
        logger.info("WebSocket disconnected: %s", client_ip)
    except Exception as exc:
        logger.error("WebSocket error: %s", exc)
        try:
            await websocket.close(code=1011)
        except Exception:
            pass
