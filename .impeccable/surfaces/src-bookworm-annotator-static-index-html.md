---
version: 1
slug: "src-bookworm-annotator-static-index-html"
primary_target: "src/bookworm/annotator/static/index.html"
related_targets: ["src/bookworm/annotator/static/annotator.css","src/bookworm/annotator/static/annotator.js"]
---

# Surface brief: BookWorm Annotator page

## Scope and mode

The single page of the local labeling web app (`src/bookworm/annotator/static/`). Mode: Operate. The visitor is in a task: label one photo, save, move to the next.

## Audience, job and constraints

- BookWorm developers at a desk, next to their editor, working through a folder of real book photos.
- Job: classify the photo, draw typed boxes, type the text inside text boxes, save, next photo. Target under one minute per photo.
- Must stay exactly as it works: every keyboard shortcut (`1` `2` `3`, `b` `c` `i` `t` `a` `p` `o`, Delete/Backspace, ⌘S / Ctrl+S, `n`) and the class-first lock.
- Would feel wrong: slower to label (more clicks, smaller targets, hidden controls), the photo getting smaller, anything that reads as a generic dashboard template.
- No build step, no CDN, works offline.

## Direction contract

THESIS: The annotator is a Cursor desktop window where photos wait like agent tasks ready for review. It refuses the stock labeling-tool arrangement of an icon tool rail, a menu bar and a layer tree.

OWN-WORLD: Cursor's warm dark: ground #14120b, raised surfaces #1b1913 and #201e18, text #edecec at full, 60% and 40%, hairlines of the same text at 2.5%, 10% and 20%. Orange #f54e00 marks only the live state; green #1f8a65 means labeled, red #cf2d56 means a problem. One system sans at every level, mono only for keys and pixel numbers. Full-pill buttons, the primary filled #edecec. A window with traffic lights and a centered title.

STORY: The developer sees how many photos are left, opens the next one, picks the class, draws and names boxes, saves, and presses n, never hunting for a control.

FIRST VIEWPORT: One window filling the viewport inside a thin margin of ground. Title bar: traffic lights, "BookWorm Annotator" and the photos folder centered, labeled count at right. Left list, about 264px: "To label" and "Labeled" groups, each row a status icon, the file name and a muted box count. Center: the photo as large as the height allows on a darker well, with a thin bar naming the photo and its save state. Right pane, about 320px: class as a segmented pill control with key hints, box types with keycaps, boxes as review rows with type color and pixel coordinates, problems, the filled Save pill pinned at the bottom.

FORM: Agent Review Window (the pick card), candidate 1 of 7 on the grounded list; seed key e10e13d7.

FINISH: unreviewed and undocumented is unfinished; this build ends with the finish review, the verdict, DESIGN.md, and every shipping raster carrying its provenance

## Carried disciplines

- The class lock is structural: a hatched veil over the photo that names the three class keys, not just dimming.
- Box rows and the cursor readout show coordinates in original photo pixels as tabular figures.
- The active box type's color marks the drawing crosshair and its row.

## Memorable moment

Opening the annotator feels like opening a Cursor window: a calm review list on the left and the photo as the main editor.

## Unresolved

- Resizing boxes and scanner pre-fill are future milestones, not part of this surface yet.
