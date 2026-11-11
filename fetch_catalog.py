#!/usr/bin/env python3
"""Fetch complete, real Shopify collection JSON; abort on any incomplete collection."""
import json
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent
# Parent covers all men's blouson categories; military is fetched separately as a coverage check.
COLLECTIONS = ["men_blousonjackets", "men_blousonjackets_millitaryjackets"]
LIMIT = 250

def fetch_collection(collection):
    result = []
    seen = set()
    counts = []
    for page in range(1, 101):
        url = f"https://ragtag-global.com/collections/{collection}/products.json?limit={LIMIT}&page={page}"
        for attempt in range(3):
            try:
                req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
                with urllib.request.urlopen(req, timeout=40) as response:
                    if response.status != 200:
                        raise RuntimeError(f"HTTP {response.status}: {url}")
                    payload = json.load(response)
                if not isinstance(payload, dict) or not isinstance(payload.get("products"), list):
                    raise ValueError(f"Invalid Shopify products array: {url}")
                break
            except Exception:
                if attempt == 2:
                    raise
                time.sleep(2 ** attempt)
        batch = payload["products"]
        if len(batch) > LIMIT: raise ValueError(f"Unexpected page size: {url}")
        counts.append(len(batch))
        for product in batch:
            pid = product.get("id")
            if pid is None or pid in seen: raise ValueError(f"Duplicate/missing product ID: {url} {pid}")
            seen.add(pid)
            result.append(product)
        print(f"{collection} page={page} count={len(batch)}", flush=True)
        if len(batch) < LIMIT:
            return result, counts
    raise RuntimeError(f"Pagination safety limit reached: {collection}")

def main():
    fetched = {}
    counts = {}
    for collection in COLLECTIONS:
        fetched[collection], counts[collection] = fetch_collection(collection)
    parent_ids = {p["id"] for p in fetched[COLLECTIONS[0]]}
    military_ids = {p["id"] for p in fetched[COLLECTIONS[1]]}
    print(f"Parent: {len(parent_ids)}; military: {len(military_ids)}; military missing from parent: {len(military_ids-parent_ids)}")
    products = {}
    for collection in COLLECTIONS:
        for p in fetched[collection]:
            products[p["id"]] = p
    all_products = list(products.values())
    if not all_products: raise ValueError("Unexpected empty combined catalog")
    # Only write after EVERY collection has been retrieved and validated.
    snapshot = {"collections": COLLECTIONS, "collection_counts": {name:len(fetched[name]) for name in COLLECTIONS},
                "page_counts": counts, "complete": True, "products": all_products}
    (ROOT/"products.json").write_text(json.dumps(snapshot, ensure_ascii=False, indent=2)+"\n")
    out = ROOT/"catalog"
    out.mkdir(exist_ok=True)
    for path in out.glob("part-*.json"): path.unlink()
    parts = []
    for i, offset in enumerate(range(0, len(all_products), 5), 1):
        name = f"part-{i:03}.json"
        chunk = all_products[offset:offset+5]
        (out/name).write_text(json.dumps({"products":chunk},ensure_ascii=False,separators=(",",":"))+"\n")
        parts.append({"file":name,"count":len(chunk)})
    manifest = {"collections":COLLECTIONS,"collection_counts":snapshot["collection_counts"],
                "page_counts":counts,"total_products":len(all_products),"complete":True,"parts":parts}
    (out/"manifest.json").write_text(json.dumps(manifest,indent=2)+"\n")
    print(f"Saved {len(all_products)} unique products across {len(parts)} chunks",flush=True)

if __name__=="__main__": main()
