#!/usr/bin/env python3
"""Check direct access to RAGTAG Shopify collection JSON, without HTML fallback."""
import json
import os
import sys
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

BASE = 'https://ragtag-global.com/collections/men_blousonjackets_millitaryjackets/products.json'
LIMIT = 250
MAX_PAGES = 100


def fetch(page):
    url = f'{BASE}?limit={LIMIT}&page={page}'
    for attempt in range(1, 4):
        try:
            req = Request(url, headers={'Accept': 'application/json', 'User-Agent': 'ragtag-json-connectivity-check/1.0'})
            with urlopen(req, timeout=25) as resp:
                content_type = resp.headers.get('Content-Type', '')
                raw = resp.read(20 * 1024 * 1024 + 1)
                if len(raw) > 20 * 1024 * 1024:
                    raise ValueError('Response exceeds 20 MB')
                if 'json' not in content_type.lower():
                    raise ValueError(f'Unexpected Content-Type: {content_type}')
            data = json.loads(raw)
            if not isinstance(data, dict) or not isinstance(data.get('products'), list):
                raise ValueError('JSON is missing products array')
            if any(not isinstance(p, dict) or 'id' not in p for p in data['products']):
                raise ValueError('Product missing id')
            return data['products'], url
        except (HTTPError, URLError, TimeoutError, ValueError, json.JSONDecodeError) as exc:
            print(f'Page {page}, attempt {attempt}/3 FAILED: {type(exc).__name__}: {exc}', file=sys.stderr, flush=True)
            if attempt == 3:
                raise
            time.sleep(2 ** attempt)


def main():
    counts = []
    seen = set()
    for page in range(1, MAX_PAGES + 1):
        products, url = fetch(page)
        ids = [str(p['id']) for p in products]
        if len(ids) != len(set(ids)) or seen.intersection(ids):
            raise ValueError(f'Duplicate product IDs detected on page {page}; refusing incomplete/ambiguous catalog')
        seen.update(ids)
        counts.append(len(products))
        print(f'OK page={page} products={len(products)} url={url}', flush=True)
        if len(products) < LIMIT:
            break
    else:
        raise RuntimeError(f'Reached safety cap of {MAX_PAGES} full pages; catalog completeness unverified')
    result = {'status': 'success', 'pages': len(counts), 'page_counts': counts, 'total_products': len(seen), 'complete': True}
    print('RESULT ' + json.dumps(result), flush=True)
    summary = os.environ.get('GITHUB_STEP_SUMMARY')
    if summary:
        with open(summary, 'a', encoding='utf-8') as f:
            f.write('## RAGTAG Shopify JSON connectivity test\n\n')
            f.write(f'**Success:** {len(seen)} unique products across {len(counts)} pages.\n\n')
            f.write('| Page | Products |\n|---:|---:|\n')
            for i, count in enumerate(counts, 1):
                f.write(f'| {i} | {count} |\n')
    return 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except Exception as exc:
        print(f'CONNECTIVITY TEST FAILED: {type(exc).__name__}: {exc}', file=sys.stderr)
        sys.exit(1)
