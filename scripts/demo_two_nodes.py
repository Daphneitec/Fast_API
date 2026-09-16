"""Hit two local Abacus nodes and prove they share one consistent sum.

Usage (after both nodes are listening):
    py -3.12 scripts/demo_two_nodes.py
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from itertools import cycle

import httpx


async def wait_healthy(client: httpx.AsyncClient, urls: list[str]) -> None:
    for url in urls:
        for _ in range(50):
            try:
                response = await client.get(f"{url}/health")
                response.raise_for_status()
                body = response.json()
                print(f"healthy {url} node={body['node']} store={body['store']}")
                break
            except Exception:
                await asyncio.sleep(0.2)
        else:
            raise SystemExit(f"Node never became healthy: {url}")


async def run(urls: list[str], posts_per_node: int, value: int) -> None:
    timeout = httpx.Timeout(10.0)
    async with httpx.AsyncClient(timeout=timeout) as client:
        await wait_healthy(client, urls)

        reset = await client.delete(f"{urls[0]}/abacus/sum")
        reset.raise_for_status()
        print(f"reset via {urls[0]} -> {reset.json()}")

        tasks: list[asyncio.Task] = []
        node_cycle = cycle(urls)
        total_adds = posts_per_node * len(urls)
        for _ in range(total_adds):
            url = next(node_cycle)
            tasks.append(
                asyncio.create_task(
                    client.post(f"{url}/abacus/number", json={"number": value})
                )
            )

        results = await asyncio.gather(*tasks, return_exceptions=True)
        failures = [r for r in results if isinstance(r, Exception) or r.status_code != 200]
        if failures:
            raise SystemExit(f"{len(failures)} POST(s) failed: {failures[:3]}")

        expected = total_adds * value
        sums = []
        for url in urls:
            response = await client.get(f"{url}/abacus/sum")
            response.raise_for_status()
            sums.append(response.json()["sum"])
            print(f"GET {url}/abacus/sum -> {response.json()}")

        if any(s != expected for s in sums):
            raise SystemExit(f"INCONSISTENT: expected {expected}, got {sums}")

        print(
            f"OK: {total_adds} POSTs of {value} across {len(urls)} nodes; "
            f"every GET returned {expected}"
        )


def main() -> None:
    parser = argparse.ArgumentParser(description="Two-node Abacus consistency demo")
    parser.add_argument(
        "--urls",
        nargs="+",
        default=["http://127.0.0.1:8001", "http://127.0.0.1:8002"],
    )
    parser.add_argument("--posts-per-node", type=int, default=250)
    parser.add_argument("--value", type=int, default=1)
    args = parser.parse_args()
    asyncio.run(run(args.urls, args.posts_per_node, args.value))


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(130)
