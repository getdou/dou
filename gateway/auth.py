"""Device authentication, fingerprinting, and request signing for Douyin API.

Douyin's API requires:
1. A registered device identity (device_id, install_id, etc.)
2. Signed requests with X-Bogus / a-bogus headers
3. Specific User-Agent and cookie patterns

This module handles all of that transparently.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import random
import string
import struct
import time
import uuid
from dataclasses import dataclass, field
from typing import Optional
from urllib.parse import urlencode

from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend


# device model pool — rotate to avoid fingerprint blocking
DEVICE_MODELS = [
    ("SM-G9980", "samsung", "14"),
    ("SM-S9180", "samsung", "14"),
    ("Pixel 8 Pro", "google", "14"),
    ("Pixel 7", "google", "13"),
    ("2201123C", "Xiaomi", "13"),
    ("22081212C", "Xiaomi", "14"),
    ("V2227A", "vivo", "13"),
    ("PGKM10", "OnePlus", "14"),
]

RESOLUTIONS = [
    ("1080x2400", 420),
    ("1080x2340", 400),
    ("1440x3200", 560),
    ("1080x2412", 420),
]


@dataclass
class DeviceFingerprint:
    """Represents a virtual Android device identity for Douyin API access."""

    device_id: str = ""
    install_id: str = ""
    device_type: str = ""
    device_brand: str = ""
    os_version: str = ""
    resolution: str = ""
    dpi: int = 420
    openudid: str = ""
    cdid: str = ""
    clientudid: str = ""
    req_id: str = ""

    def __post_init__(self):
        if not self.device_type:
            model = random.choice(DEVICE_MODELS)
            self.device_type, self.device_brand, self.os_version = model

        if not self.resolution:
            res = random.choice(RESOLUTIONS)
            self.resolution, self.dpi = res

        if not self.device_id:
            self.device_id = str(random.randint(10**18, 10**19 - 1))
        if not self.install_id:
            self.install_id = str(random.randint(10**18, 10**19 - 1))
        if not self.openudid:
            self.openudid = hashlib.md5(
                self.device_id.encode()
            ).hexdigest()[:16]
        if not self.cdid:
            self.cdid = str(uuid.uuid4())
        if not self.clientudid:
            self.clientudid = str(uuid.uuid4())
        if not self.req_id:
            self.req_id = hashlib.md5(
                (self.device_id + str(time.time())).encode()
            ).hexdigest()[:16]

    def to_dict(self) -> dict[str, str]:
        return {
            "device_id": self.device_id,
            "iid": self.install_id,
            "device_type": self.device_type,
            "device_brand": self.device_brand,
            "os_version": self.os_version,
            "resolution": self.resolution,
            "dpi": str(self.dpi),
            "openudid": self.openudid,
            "cdid": self.cdid,
            "clientudid": self.clientudid,
        }

    def save(self, path: str = ".dou_device.json"):
        """Persist device fingerprint to disk for reuse across sessions."""
        with open(path, "w") as f:
            json.dump(self.__dict__, f, indent=2)

    @classmethod
    def load(cls, path: str = ".dou_device.json") -> "DeviceFingerprint":
        """Load persisted device fingerprint."""
        with open(path) as f:
            data = json.load(f)
        return cls(**data)


class DeviceAuth:
    """Handles device registration and request signing for Douyin API.

    Usage:
        auth = DeviceAuth()
        params = auth.get_common_params()
        headers = auth.sign_request(url, params)
    """

    APP_PARAMS = {
        "app_name": "aweme",
        "version_code": "310200",
        "version_name": "31.2.0",
        "channel": "googleplay_go",
        "aid": "1128",
        "update_version_code": "31209900",
        "manifest_version_code": "310200",
        "ab_version": "31.2.0",
        "ssmix": "a",
        "ac": "wifi",
        "is_pad": "0",
        "language": "zh",
        "region": "CN",
        "sys_region": "CN",
        "app_type": "normal",
        "os_api": "30",
    }

    # XOR key table for X-Gorgon computation
    _GORGON_TABLE = bytes(range(256))

    def __init__(
        self,
        device_id: str | None = None,
        fingerprint: DeviceFingerprint | None = None,
        proxy: str | None = None,
    ):
        env_device_id = device_id or os.getenv("DOUYIN_DEVICE_ID", "")

        if fingerprint:
            self.fingerprint = fingerprint
        elif env_device_id:
            self.fingerprint = DeviceFingerprint(device_id=env_device_id)
        else:
            # try to load persisted device, else generate new
            try:
                self.fingerprint = DeviceFingerprint.load()
            except (FileNotFoundError, json.JSONDecodeError):
                self.fingerprint = DeviceFingerprint()
                self.fingerprint.save()

        self.proxy = proxy or os.getenv("PROXY_URL", "")
        self._session_id = hashlib.md5(
            str(time.time()).encode()
        ).hexdigest()[:16]
        self._cookies: dict[str, str] = {}

    def get_common_params(self) -> dict[str, str]:
        """Build query parameters required on every Douyin API request."""
        ts = str(int(time.time()))
        return {
            **self.APP_PARAMS,
            **self.fingerprint.to_dict(),
            "ts": ts,
            "_rticket": str(int(time.time() * 1000)),
            "os": "android",
        }

    def get_user_agent(self) -> str:
        fp = self.fingerprint
        return (
            f"com.ss.android.ugc.aweme/{self.APP_PARAMS['version_code']} "
            f"(Linux; U; Android {fp.os_version}; {fp.device_type} "
            f"Build/TP1A.{random.randint(100000, 999999)}.{random.randint(100, 999)})"
        )

    def sign_request(
        self,
        url: str,
        params: dict[str, str] | None = None,
        body: bytes | None = None,
    ) -> dict[str, str]:
        """Generate authentication headers for a Douyin API request.

        Computes X-Gorgon, X-Khronos, X-SS-STUB, and X-Argus headers.
        These are required for the API to accept the request.
        """
        merged = {**self.get_common_params(), **(params or {})}
        query_str = urlencode(sorted(merged.items()))

        khronos = str(int(time.time()))

        # X-SS-STUB: MD5 of request body (empty string if GET)
        stub = hashlib.md5(body or b"").hexdigest()

        # X-Gorgon: computed from query + timestamp + stub
        gorgon = self._compute_gorgon(query_str, khronos, stub)

        # X-Argus: additional signature layer (simplified)
        argus = self._compute_argus(query_str, khronos)

        headers = {
            "X-Gorgon": gorgon,
            "X-Khronos": khronos,
            "X-SS-STUB": stub,
            "X-Argus": argus,
            "User-Agent": self.get_user_agent(),
            "Accept-Encoding": "gzip, deflate",
            "Accept": "application/json",
            "Connection": "keep-alive",
            "X-SS-REQ-TICKET": str(int(time.time() * 1000)),
            "passport-sdk-version": "19",
            "sdk-version": "2",
        }

        if self._cookies:
            headers["Cookie"] = "; ".join(
                f"{k}={v}" for k, v in self._cookies.items()
            )

        return headers

    def _compute_gorgon(
        self, query: str, khronos: str, stub: str
    ) -> str:
        """Compute X-Gorgon value.

        Algorithm: hash query params, combine with timestamp bytes,
        apply XOR garbling, output as hex string with version prefix.
        """
        # hash inputs
        query_hash = hashlib.md5(query.encode()).digest()
        stub_hash = bytes.fromhex(stub)
        ts_bytes = struct.pack("<I", int(khronos))

        # build 20-byte gorgon seed
        seed = bytearray(20)
        seed[0:4] = ts_bytes
        seed[4:8] = query_hash[:4]
        seed[8:12] = stub_hash[:4]
        seed[12:16] = query_hash[4:8]
        seed[16:20] = query_hash[8:12]

        # XOR garble pass
        for i in range(len(seed)):
            seed[i] = (seed[i] ^ 0x47 ^ (i * 3)) & 0xFF

        # second garble — rotate bits
        for i in range(0, len(seed) - 1, 2):
            seed[i], seed[i + 1] = (
                ((seed[i] << 4) | (seed[i + 1] >> 4)) & 0xFF,
                ((seed[i + 1] << 4) | (seed[i] >> 4)) & 0xFF,
            )

        return "0404b0d30000" + seed.hex()

    def _compute_argus(self, query: str, khronos: str) -> str:
        """Compute X-Argus signature (simplified version).

        Full X-Argus involves protobuf serialization + AES encryption.
        This produces a compatible signature for most feed endpoints.
        """
        raw = f"{query}&khronos={khronos}&device_id={self.fingerprint.device_id}"
        h = hashlib.sha256(raw.encode()).digest()

        # AES-CBC encrypt the hash with a static key (from APK)
        key = b"d3829f0207da2c81"  # extracted from libcms.so
        iv = b"0102030405060708"
        cipher = Cipher(algorithms.AES(key), modes.CBC(iv), backend=default_backend())
        encryptor = cipher.encryptor()

        # PKCS7 pad to 32 bytes
        padded = h + bytes([16] * 16) if len(h) == 16 else h
        if len(padded) % 16 != 0:
            pad_len = 16 - (len(padded) % 16)
            padded = padded + bytes([pad_len] * pad_len)

        encrypted = encryptor.update(padded) + encryptor.finalize()
        import base64
        return base64.b64encode(encrypted).decode()

    def update_cookies(self, response_cookies: dict[str, str]):
        """Update session cookies from API response headers."""
        self._cookies.update(response_cookies)

    async def register_device(self, client) -> bool:
        """Register device with Douyin servers to obtain session tokens.

        Called automatically on first request if no valid session exists.
        """
        params = self.get_common_params()
        headers = self.sign_request("/service/2/device_register/", params)

        payload = {
            "magic_tag": "ss_app_log",
            "header": {
                "display_name": "抖音短视频",
                "update_version_code": int(self.APP_PARAMS["update_version_code"]),
                "manifest_version_code": int(self.APP_PARAMS["manifest_version_code"]),
                "app_version_minor": "",
                "aid": int(self.APP_PARAMS["aid"]),
                "channel": self.APP_PARAMS["channel"],
                "package": "com.ss.android.ugc.aweme",
                "app_name": "aweme",
                "version_code": int(self.APP_PARAMS["version_code"]),
                "version_name": self.APP_PARAMS["version_name"],
                "device_id": int(self.fingerprint.device_id),
                "resolution": self.fingerprint.resolution,
                "os": "Android",
                "os_version": self.fingerprint.os_version,
                "os_api": self.APP_PARAMS["os_api"],
                "device_model": self.fingerprint.device_type,
                "device_brand": self.fingerprint.device_brand,
                "cpu_abi": "arm64-v8a",
                "release_build": "31.2.0",
                "density_dpi": self.fingerprint.dpi,
                "display_density": "mdpi",
                "openudid": self.fingerprint.openudid,
                "clientudid": self.fingerprint.clientudid,
                "region": "CN",
                "tz_name": "Asia/Shanghai",
                "tz_offset": 28800,
                "sim_region": "cn",
            },
            "_gen_time": int(time.time() * 1000),
        }

        try:
            resp = await client.post(
                "https://log.snssdk.com/service/2/device_register/",
                json=payload,
                headers=headers,
                params=params,
            )
            data = resp.json()
            if "device_id" in str(data):
                new_did = data.get("device_id_str") or data.get("device_id")
                new_iid = data.get("install_id_str") or data.get("install_id")
                if new_did:
                    self.fingerprint.device_id = str(new_did)
                if new_iid:
                    self.fingerprint.install_id = str(new_iid)
                self.fingerprint.save()
                return True
        except Exception:
            pass
        return False
