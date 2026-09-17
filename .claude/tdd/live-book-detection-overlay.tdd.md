# TDD Evidence: Live book-detection overlay on mobile

**Source**: conversational plan from `/ecc:plan` (no `.plan.md` artifact — free-form request: "add live inference into the mobile version of the app, efficiently, using the latest fine-tuned weights"). Architecture confirmed with the user: server-streamed (no on-device inference, no extra infra), since `bookworm-mobile` uses `expo-camera` with no frame-processor hook and there's no budget for new hosting. Open question on `/api/scan`'s response shape resolved as **option (a)**: return the honest partial result, no fabricated title/author/coverImage.
**Branch**: `main`. Checkpoints (in order): `f0f823f0` (RED, mobile module), `c40d3492` (GREEN, mobile module), `9f7965f8` (RED, CLI), `af0a71ef` (GREEN, CLI), `5c92951c` (refactor, remove orphaned stub), `558340df` (RED→GREEN, base64-frame contract fix), `1ecf813a` (mobile TS feature, no automated tests — see below), `6d9aa0d4` (GREEN, coverage close-out).

## User journeys
- As a thrifter, I aim my phone at a book and see a live box appear over it before I tap anything, so I know the app is actually seeing the cover.
- As a thrifter, when I tap to scan, I get what the app actually read (ISBN, or OCR snippets if the ISBN wasn't legible) — not a fake, always-the-same result.
- As a developer, live detection doesn't run OCR/barcode work per frame, and a single bad frame never hangs the connection.

## Discoveries made before writing tests
- **D1**: `/api/scan` (`bookworm.annotator.server`, pre-existing) always returned a hardcoded "Drácula" — `bookworm-mobile/PRODUCT.md` already named this as a known gap.
- **D2**: `expo-camera`'s `CameraView` has no raw frame-processor hook without ejecting Expo's managed workflow. "Live" here is periodic low-res still-capture polling (~500ms), not per-video-frame analysis.
- **D3**: the old mobile server was never imported by `cli.py` and had zero tests — orphaned.
- **D4**: `uvicorn` was pinned without `websockets`/`wsproto`; a FastAPI `WebSocket` route wouldn't have served without adding one.
- **Mid-build**: React Native's `WebSocket` would need a hand-rolled, untested base64→bytes decoder to send raw binary frames. Switched the wire contract to base64 **text** frames instead — simpler and avoids exactly the kind of unverified code this project's traceback culture exists to avoid.
- **Mid-build bug caught by the RED cycle itself**: the first live-detect implementation could hang forever if the background frame-receiver task hit any exception other than `WebSocketDisconnect` (proven by an actual test hang, not by inspection). Fixed by making the receiver loop always signal session-end via `finally`.
- **Repo hygiene, flagged but not fixed here**: `bookworm-mobile/node_modules/` (25,877 files) is fully tracked in git; `bookworm-mobile/.gitignore` never excludes it. Left untouched — out of scope and too large a blast radius for this feature.

## Task report

### 1–2. Real `/api/scan` pipeline + relocate to `bookworm.mobile.server` + `bookworm serve` CLI command
- RED: `uv run pytest tests/test_mobile_server.py -v` → `ModuleNotFoundError: No module named 'bookworm.mobile'` (compile-time RED, intended missing implementation).
- GREEN: `uv run pytest tests/test_mobile_server.py -v` → 5 passed.
- RED (CLI): `uv run pytest tests/test_cli.py -k serve -v` → `No such command 'serve'` / `AttributeError: ... has no attribute 'create_mobile_app'`.
- GREEN (CLI): `uv run pytest tests/test_cli.py -v` → 15 passed (all commands, no regressions).
- Refactor: removed the now-fully-orphaned `bookworm/annotator/server.py`; `uv run pytest -q -m "not slow"` → 323 passed after removal.
- **Guaranteed**: `/api/scan` returns the real `ScanResult` (isbn/kind/OCR text/boxes), saves the photo, rejects a malformed payload with 400; `bookworm serve` binds to `0.0.0.0` (unlike `annotator`/`dashboard`'s `127.0.0.1`, since the phone reaches it over LAN) with a documented default port and photos dir.

### 3–4. `websockets` dependency + `WS /api/live-detect`
- Added via `uv add websockets` (uvicorn needs `websockets` or `wsproto` to serve a `WebSocket` route; neither was present in `uv.lock`).
- RED: initial design sent raw bytes (`websocket.send_bytes`); switching the test to `send_text` with base64 caused the test to **hang** (not fail cleanly) — the receiver task called `receive_bytes()` on a text frame, raised an exception `receive_frames_into_buffer` didn't catch, died silently, and the main loop waited forever. Killed the run (exit 144) and fixed the receiver loop to always call `buffer.mark_disconnected()` in a `finally`, regardless of how it exits.
- GREEN: `uv run pytest tests/test_mobile_server.py -v` → 6 passed, then a 7th test closing the last coverage gap (a frame that's valid base64 but not a decodable JPEG) → 100% line coverage on `bookworm/mobile/server.py`.
- **Guaranteed**: live-detect decodes base64-text frames, shrinks to 640px long side, runs `detect_books` only (reuses `load_book_detector()`'s cache — verified no second model load path exists), returns boxes as JSON; a malformed or undecodable frame is skipped, not fatal; disconnect ends the session cleanly; one summary log line per session (frame count, duration, avg latency), not one per frame.

### 5. Mobile TS: live overlay + honest results
- **No automated tests** — `bookworm-mobile` has no JS/TS test runner configured (no `test` script; the only JS test precedent, `tests/js/box_geometry.test.js`, is CommonJS `node:test` against a plain browser script for the *annotator*, not this TypeScript/ESM Expo app). Adding a real runner (Jest/Vitest + RN Testing Library) for two pure functions was judged out of scope per this project's "avoid overengineering" guidance and stated explicitly to the user before writing the code, rather than silently skipping or faking coverage.
- Verification performed instead:
  - `npx tsc --noEmit -p tsconfig.json`: zero errors in any file this change touched (`use-live-detection.ts`, `live-detection-geometry.ts`, `api.ts`, `BookContext.tsx`, `index.tsx`, `biblioteca.tsx`). All remaining `tsc` errors are pre-existing, in files never touched by this change (confirmed by re-running after a full `npm install` fixed an unrelated broken-`node_modules` state).
  - `npm run lint`: fails in this environment on a pre-existing broken Expo CLI install (`Cannot find module '.../@expo/cli/build/bin/cli'`), reproduced identically *before* this session touched anything — not a regression.
  - Manual on-device verification (phone + `uv run bookworm serve`) was **not performed in this session** — flagged here explicitly rather than claimed.
- **What the code does, for the record**: `shouldCaptureFrame`/`scaleBoxToPreview` are pure, typed, side-effect-free functions; `useLiveDetection` sends a downscaled base64 JPEG over the live-detect socket every ~500ms (throttled, one in flight at a time) and exposes the latest box; `index.tsx` renders a gold overlay box while framing a book and shows the honest scan result (ISBN or OCR snippets, no fabricated title/author/cover) on tap-to-scan; `biblioteca.tsx` degrades gracefully for saved books with no title/author.

## Test specification

| # | What is guaranteed | Test file | Type | Result |
|---|---|---|---|---|
| 1 | `/api/scan` returns the real pipeline result, not a stub, with no fabricated fields | `tests/test_mobile_server.py::test_scan_endpoint_returns_real_pipeline_result_not_a_stub` | integration | PASS |
| 2 | A malformed photo payload gets HTTP 400 | `tests/test_mobile_server.py::test_scan_endpoint_rejects_a_malformed_photo` | integration | PASS |
| 3 | The submitted photo is saved to the photos dir | `tests/test_mobile_server.py::test_scan_endpoint_saves_the_photo_to_the_photos_dir` | integration | PASS |
| 4 | Live-detect returns boxes for a single base64 frame | `tests/test_mobile_server.py::test_live_detect_returns_boxes_for_a_single_base64_frame` | integration | PASS |
| 5 | Disconnecting ends the session cleanly (no hang) | `tests/test_mobile_server.py::test_live_detect_disconnect_ends_the_session_cleanly` | integration | PASS |
| 6 | A malformed (non-base64) frame is skipped, not fatal | `tests/test_mobile_server.py::test_live_detect_skips_a_malformed_frame_without_hanging` | integration | PASS |
| 7 | A frame that's valid base64 but not a real image is skipped | `tests/test_mobile_server.py::test_live_detect_skips_a_frame_that_is_not_a_real_image` | integration | PASS |
| 8 | `bookworm serve` binds to all interfaces (not localhost-only, unlike other commands) | `tests/test_cli.py::test_serve_binds_to_all_interfaces` | integration | PASS |
| 9 | `bookworm serve` uses documented defaults | `tests/test_cli.py::test_serve_uses_default_photos_dir_and_port` | integration | PASS |

Command: `uv run pytest tests/test_mobile_server.py tests/test_cli.py -v` → all passed. Full suite: `uv run pytest -q -m "not slow"` → 323 passed. `tests/test_real_photos.py` has one pre-existing, unrelated failure per real photo (fine-tuned model doesn't detect a book in that specific sample) — confirmed via `git log -- tests/test_real_photos.py` that this file predates this session and nothing in this change touches detection weights, `book_detection.py`, or `image_loading.py`.

## Coverage and known gaps
- `uv run pytest tests/test_mobile_server.py tests/test_cli.py --cov=bookworm.mobile --cov=bookworm.cli`: **`bookworm/mobile/server.py` 100%**, `bookworm/cli.py` 95% (misses are pre-existing `main()`/annotator-argument-validation lines unrelated to this change).
- **Known, stated gap**: no automated coverage for the mobile TypeScript/React Native code (hook, geometry functions, UI wiring) — see Task 5 above for why, and what was done instead. Recommend a follow-up decision (not made here) on whether `bookworm-mobile` should get a real test runner going forward.
- **Known, stated gap**: no on-device manual verification was performed this session. Before calling the feature "done" in a user-facing sense, run `uv run bookworm serve` and `expo start` on a phone and confirm the overlay tracks a real book and that tap-to-scan shows honest results.

## Follow-up fix: `CameraNotReadyException` + live detection never finding a book

Reported by the user after connecting a real phone (first on-device test of this feature). Both symptoms traced to one root cause.

- **RED (code-level, no runtime test available — see the stated gap above)**: neither `takePictureAsync` call site (`escanearLibroReal`'s tap-to-scan, and `useLiveDetection`'s polling loop) waited for `expo-camera`'s `onCameraReady` callback. `cameraRef.current` becomes truthy as soon as `CameraView` mounts, well before the native camera hardware finishes initializing — confirmed against the installed `expo-camera` types (`node_modules/expo-camera/build/CameraView.d.ts`), whose own docstring reads: *"Make sure to wait for the `onCameraReady` callback before calling this method."* `useLiveDetection`'s interval started polling the instant `isCameraActive` flipped true, meaning every frame-capture attempt in that window failed (caught, logged, dropped) — so the backend never received a single frame, which is the full explanation for "failing to detect the book" as the same bug, not a second one.
- **Fix**: added `isCameraReady` state, set only by `CameraView`'s `onCameraReady` prop, reset to `false` each time the camera is (re)opened in `encenderCamara`. `useLiveDetection`'s `isActive` argument is now `isCameraActive && isCameraReady`, so its polling `useEffect` never starts until the camera actually signals readiness. `escanearLibroReal` early-returns if `!isCameraReady`.
- **GREEN evidence**: `npx tsc --noEmit -p tsconfig.json` on the changed file shows zero new errors (only the same two pre-existing `absoluteFillObject` type mismatches present before this change). `onCameraReady`'s signature (`() => void`) confirmed against the installed package's `.d.ts`.
- **Not yet confirmed**: on-device retest. Ask the user to reproduce on the phone again; if the box still doesn't appear, the next diagnostic step is the Metro console output from their own terminal (I have no access to logs from a `npx expo start` they run outside this session — they'd need to paste the relevant lines).

## Follow-up fix 2: exception still visible in the UI + identified cover lost on save

Reported by the user after retesting the fix above on a real device: it now works, but (a) the exception still shows in the UI, and (b) a correctly-identified cover shows as "Portada sin identificar" once saved.

- **(a) Root cause**: two contributing factors, both timing/logging related, not a second readiness bug. First, `onCameraReady` can fire slightly before the native camera session actually accepts `takePictureAsync` on some devices — a documented `expo-camera` quirk, not something JS-side state alone fully closes. Second, and more directly explaining "still shown in the UI": any caught error logged with `console.error` still triggers React Native's intrusive red LogBox overlay in dev mode, regardless of whether the surrounding code recovered gracefully — so a harmless, self-recovering dropped live-detect frame was rendering as if it were a crash.
- **Fix (a)**: added a 400ms grace buffer (`CAMERA_READY_GRACE_MS`) after `onCameraReady` before flipping `isCameraReady`, on top of the existing gate. Downgraded the live-detect frame-capture catch from `console.error` to `console.warn` (RN's LogBox treats these very differently) — an expected, continuously-retried frame drop is not an error-level event.
- **(b) Root cause**: `guardarLibro` only ever saved `isbn`, discarding `foundBook.texts` (the OCR snippets the model actually read off the cover). Since `title` is always absent by design (no fabricated titles, per the earlier option (a) decision), every saved cover-kind scan fell through to the generic "Portada sin identificar" placeholder — even when OCR had genuinely read something.
- **Fix (b)**: `Book` gained an optional `recognizedText` field, populated by a new `joinRecognizedTexts` helper (the same OCR-join expression already used in the scan-result modal, deduplicated rather than copy-pasted a second time). `biblioteca.tsx`'s title fallback chain is now `title ?? recognizedText ?? 'Portada sin identificar'`. This does not violate the "no fabricated title" decision — it is still literally the text OCR read, the same thing already honestly shown in the confirm-scan modal before saving.
- **GREEN evidence**: `npx tsc --noEmit -p tsconfig.json` on all four changed files shows no new errors (same two pre-existing, unrelated errors as before this session touched anything).
- **Known gap, unchanged**: still no automated test for the TS/RN side; still no on-device confirmation performed by me directly — pending the user's next retest.
