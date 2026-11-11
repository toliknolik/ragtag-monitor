# RAGTAG JSON connectivity test

This is **only a connectivity test**, not yet a product monitor. It directly fetches Shopify JSON from RAGTAG's `men_blousonjackets_millitaryjackets` collection, paginates until the first page with fewer than 250 products, and checks the `products` arrays. It does **not** scrape HTML, invent listings, save snapshots, or send notifications.

## Run without a terminal

1. Create a GitHub repository (private is fine).
2. Download and unzip the package. In your GitHub repository, select **Add file → Upload files** and upload `check.py` and `README.md`.
3. GitHub's browser upload interface may not preserve hidden folders reliably. To add the workflow, open your repository and choose **Add file → Create new file**. Enter this exact filename: `.github/workflows/connectivity.yml`. Copy the contents of the included `.github/workflows/connectivity.yml` into the editor and commit it. (If your upload preserved that workflow path already, skip this step.)
4. Open **Actions → RAGTAG JSON connectivity test → Run workflow**. If prompted, enable Actions for the repository.
5. Open the run and inspect **Fetch and validate paginated Shopify JSON** and the run summary.

Success means GitHub Actions retrieved and validated the full paginated collection at the time of the run. Failure means **the catalog has not been checked**, not that there are no new products. Share the logs or a screenshot of the run so the next phase can be implemented only after confirmed success.

## Expected output

```text
OK page=1 products=171 url=https://...page=1
RESULT {"status": "success", "pages": 1, "page_counts": [171], "total_products": 171, "complete": true}
```

The numbers above are illustrative, **not a live result**.

## Safety

- Manual trigger only. No scheduled jobs, secrets, writes, or notifications.
- Retries network errors; rejects non-JSON responses and missing `products` arrays.
- Aborts on duplicate product IDs, failed pages, or an excessive number of pages.
- Never falls back to HTML or search results.
