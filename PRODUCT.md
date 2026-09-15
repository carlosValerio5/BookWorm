# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users

BookWorm developers, a two-person pair-programming team, at a desk. They label real book photos, mostly iPhone HEIC shots of front and back covers taken while thrifting, to build ground truth for the BookWorm scanner.

## Product Purpose

BookWorm Annotator turns real book photos into ground-truth labels: the photo's class (`isbn`, `cover`, `unknown`) plus typed boxes with the text inside them, saved as one JSON file per photo in original-photo pixels. The labels feed a scanner accuracy test and, later, YOLO and OCR-with-boxes training. Success is a photo labeled in under a minute, driven from the keyboard.

## Positioning

A labeler cut to BookWorm's own vocabulary: classify first, then the seven box types the scanner and its future models use, with coordinates in the same pixels the scanner reports. It is deliberately not a general annotation platform; Label Studio and CVAT were rejected as too heavy for this job.

## Operating Context

Started locally with `uv run bookworm annotator PHOTOS_DIR` and opened at `http://127.0.0.1:8765` in a desktop browser next to the code editor. Sessions are focused runs through a folder of photos. Photos stay in the gitignored `dataset/`, labels in the gitignored `labels/`.

## Capabilities and Constraints

- Class first: drawing is blocked until `isbn`, `cover` or `unknown` is picked. This lock must stay.
- Box types: `book`, `barcode`, `printed_isbn`, `title`, `author`, `publisher`, `other_text`. Barcode boxes carry no text, `printed_isbn` must contain a valid ISBN, and text types need text.
- Draw, move and delete boxes, save, reopen and edit, go to the next photo.
- Keyboard shortcuts must keep working: `1` `2` `3` class, `b` `c` `i` `t` `a` `p` `o` box type, Delete/Backspace, ⌘S / Ctrl+S, `n` next photo.
- The server validates every save and returns a list of problems; nothing invalid is written.
- Stack: Python FastAPI backend serving plain static HTML, CSS and JS. No build step and no CDN, so it works offline.
- Undecided: pre-filling boxes from the scanner (PRD milestone 2) and resizing boxes.

## Brand Commitments

- Name: BookWorm Annotator, part of BookWorm.
- The user made the Cursor website's sleek, elegant style the binding visual reference for the annotator (2026-09-15).

## Evidence on Hand

- Real photos: `dataset/cover/IMG_0012.HEIC` and `dataset/isbn/9786076410899.HEIC`. They are local and gitignored and must never be committed or published.
- Product requirements: `.claude/prds/book-annotator.prd.md`.
- Labeling time is logged per save as `labeling_duration_ms`; no real timing data exists yet.

## Product Principles

1. The photo is the work: seeing the photo clearly and labeling fast outrank decoration.
2. Keyboard first: every action except drawing a box is reachable without the mouse.
3. Labels are ground truth: validation stays strict and its problems stay visible.
4. Local and private: real photos never leave the machine.
