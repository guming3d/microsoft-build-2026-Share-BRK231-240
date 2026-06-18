"""
Verify result consistency: do multiple calls to the same endpoint return
similar results, or do they vary significantly?

Tests both news (Beta) and web (GA) to compare stability.
"""

from __future__ import annotations
import time
from collections import Counter
from webiq_client import client_from_env

def extract_urls(response_data: dict, endpoint: str) -> set[str]:
    """Extract result URLs from a response."""
    if endpoint == "news":
        return {item["url"] for item in response_data.get("newsResults", [])}
    elif endpoint == "web":
        return {item["url"] for item in response_data.get("webResults", [])}
    return set()

def calculate_overlap(set1: set, set2: set) -> tuple[int, int, float]:
    """Return (common, total_unique, jaccard_similarity)."""
    common = len(set1 & set2)
    total = len(set1 | set2)
    jaccard = common / total if total > 0 else 0.0
    return common, total, jaccard

def main():
    client = client_from_env()
    query = "Microsoft Build 2026"
    iterations = 5
    delay = 1.0  # seconds between calls

    for endpoint in ["news", "web"]:
        print(f"\n{'='*70}")
        print(f"Testing {endpoint.upper()} endpoint consistency")
        print(f"Query: '{query}'  |  Iterations: {iterations}  |  Delay: {delay}s")
        print('='*70)

        all_results = []
        all_urls = []

        for i in range(iterations):
            if endpoint == "news":
                resp = client.news(query, max_results=20)
            else:
                resp = client.web(query, max_results=10)
            
            urls = extract_urls(resp.data, endpoint)
            all_results.append(resp)
            all_urls.append(urls)
            
            print(f"  Call {i+1}: {len(urls)} results  |  {resp.elapsed_ms:.1f} ms")
            
            if i < iterations - 1:
                time.sleep(delay)

        # Analyze consistency
        print(f"\n--- Consistency analysis ---")
        
        # Count how many times each URL appeared
        all_urls_flat = [url for urls in all_urls for url in urls]
        url_counts = Counter(all_urls_flat)
        
        stable = sum(1 for count in url_counts.values() if count == iterations)
        occasional = sum(1 for count in url_counts.values() if 1 < count < iterations)
        unique_once = sum(1 for count in url_counts.values() if count == 1)
        
        print(f"  Unique URLs seen across {iterations} calls: {len(url_counts)}")
        print(f"    - Appeared in ALL {iterations} calls:  {stable}  (stable results)")
        print(f"    - Appeared in 2-{iterations-1} calls: {occasional}  (occasional)")
        print(f"    - Appeared only once:    {unique_once}  (one-off)")
        
        # Pairwise overlaps
        print(f"\n  Pairwise overlaps (Jaccard similarity):")
        overlaps = []
        for i in range(len(all_urls) - 1):
            common, total, jaccard = calculate_overlap(all_urls[i], all_urls[i+1])
            overlaps.append(jaccard)
            print(f"    Call {i+1} vs Call {i+2}: {common}/{total} common  "
                  f"(Jaccard: {jaccard:.2%})")
        
        avg_jaccard = sum(overlaps) / len(overlaps) if overlaps else 0
        print(f"\n  Average consecutive overlap: {avg_jaccard:.1%}")
        
        if avg_jaccard > 0.8:
            verdict = "VERY STABLE (>80% overlap)"
        elif avg_jaccard > 0.5:
            verdict = "MODERATELY STABLE (50-80%)"
        else:
            verdict = "VARIABLE (<50% overlap)"
        
        print(f"  Verdict: {verdict}")

    print("\n" + "="*70)

if __name__ == "__main__":
    main()
