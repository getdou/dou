"""dòu gateway — reverse-engineered douyin API client.

Provides geo-unrestricted access to Douyin's content API using
device fingerprint spoofing and request signature generation.
"""

from .client import DouyinClient
from .auth import DeviceAuth, DeviceFingerprint
from .feeds import FeedService
from .video import VideoService

__all__ = ["DouyinClient", "DeviceAuth", "DeviceFingerprint", "FeedService", "VideoService"]
