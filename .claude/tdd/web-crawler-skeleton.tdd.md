# TDD Evidence: Deterministic web crawler skeleton (F1–F7)

**Source**: Plan v2 in conversation (2026-09-15). No `.plan.md` file. eBay skipped by user decision.
**Branch**: `worktree-feat+web-crawler`. RED `31bc24d`, GREEN `97ad1bc`, refactor `423b3f3`.

## User journeys
- As a dataset builder, I run `bookworm-crawl run` a little at a time and each run continues where the last one stopped.
- As a site owner, the crawler names itself, obeys robots.txt, spaces out requests per host, and stops when I rate-limit it.
- As a YOLO trainer, every saved photo carries a hint label (`expected_content`), its license and where it came from.

## Probe before writing tests (F0)
| # | Finding |
|---|---|
| D6 | Openverse anonymous: 20 requests/min, 200/day, `page_size` max 20, 240 results per query (`page_count` 12) |
| D7 | `book cover`, `thrift books`, `isbn` hit the 240 cap; `book barcode` returns 0 |
| D10 | One Openverse call took 33s; a 30s client timeout failed |
| D11 | Blog images live on other hosts (`i0.wp.com`, `*.files.wordpress.com`, Squarespace CDN) |
| D12 | Many `<img>` are 40×40 avatars, banners or `pixel.wp.com` trackers |
| D13 | One Openverse response was not JSON |
| D14 | Openverse results carry a `mature` flag |
| D15 | WordPress `<img>` has `data-orig-file` (full-size original) |
| D16 | Blog category pages paginate (`/page/2/`); not followed yet |

**Design changes from the plan, based on the probe:**
- No host allowlist in the core. Each source decides what to enqueue; blogs block tracker and avatar hosts by suffix.
- Image size is checked on the downloaded bytes. Openverse also pre-filters on its `width`/`height` metadata.
- HTTP timeout is 90s.

## RED
`uv run pytest -q -m "not slow" --continue-on-collection-errors`
```
E   ModuleNotFoundError: No module named 'bookworm.crawler'   (x11)
70 passed, 11 deselected, 11 errors
```

## GREEN
`uv run pytest -q -m "not slow"` → **140 passed, 11 deselected** (70 new crawler tests).

## Refactor
B1: the CLI and tests never closed SQLite connections (29 `ResourceWarning: unclosed database`).
CLI now uses `contextlib.closing` and `with client`; tests close through fixtures.
`uv run pytest -q -m "not slow" -W error::ResourceWarning` → **140 passed**.

## Coverage
`uv run pytest -q -m "not slow" --cov=bookworm.crawler --cov-report=term-missing` → **99%**. Only `crawl_cli.main()` (2 lines) is uncovered.

## Real run (F8)
`BOOKWORM_CRAWLER_CONTACT=https://github.com/carlosValerio5/BookWorm uv run bookworm-crawl run openverse_photos --seed-file crawler_seeds/openverse_queries.toml --max-requests 50`
```
{"requests_handled": 9, "files_saved": 0, "stop_reason": "queue_empty"}
parse|skipped|disallowed_by_robots|9
```
**D17:** `api.openverse.org/robots.txt` has `Disallow: /v1/images/` for every agent and blocks AI crawlers (`GPTBot`, `CCBot`, `anthropic-ai`, `cohere-ai`) entirely. The crawler behaved correctly; the Openverse source collects nothing while robots.txt is obeyed. Decision pending with the user.

Blog run not done: `crawler_seeds/blog_pages.toml` is a draft waiting for approval.

