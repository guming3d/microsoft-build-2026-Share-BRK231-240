"""
Q2 - Pagination & result coverage.

Answers (via live calls):
  A. subset/prefix   - is the top-10 a strict prefix (and subset) of the top-50?
                       If yes, maxResults just truncates one fixed ranking.
  B. pagination      - probe offset/skip/page/from/cursor/start body params to see
                       if ANY of them returns a different "page 2" of results.
                       The typed client has no such params, so we raw-probe via _post.

Usage:
  python test_q2_pagination.py
  python test_q2_pagination.py --query "azure openai"
"""
from __future__ import annotations
import argparse
from webiq_client import client_from_env


def web_urls(data: dict) -> list[str]:
    return [i.get("url", "") for i in data.get("webResults", [])]


def news_urls(data: dict) -> list[str]:
    return [i.get("url", "") for i in data.get("newsResults", [])]


# --------------------------------------------------------------------------- #
def test_subset(client, query: str) -> None:
    print("\n" + "=" * 70)
    print(f"A. IS top-N A PREFIX/SUBSET OF top-MAX?  -  query='{query}'")
    print("=" * 70)

    # web: 10 vs 50
    r10 = web_urls(client.web(query, max_results=10).data)
    r50 = web_urls(client.web(query, max_results=50).data)
    prefix = r10 == r50[:len(r10)]
    subset = set(r10) <= set(r50)
    print(f"  web:  top-10 = {len(r10)} urls,  top-50 = {len(r50)} urls")
    print(f"        top-10 == top-50[:10]  (strict prefix, same order)? {prefix}")
    print(f"        set(top-10) subset-of set(top-50)?                  {subset}")
    if not prefix and subset:
        # show where order diverges
        for idx, (a, b) in enumerate(zip(r10, r50)):
            if a != b:
                print(f"        first order divergence at rank {idx}: 10->{a}  50->{b}")
                break

    # news: 10 vs 20
    n10 = news_urls(client.news(query, max_results=10).data)
    n20 = news_urls(client.news(query, max_results=20).data)
    nprefix = n10 == n20[:len(n10)]
    nsubset = set(n10) <= set(n20)
    print(f"  news: top-10 = {len(n10)} urls,  top-20 = {len(n20)} urls")
    print(f"        top-10 == top-20[:10]  (strict prefix, same order)? {nprefix}")
    print(f"        set(top-10) subset-of set(top-20)?                  {nsubset}")

    print("\n  --- verdict ---")
    if prefix and nprefix:
        print("  maxResults TRUNCATES one stable ranking (top-N is a prefix of top-MAX).")
    elif subset and nsubset:
        print("  top-N is a SUBSET of top-MAX but order/ranking shifts between sizes.")
    else:
        print("  top-N is NOT contained in top-MAX -> ranking changes with maxResults.")


# --------------------------------------------------------------------------- #
def test_pagination(client, query: str) -> None:
    print("\n" + "=" * 70)
    print(f"B. PAGINATION PARAM PROBE (raw _post)  -  query='{query}'")
    print("=" * 70)

    page1 = set(web_urls(client.web(query, max_results=10).data))
    print(f"  page-1 baseline: {len(page1)} urls (maxResults=10, no offset)\n")

    # param -> value meaning "give me the second page of 10"
    candidates = [
        ("offset", 10), ("skip", 10), ("page", 2), ("from", 10),
        ("cursor", 10), ("start", 10), ("pageNumber", 2), ("count", 10),
    ]
    any_paging = False
    for param, val in candidates:
        body = {"query": query, "maxResults": 10, param: val}
        try:
            r = client._post("/search/web", body)
            cur = set(web_urls(r.data))
            new = len(cur - page1)
            if cur and cur.isdisjoint(page1):
                verdict = "NEW PAGE (disjoint from page-1!)"
                any_paging = True
            elif new > 0:
                verdict = f"partial shift (+{new} new urls)"
                any_paging = True
            else:
                verdict = "ignored (same as page-1)"
            print(f"  +{param:<11}={val:<3} -> HTTP 200  {len(cur)} urls  {verdict}")
        except Exception as exc:  # noqa: BLE001
            status = getattr(exc, "status", "?")
            print(f"  +{param:<11}={val:<3} -> rejected (HTTP {status})")

    print("\n  --- verdict ---")
    if any_paging:
        print("  At least one param shifted results -> SOME pagination/offset exists.")
    else:
        print("  No param produced a new page -> NO pagination; maxResults is a hard ceiling.")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--query", default="Microsoft Build 2026")
    args = ap.parse_args()
    client = client_from_env()
    test_subset(client, args.query)
    test_pagination(client, args.query)
    print("\n" + "=" * 70)


if __name__ == "__main__":
    main()
