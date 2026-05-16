import asyncio
from app.services.bing_search import bing_search
from app.services.address_fill_agent import _extract_level4_candidates, _summarize_level_candidates


async def test():
    queries = [
        "杭州市西湖区文三路478号华星时代广场B座5层，在哪个乡镇/街道是什么",
        "华星时代广场 文三路 478号 杭州 街道",
        "文三路478号 杭州 街道",
    ]
    for q in queries:
        print(f"\n=== Query: {q} ===")
        resp = await bing_search(q, max_results=8)
        results = resp.get("results", [])
        print(f"  Results count: {len(results)}")
        if resp.get("error"):
            print(f"  Error: {resp['error']}")
        for r in results:
            title = r.get("title", "")
            content = r.get("content", "")
            print(f"  Title: {title[:80]}")
            print(f"  Content: {content[:120]}")
            # Check for level4 candidates
            text = f"{title} {content}"
            cands = _extract_level4_candidates(text)
            if cands:
                print(f"  >>> Level4 candidates found: {cands}")
            print()

    # Also test candidate summarization across all results
    print("\n=== Candidate summarization test ===")
    all_results = []
    for q in queries:
        resp = await bing_search(q, max_results=8)
        all_results.extend(resp.get("results", []))
    summary = _summarize_level_candidates(all_results)
    print(f"  Level4 candidates from all searches: {summary}")


if __name__ == "__main__":
    asyncio.run(test())