## Test specification
| # | Guarantee | Test | Type | Result |
|---|---|---|---|---|
| 1 | The same URL is queued once, across runs | `test_enqueue_keeps_one_row_per_url` | unit | PASS |
| 2 | Requests come out in insertion order (deterministic) | `test_next_pending_request_follows_insertion_order` | unit | PASS |
| 3 | Queue and labels survive closing and reopening the state file | `test_queue_survives_reopening_the_state_file`, `test_request_keeps_purpose_depth_and_labels` | unit | PASS |
| 4 | `--retry-failed` puts failed requests back in the queue | `test_reset_failed_requests_makes_them_pending_again`, `test_retry_failed_downloads_what_failed_before` | unit, integration | PASS |
| 5 | Same image content is stored once | `test_record_saved_file_returns_false_for_content_already_saved`, `test_same_image_at_two_urls_is_saved_once` | unit, integration | PASS |
| 6 | Each host waits its own gap; the first request never waits | `test_request_pacing.py` (4) | unit | PASS |
| 7 | robots.txt: disallowed paths blocked; 4xx allows all; 5xx or unreachable blocks all; fetched once per host | `test_robots_policy.py` (6) | unit | PASS |
| 8 | Fetch strips charset, returns error statuses, raises `FetchError` on timeout, sends the User-Agent | `test_http_fetching.py` (4) | unit | PASS |
| 9 | Image long side is read from bytes; non-images raise `ImageDecodeError` | `test_image_size_reading.py` (3) | unit | PASS |
| 10 | HTML: absolute URLs, `data-orig-file` > widest `srcset` > `src`, no `data:`/`mailto:`, no duplicates | `test_html_extraction.py` (6) | unit | PASS |
| 11 | Openverse: stable search URL, one download per result with license labels, next page at same depth, stops at last page | `test_openverse_photos.py` | unit | PASS |
| 12 | Openverse: skips mature and known-small results, keeps unknown size, non-JSON raises `ExtractionError` | `test_openverse_photos.py` | unit | PASS |
| 13 | Blogs: images labeled with seed and page URL; tracker hosts dropped; only same-host links matching the pattern are followed | `test_blog_pages.py` (5) | unit | PASS |
| 14 | Parse → download saves the file as `<sha256>.<ext>` with labels | `test_parse_then_download_saves_the_image_with_its_labels`, `test_saved_image_is_named_by_its_content_hash` | integration | PASS |
| 15 | A second run fetches nothing already done | `test_second_run_fetches_nothing_already_done` | integration | PASS |
| 16 | Budget stops the run; 429 stops the run and keeps the request pending | `test_run_stops_when_the_request_budget_is_reached`, `test_rate_limited_response_stops_the_run_and_keeps_the_request_pending` | integration | PASS |
| 17 | Robots-disallowed URLs are never fetched | `test_request_disallowed_by_robots_is_skipped_without_fetching` | integration | PASS |
| 18 | Small images skipped; 404, wrong media type, timeout, bad page all marked failed | `test_crawl_loop.py` (5) | integration | PASS |
| 19 | Parse requests deeper than `max_depth` are never queued | `test_parse_requests_deeper_than_max_depth_are_not_queued` | integration | PASS |
| 20 | Fetch log events carry `url`, `source_name` and one `crawl_run_id` | `test_fetch_events_carry_crawl_run_id_source_and_url` | integration | PASS |
| 21 | CLI rejects unknown sources and a missing contact; `run` prints the summary; `status` prints counts | `test_crawl_cli.py` (5) | e2e (mocked HTTP) | PASS |
| 22 | Committed seed files parse, use only `cover`/`isbn`, blog patterns compile | `test_seed_files.py` (4) | unit | PASS |

## Known gaps
- B2: requests skipped by robots stay `skipped`; there is no command to re-check them.
- Blog pagination (D16) is not followed.
- No perceptual-hash dedupe; the same photo at two sizes is saved twice.
- `bookworm-crawl status` also prints JSON log lines on stderr; stdout stays clean JSON.

---

# F9–F11 + B3: Commons source, 600px blog minimum, spine label (2026-09-15)

**Checkpoints**: RED `0593dc8`, GREEN `8ffd8bf`; B3 RED `9a83042`, GREEN `44218c0`.

## Probe (F0)
| # | Finding |
|---|---|
| D20 | Commons `robots.txt` disallows `/w/` (API) and `/api/`; Robot policy says honor robots.txt |
| D28 | Category pagination links are `/w/index.php?...`, disallowed; only the first 200 files per category |
| D29 | Each file is linked twice on a category page (399 links, 200 unique) |
| D30 | Extensions mix case (`.JPG`) and include `.ogg` |
| D31 | File pages list standard thumbnails (`.mw-thumbnail-link`: 330, 1280, 3840) |

