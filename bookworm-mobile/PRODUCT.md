# Product: BookWorm Mobile

<!-- impeccable:product-schema 1 -->

## Platform

iOS and Android (Expo). Phone-first; one hand in a thrift aisle.

## Users

Readers who thrift: in a shop with a book in hand, they want a quick ID (ISBN or cover text) and a place to remember what they found before they buy.

## Product Purpose

Point the camera at a back cover (barcode or printed ISBN) or front cover, get a best-effort match, save it to a local biblioteca. Success is **identify in one tap** and **save without typing**.

## Positioning

Not Goodreads or a social shelf. A **pocket lookup + personal haul log** wired to the same scanner the team trains (YOLO, OCR, zxing).

## Operating Context

- Often noisy, one-handed, bad lighting; camera is the main surface.
- Talks to a **local** FastAPI backend on the dev machine today (`/api/scan`); production path is the real `bookworm scan` pipeline, not mock Drácula.
- Biblioteca is on-device for now (`BookContext`); aligns with roadmap local DB.

## Core flows

1. **Scan** — Open camera → capture → loading → result sheet (title, author, ISBN, cover) → save or dismiss.
2. **Biblioteca** — List saved finds; empty state pushes back to scan.
3. **Failure** — Actionable error (permissions, no match, network/backend down); stay off modal dead-ends.

## Capabilities and constraints

- Must work with HEIC from iPhone (backend/image path).
- Spanish UI copy today; language is a product choice, not locked in code forever.
- No account, no cloud sync in v1 mobile design.
- Scanner truth: `kind` is `isbn` | `cover` | `unknown`; UI should not pretend certainty when `unknown`.

## Brand commitments

- Same family as BookWorm Annotator: warm dark, Cursor-inspired, photo/camera is the hero.
- Name: **BookWorm** (tabs: Escanear, Biblioteca).

## Product principles

1. **Camera is the work** — Chrome stays quiet; live state uses orange sparingly.
2. **One tap to capture** — No multi-step wizards in the aisle.
3. **Honest results** — Show what we read (ISBN, OCR snippets) when lookup is thin.
4. **Local first** — Finds stay on the device until we explicitly add sync.
