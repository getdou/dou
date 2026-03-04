"""Health check — verify gateway connectivity and translation pipeline."""

import asyncio
import sys
import os

# add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from gateway import DouyinClient, DeviceAuth, FeedService
from translate import TranslationEngine


async def main():
    print("dou healthcheck")
    print("=" * 50)

    # 1. device auth
    auth = DeviceAuth()
    print(f"  device_id:    {auth.fingerprint.device_id}")
    print(f"  install_id:   {auth.fingerprint.install_id}")
    print(f"  device_type:  {auth.fingerprint.device_type}")
    print(f"  os_version:   {auth.fingerprint.os_version}")
    print()

    # 2. gateway connectivity
    print("[gateway]")
    async with DouyinClient(auth=auth) as client:
        feed_svc = FeedService(client)

        try:
            data = await feed_svc.trending(count=3)
            items = data.get("aweme_list", [])
            if items:
                print(f"  status: OK ({len(items)} videos)")
                for i, item in enumerate(items[:3]):
                    desc = item.get("desc", "")[:60]
                    author = item.get("author", {}).get("nickname", "?")
                    likes = item.get("statistics", {}).get("digg_count", 0)
                    print(f"  [{i+1}] @{author}: {desc}... ({likes} likes)")
            else:
                print("  status: WARN - connected but 0 videos returned")
        except Exception as e:
            print(f"  status: FAIL - {e}")

    print()

    # 3. translation
    print("[translation]")
    engine = TranslationEngine()

    if not engine.api_key:
        print("  status: SKIP - no DEEPSEEK_API_KEY in env")
    else:
        test_cases = [
            ("你好世界", "should translate to 'hello world' or similar"),
            ("绝绝子", "should translate douyin slang"),
            ("yyds", "should recognize internet acronym"),
        ]
        for text, expected in test_cases:
            try:
                result = await engine.translate(text)
                print(f"  '{text}' -> '{result}'  ({expected})")
            except Exception as e:
                print(f"  '{text}' -> FAIL: {e}")

    await engine.close()

    print()

    # 4. redis
    print("[cache]")
    try:
        import redis.asyncio as aioredis
        r = aioredis.from_url(os.getenv("REDIS_URL", "redis://localhost:6379"))
        await r.ping()
        print("  redis: OK")
        await r.close()
    except Exception as e:
        print(f"  redis: UNAVAILABLE ({e})")
        print("  (translation caching disabled, everything else works fine)")

    print()
    print("=" * 50)
    print("healthcheck complete")


if __name__ == "__main__":
    asyncio.run(main())
