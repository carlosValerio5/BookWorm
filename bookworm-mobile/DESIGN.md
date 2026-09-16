---
name: BookWorm Mobile
description: Warm dark thrift scanner with vintage gold star accents; camera full-bleed, results on a sheet.
extends: ../DESIGN.md
---

# Design System: BookWorm Mobile

## North star: "The Viewfinder"

The aisle is the context. The screen is mostly **live camera** on **ground** (`#14120b`). A thin top bar (wordmark + version) and bottom tab bar sit on **surface-1**. Capture is one obvious control; everything else waits until after the shot.

Shared tokens, typography rules, and accent semantics live in the repo root [`DESIGN.md`](../DESIGN.md). This file is only what changes on a phone.

## Screens

| Screen | Job | Layout |
|--------|-----|--------|
| **Escanear (idle)** | Invite capture | Ground fill; centered dashed **gold-line** frame on surface-1; **✦** star + gold **live dot**; primary line + caption |
| **Escanear (active)** | Aim and shoot | Full-bleed camera; subtle ground scrim; bottom **pill** shutter hint; loading = spinner on scrim, no fake progress |
| **Result sheet** | Confirm match | Modal **sheet** on surface-1, 12px top radius; cover thumb; title 500; author text-2; ISBN mono caption; primary pill **Guardar**; text dismiss |
| **Biblioteca** | Recall finds | Gold **✦** on section label; count pill with gold hairline; rows = surface-1 cards with spine stripe (gold + muted pastels from ISBN hash); empty = three gold stars + dark book stack with gold spines |
| **Errors** | Recover | **Problem** pattern from annotator: 14% bad tint, no full-width red banner |

## Mobile components

- **Primary pill** — Same as annotator: fill `text`, label `ground`, height 48px on mobile (touch), full width in sheets.
- **Camera frame** — 1px `line-2` dashed, 16px corner (not 24px soft UI); no heavy drop shadow (One Lift Rule → no shadow on cards; hairline only).
- **Tab bar** — `surface-1` background; selected tab label **gold** (`#f2cc8f`), unselected `text-3`.
- **Star accent (`✦`)** — Decorative only (`StarAccent`); headers, empty state, result sheet. Never a button.
- **Gold tokens** — `gold`, `goldLine`, `goldDeep` for borders, badges, live dot, loading spinner on camera.
- **Book row** — surface-1, 8px radius, 1px line-2; left stripe from `type-*` palette for visual variety without rainbow chrome.

## Motion

- Sheet: fade + slight translate up, 160ms, `cubic-bezier(0.16, 1, 0.3, 1)`.
- Respect `Reduce motion` → instant sheet.

## Do / don't (mobile)

**Do** default the app to warm dark tokens in `src/constants/theme.ts`.  
**Do** use mono for ISBN only.  
**Do** keep serif off the wordmark (system sans 500, 20–22px).  

**Don't** reuse the annotator traffic-light window chrome.  
**Don't** use light aqua panels (`#EAF6F9`) — retired prototype look.  
**Don't** use orange on mobile chrome (reserved for desktop annotator live state).  
**Don't** turn stars into tappable controls.

## Implementation map

| Token | RN key in `Colors.dark` |
|-------|-------------------------|
| ground | `background` |
| surface-1 | `backgroundElement` |
| surface-2 | `backgroundSelected` |
| text / text-2 / text-3 | `text`, `textSecondary`, `textTertiary` |
| line-2 | `border` |
| accent | `accent` |
| good / bad | `good`, `bad` |

Screens should import `Colors` and shared `Spacing` instead of inline hex (migration in progress).
