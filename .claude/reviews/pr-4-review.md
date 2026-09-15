# PR Review: #4 — feat: add deterministic web crawler for YOLO training photos

**Reviewed**: 2026-09-15
**Author**: carlosValerio5
**Branch**: worktree-feat+web-crawler → main (head `a920662`)
**Decision**: REQUEST CHANGES (posted as a comment: GitHub does not allow requesting changes on your own PR)

## Summary
Clean, well-tested crawler (180 tests pass, 99% crawler coverage). One verified bug makes a source stop collecting forever after a single persistent 403, and redirects skip the robots.txt check. Fix H1 before merge; M1–M3 are recommended.

## Findings

### CRITICAL
None. No secrets, all SQL is parameterized, and saved file names come from sha256 (no path traversal).

### HIGH

**H1. One persistent 401/403 blocks a source on every future run** — `src/bookworm/crawler/crawl_loop.py:30`, `:127`
- 401 and 403 are treated like rate limits: the run stops and the request stays `pending`.
- Since B3, pending downloads are taken first (`crawl_state.py:81`), so the same request is picked first on every run.
- A photo behind hotlink protection or a deleted file returns 403 forever, so that source never collects again.
- **Verified** with a mock run: 3 runs in a row, each `requests_handled=0, stop_reason=rate_limited`; the good image queued behind it was never fetched.
- **Fix:** stop the run only on 429. Mark 401/403 as `failed` (`http_403`) and continue. Add a loop test: a 403 image fails and the next image is still saved.

### MEDIUM

**M1. Redirects skip the robots.txt check of the target host** — `src/bookworm/crawler/http_fetching.py:20`
- `follow_redirects=True`, and robots.txt is only checked for the original URL.
- **Verified:** a 302 to a host with `Disallow: /` was fetched and the photo saved.
- The saved `source_url` is also the URL before the redirect, so provenance is wrong.
- **Fix:** set `follow_redirects=False` and enqueue the `Location` URL as a new request (the loop then checks its robots.txt), or check the final URL against robots.txt before accepting the body.

**M2. No size limit on responses** — `src/bookworm/crawler/http_fetching.py:28`, `:35`; `src/bookworm/crawler/image_size_reading.py:10`
- The whole body is loaded into memory, and every image is fully decoded to read its size.
- A very large file or a decompression bomb from a blog page can exhaust memory.
- **Fix:** stream the response and stop after a byte limit (e.g. 30 MB, checking `Content-Length` first); read image dimensions from the header before decoding.

**M3. Image URLs from third-party pages can point at private addresses** — `src/bookworm/crawler/sources/blog_pages.py:40`
- Blog `<img>` URLs are accepted from any host. A page with `http://127.0.0.1/…`, `http://192.168.1.1/…` or `http://169.254.169.254/…` gets fetched (their robots.txt is missing, so everything is allowed) and saved if it's an image.
- **Fix:** before fetching, resolve the host and skip loopback, private and link-local addresses.

### LOW

- **L1.** `src/bookworm/crawler/crawl_state.py:81` — no index on `(source_name, status, purpose, queue_position)`; every request scans the whole queue as it grows.
- **L2.** `src/bookworm/crawler/crawl_state.py:18` — `url` is unique across all sources; a URL queued by one source is silently ignored for another.
- **L3.** `src/bookworm/crawler/sources/blog_pages.py:14`, `:55` — the spine rule matches the whole URL, so a host or folder like `spinelli-books.com` gives a false `spine` hint. Match the file name only.
- **L4.** `src/bookworm/crawler/html_extraction.py:31` — `srcset` is split on commas, which breaks URLs that contain commas (e.g. `w_300,h_200`).
- **L5.** `src/bookworm/crawler/crawl_cli.py:74` — `bookworm-crawl status` with a wrong `--state-db` creates an empty database instead of failing.
- **L6.** `src/bookworm/crawler/robots_policy.py:44` — robots.txt fetches aren't paced, so they go out back-to-back with the first request to a host.
- **L7.** Tests: `crawl_cli.main()` is not covered, and there are no tests for H1 or M1.

## Validation Results

| Check | Result |
|---|---|
| Type check | Skipped (no type checker in dev dependencies) |
| Lint | Skipped (no linter configured) |
| Tests | Pass — `uv run pytest -q -m "not slow" -W error::ResourceWarning`: 180 passed, 11 deselected (slow YOLO/EasyOCR tests, not touched by this PR) |
| Build | Pass — `uv run` rebuilt the `bookworm` package |
| H1 / M1 repro | Fail as described — mock runs in a scratch script |

## Files Reviewed

| Area | Files | Change |
|---|---|---|
| Source | `src/bookworm/crawler/{__init__,crawl_cli,crawl_loop,crawl_state,crawl_types,file_saving,html_extraction,http_fetching,image_size_reading,request_pacing,robots_policy}.py` | Added |
| Source | `src/bookworm/crawler/sources/{__init__,blog_pages,commons_categories,openverse_photos}.py` | Added |
| Tests | `tests/crawler_factories.py`, `tests/test_{blog_pages,commons_categories,crawl_cli,crawl_loop,crawl_state,html_extraction,http_fetching,image_size_reading,openverse_photos,request_pacing,robots_policy,seed_files}.py` | Added |
| Seeds | `crawler_seeds/{blog_pages,commons_categories,openverse_queries}.toml` | Added |
| Config | `pyproject.toml`, `uv.lock` | Modified |
| Docs | `CHANGELOG.md`, `CLAUDE.md` | Modified |
| Docs | `.claude/tdd/web-crawler-skeleton.tdd.md` | Added |

## Follow-up (2026-09-15)

| Finding | Status | Evidence |
|---|---|---|
| H1 | Fixed | RED `ac6d8a9`, GREEN `7af64dc`; `test_forbidden_download_is_failed_and_the_run_continues` |
| M1 | Fixed | RED `ac6d8a9`, GREEN `7af64dc`; redirect tests in `test_crawl_loop.py`, `test_http_fetching.py`, `test_robots_policy.py` |
| M2 | Fixed | RED `ac6d8a9`, GREEN `7af64dc`; 30 MB body limit, header-only image size, 16384px cap |
| M3 | Fixed | RED `727719d`, GREEN `74af5d4`; `test_address_policy.py`, private and unresolvable host tests |
| L1–L7 | Open | Not in scope of this fix |

After the fixes: `uv run pytest -q -m "not slow" -W error::ResourceWarning` → 198 passed, crawler coverage 99%. A real `blog_pages` run of 10 requests saved 9 photos.