**Design:** category page → photo file pages only (`.jpg/.jpeg/.png/.webp`) → largest standard thumbnail ≥ 640px, else original; query string removed; `license` label from `.licensetpl_short`. No pagination, no subcategories.

## RED / GREEN
- RED: `4 failed, 139 passed, 1 error` (`ModuleNotFoundError: bookworm.crawler.sources.commons_categories`, `640 == 600`, `'cover' == 'spine'`, `commons_categories` not registered).
- GREEN: `uv run pytest -q -m "not slow" -W error::ResourceWarning --cov=bookworm.crawler` → **153 passed**, 99%, `commons_categories.py` 100%.

## B3: downloads waited behind pages
First real Commons run: `50 handled, 0 saved`. The queue was strictly FIFO, so 46 downloads sat behind 221 file pages.
Fix: `find_next_pending_request` orders by `purpose = 'download' DESC, queue_position` (still deterministic).
- RED: `AssertionError: 'https://blog.example/page-2' == 'https://img.example/photo.jpg'`.
- GREEN: **154 passed**.

## Real runs
| Run | Result |
|---|---|
| `blog_pages`, 50 requests (before F10) | 19 saved (6.2 MB), 21 skipped too small (six at 600px) |
| `commons_categories`, 50 requests (before B3) | 0 saved |
| `commons_categories`, 50 requests (after B3) | **32 saved** (22 `isbn`, 10 `cover`, 29 MB), 16 skipped < 640px, 219 file pages pending |

Photos checked by eye:
- `ISBN`: real photos of barcodes and ISBN text on book backs; one diagram slipped in (`ISBN_Details-ar.png`). **D33**
- `Book sales`: wide scenes (a 1974 crowd, a warehouse of book stacks), not covers. **D34**

## Test specification (new)
| # | Guarantee | Test | Type | Result |
|---|---|---|---|---|
| 23 | Category URL uses underscores | `test_category_url_uses_underscores` | unit | PASS |
| 24 | Seeds parse each category with its hint label | `test_seed_requests_parse_each_category_page` | unit | PASS |
| 25 | Category page queues each photo file page once; no pagination, subcategories or footer links | `test_category_page_queues_each_photo_file_page_once` | unit | PASS |
| 26 | Non-photo files (svg, ogg, pdf) are not queued | `test_category_page_skips_files_that_are_not_photos` | unit | PASS |
| 27 | Largest thumbnail ≥ 640px, query removed, license stripped | `test_file_page_downloads_the_largest_thumbnail_with_its_license` | unit | PASS |
| 28 | Original is used when thumbnails are too small | `test_file_page_downloads_the_original_when_thumbnails_are_too_small` | unit | PASS |
| 29 | Missing license → empty label; missing original → `ExtractionError`; unknown page → `ExtractionError` | `test_commons_categories.py` (4) | unit | PASS |
| 30 | Blog minimum is 600px | `test_blog_source_keeps_images_from_600px` | unit | PASS |
| 31 | Blog images with "spine" in the URL get `expected_content = spine` | `test_extract_labels_images_named_spine_as_spine` | unit | PASS |
| 32 | Committed seeds use only `cover`/`isbn`/`spine`; every source has a seed file | `test_seed_files.py` | unit | PASS |
| 33 | Pending downloads are taken before pages queued earlier | `test_downloads_are_taken_before_pages_queued_earlier` | unit | PASS |

## Known gaps (new)
- 3840px thumbnails are ~1 MB each; kept on purpose (T8: barcodes stop decoding at 1280px).
- Photos saved before F11 keep their old labels.

## User decisions (2026-09-15)
- D33 resolved: Commons skips `.png` files. RED `1a22935` (`ISBN_Details-ar.png` still queued), GREEN: **154 passed**.
- D34 resolved: `Book sales` removed from `crawler_seeds/commons_categories.toml`.
- Local queue: 6 pending requests marked `skipped` (1 `dropped_by_user:book_sales`, 5 `png_not_collected`).
- Already saved and not deleted: 10 `Book sales` photos, 4 ISBN `.png` files.
