"""Benchmark gateway and translation performance."""

import asyncio
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from gateway import DouyinClient, DeviceAuth, FeedService
from translate import TranslationEngine


async def benchmark_gateway(n_requests: int = 10):
    """Benchmark gateway request latency."""
    auth = DeviceAuth()
    async with DouyinClient(auth=auth) as client:
        feed_svc = FeedService(client)

        times = []
        for i in range(n_requests):
            start = time.perf_counter()
            try:
                data = await feed_svc.trending(count=5, cursor=i * 5)
                elapsed = time.perf_counter() - start
                count = len(data.get("aweme_list", []))
                times.append(elapsed)
                print(f"  request {i+1}/{n_requests}: {elapsed:.3f}s ({count} videos)")
            except Exception as e:
                elapsed = time.perf_counter() - start
                print(f"  request {i+1}/{n_requests}: FAILED {elapsed:.3f}s ({e})")

        if times:
            avg = sum(times) / len(times)
            p50 = sorted(times)[len(times) // 2]
            p95 = sorted(times)[int(len(times) * 0.95)]
            print(f"\n  avg: {avg:.3f}s  p50: {p50:.3f}s  p95: {p95:.3f}s")


async def benchmark_translation(n_texts: int = 20):
    """Benchmark translation throughput."""
    engine = TranslationEngine()

    test_texts = [
        "这个视频太好看了",
        "今天天气真好适合出去玩",
        "绝绝子这也太好吃了吧",
        "家人们谁懂啊",
        "破防了",
        "这是什么神仙操作",
        "笑死我了哈哈哈",
        "太离谱了吧这个",
        "内卷到底什么时候是个头",
        "摆烂也是一种生活态度",
    ] * (n_texts // 10 + 1)
    test_texts = test_texts[:n_texts]

    # sequential
    print("  sequential:")
    start = time.perf_counter()
    for text in test_texts:
        await engine.translate(text)
    seq_time = time.perf_counter() - start
    print(f"    {n_texts} translations in {seq_time:.2f}s ({n_texts/seq_time:.1f}/s)")

    # batch (concurrent)
    print("  batch (concurrent):")
    start = time.perf_counter()
    await engine.translate_batch(test_texts)
    batch_time = time.perf_counter() - start
    print(f"    {n_texts} translations in {batch_time:.2f}s ({n_texts/batch_time:.1f}/s)")

    await engine.close()


async def main():
    print("dou benchmark")
    print("=" * 50)

    print("\n[gateway latency]")
    await benchmark_gateway(10)

    print("\n[translation throughput]")
    await benchmark_translation(20)

    print("\n" + "=" * 50)


if __name__ == "__main__":
    asyncio.run(main())
