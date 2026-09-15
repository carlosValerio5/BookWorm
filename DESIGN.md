---
name: BookWorm Annotator
description: A warm dark desktop window for labeling real book photos, keyboard first.
colors:
  ground: "#14120b"
  surface-1: "#1b1913"
  surface-2: "#201e18"
  text: "#edecec"
  text-2: "rgb(237 236 236 / 0.6)"
  text-3: "rgb(237 236 236 / 0.5)"
  line-1: "rgb(237 236 236 / 0.025)"
  line-2: "rgb(237 236 236 / 0.1)"
  line-3: "rgb(237 236 236 / 0.2)"
  accent: "#f54e00"
  good: "#1f8a65"
  bad: "#cf2d56"
  type-book: "#9fc9a2"
  type-barcode: "#e59a7c"
  type-printed-isbn: "#e6c07b"
  type-title: "#9fbbe0"
  type-author: "#c0a8dd"
  type-publisher: "#e5a0c0"
  type-other-text: "#b9b4a7"
typography:
  headline:
    fontFamily: "system-ui, -apple-system, SF Pro Text, Helvetica Neue, Helvetica, Arial, sans-serif"
    fontSize: "15px"
    fontWeight: 500
    lineHeight: 1.45
  title:
    fontFamily: "system-ui, -apple-system, SF Pro Text, Helvetica Neue, Helvetica, Arial, sans-serif"
    fontSize: "13px"
    fontWeight: 500
    lineHeight: 1.45
  body:
    fontFamily: "system-ui, -apple-system, SF Pro Text, Helvetica Neue, Helvetica, Arial, sans-serif"
    fontSize: "13px"
    fontWeight: 400
    lineHeight: 1.45
  label:
    fontFamily: "system-ui, -apple-system, SF Pro Text, Helvetica Neue, Helvetica, Arial, sans-serif"
    fontSize: "12px"
    fontWeight: 500
    lineHeight: 1.45
  caption:
    fontFamily: "system-ui, -apple-system, SF Pro Text, Helvetica Neue, Helvetica, Arial, sans-serif"
    fontSize: "12px"
    fontWeight: 400
    lineHeight: 1.45
    fontFeature: "tnum"
  mono-number:
    fontFamily: "ui-monospace, SF Mono, Menlo, Consolas, monospace"
    fontSize: "12px"
    fontWeight: 400
    fontFeature: "tnum"
  keycap:
    fontFamily: "ui-monospace, SF Mono, Menlo, Consolas, monospace"
    fontSize: "11px"
    fontWeight: 500
    lineHeight: 1
    fontFeature: "tnum"
rounded:
  swatch: "2px"
  photo: "4px"
  key: "5px"
  icon: "6px"
  row: "8px"
  window: "12px"
  pill: "999px"
spacing:
  hair: "2px"
  xs: "4px"
  sm: "6px"
  md: "8px"
  lg: "10px"
  pane: "14px"
  group: "20px"
components:
  window:
    backgroundColor: "{colors.surface-1}"
    rounded: "{rounded.window}"
  button-primary:
    backgroundColor: "{colors.text}"
    textColor: "{colors.ground}"
    typography: "{typography.title}"
    rounded: "{rounded.pill}"
    padding: "0 14px"
    height: "34px"
  segmented-track:
    backgroundColor: "{colors.ground}"
    rounded: "{rounded.pill}"
    padding: "3px"
  segment:
    textColor: "{colors.text-2}"
    typography: "{typography.body}"
    rounded: "{rounded.pill}"
    height: "30px"
  segment-hover:
    backgroundColor: "{colors.line-2}"
    textColor: "{colors.text}"
  segment-active:
    backgroundColor: "{colors.text}"
    textColor: "{colors.ground}"
  type-option:
    textColor: "{colors.text-2}"
    rounded: "{rounded.row}"
    padding: "0 5px 0 10px"
    height: "32px"
  type-option-selected:
    backgroundColor: "{colors.surface-2}"
    textColor: "{colors.text}"
  queue-row:
    textColor: "{colors.text-2}"
    rounded: "{rounded.row}"
    padding: "8px"
  queue-row-hover:
    backgroundColor: "{colors.line-1}"
    textColor: "{colors.text}"
  queue-row-current:
    backgroundColor: "{colors.surface-2}"
    textColor: "{colors.text}"
  text-input:
    backgroundColor: "{colors.ground}"
    textColor: "{colors.text}"
    typography: "{typography.body}"
    rounded: "{rounded.row}"
    padding: "0 10px"
    height: "30px"
  keycap:
    backgroundColor: "{colors.line-1}"
    textColor: "{colors.text-2}"
    typography: "{typography.keycap}"
    rounded: "{rounded.key}"
    padding: "3px 5px"
  icon-button:
    textColor: "{colors.text-3}"
    rounded: "{rounded.icon}"
    size: "24px"
  problem:
    textColor: "{colors.text}"
    rounded: "{rounded.row}"
    padding: "8px 10px"
---

# Design System: BookWorm Annotator

## Overview

**Creative North Star: "The Review Window"**

The annotator is a warm dark desktop application window, drawn from the Cursor website's style that the user made the binding reference. Everything sits inside one rounded window on a thin margin of ground: a title bar with traffic lights and a centered title, a quiet list on the left, the photo as the main editor in a darker well, a label pane on the right and a status bar along the bottom. The photo is the only loud thing on screen; the chrome is text on warm near-black, separated by hairlines rather than boxes.

The system is dense and calm. One system sans carries every level at 12 to 15px, and hierarchy comes from weight (400 versus 500) and from three text opacities, not from size jumps. Mono appears only where a character must align: keycaps, pixel coordinates, the photo size and the timer. Color is rationed by meaning: orange marks only what is live, green means labeled, red means a problem, and a set of soft pastel data colors identify box types on photos.

Controls are full pills and soft rows. Keyboard shortcuts are visible as small hairline keycaps next to the control they trigger, because the tool is driven from the keyboard.

**Key Characteristics:**
- One window with traffic lights, a 40px title bar and a 30px status bar framing three columns.
- Warm dark ground and two raised surfaces; depth by tone and hairline, one soft window shadow.
- Text at 100%, 60% and 50%; hairlines of the same text at 2.5%, 10% and 20%.
- Orange for the live state only; primary action filled with the text color, not the accent.
- System sans everywhere, mono only for keys and numbers that align.
- Box-type pastels as data colors, shown as 8px swatches in chrome and as strokes and chips on the photo.

## Colors

A warm near-black ground with text-derived neutrals and three single-purpose signal colors, plus a separate pastel family that belongs to the data, not the chrome.

### Primary
- **Live Orange** (accent): marks what is happening now and nothing else: the dot before the status-bar mode, the text caret in box inputs, and the text selection tint (35% mix). It never fills a button.

### Secondary
- **Labeled Green** (good): a finished state: the check icon on labeled photos in the queue and the dot before "Saved".
- **Problem Red** (bad): validation problems. Used as a 14% tint background with text mixed 45% red into the text color, never as a solid fill.

### Tertiary
Box-type data colors, one per label type, all soft pastels chosen to read as strokes and chips over real photos: **Sage** (type-book), **Clay** (type-barcode), **Straw** (type-printed-isbn), **Sky** (type-title), **Lilac** (type-author), **Rose** (type-publisher), **Stone** (type-other-text). In the chrome they appear only as 8px swatches with 2px corners, the 1px left edge of the selected box row, and the 55% border of the selected type option. On the canvas they are the box stroke, the 10 to 12% fill, the chip background and the 75% crosshair.

### Neutral
- **Warm Ground** (ground): the page margin, the photo well, the segmented-control track and text inputs. Also the text color inside filled pills and canvas chips.
- **Window Surface** (surface-1): the window body, pills over the photo on the class lock, select menus.
- **Raised Surface** (surface-2): the current queue row, the selected type option and the selected box row.
- **Paper Text** (text): primary text and the filled primary button.
- **Secondary Text** (text-2): labels, resting rows and controls, save status, the focus outline.
- **Tertiary Text** (text-3): counts, meta, coordinates, placeholders, hints. Deliberately 50%, not the reference's 40%, to hold 4.5:1 on the ground.
- **Faint Hairline** (line-1): resting borders of type options, hover wash on rows, keycap fill.
- **Hairline** (line-2): every structural divider, window border, input border, segment hover, input focus ring.
- **Strong Hairline** (line-3): focused input border, traffic lights, scrollbar thumb.

### Named Rules
**The Live Only Rule.** Orange marks the current live state (mode dot, caret, selection). If an element is not happening right now, it is not orange.

**The Text Is The Ink Rule.** Neutrals are the text color at an opacity, never a new gray. Hairlines are text at 2.5, 10 or 20%; secondary text is 60 or 50%.

**The Data Stays On The Photo Rule.** Box-type pastels identify labels. In chrome they shrink to a swatch, an edge or a tinted border; they never fill a control.

## Typography

**Body Font:** system-ui (with -apple-system, SF Pro Text, Helvetica Neue, Helvetica, Arial, sans-serif)
**Label/Mono Font:** ui-monospace (with SF Mono, Menlo, Consolas, monospace)

**Character:** A native desktop voice: the platform sans at small sizes, weight doing the work of hierarchy, with mono kept for the few things that must align.

### Hierarchy
- **Headline** (500, 15px): the empty-stage prompt in the photo well. The class-lock title uses the same weight at 14px.
- **Title** (500, 13px): the photo name in the title bar, button text, the selected box type in a box row.
- **Body** (400, 13px, 1.45): rows, segments, type options, inputs. Root size of the page.
- **Label** (500, 12px): pane and group headings ("Class", "Box type", "To label"), in sentence case at text-2.
- **Caption** (400, 12px, tabular figures): counts, save status, status bar, problems, notes.
- **Mono Number** (400, 11.5 to 12px, tabular figures): pixel coordinates, photo size, cursor readout, timer.
- **Keycap** (500, 11px mono, line-height 1): shortcut keys.

### Named Rules
**The Weight Not Size Rule.** The whole ramp lives between 11 and 15px. Promote with weight 500 or full text opacity before reaching for a bigger size.

**The Mono Means Aligned Rule.** Mono is for keys and numbers that are compared or read as coordinates. Words are always sans.

## Layout

The page is a single app window filling the viewport inside a 10px ground margin. The window is a grid: 264px left queue, a flexible photo well, a 320px label pane; rows of 40px title bar, flexible body and 30px status bar. The photo is fitted as large as the well allows, centered on the ground.

Spacing runs on a small rhythm of 2, 4, 6, 8, 10 and 14px, with 20px between queue groups. Panes pad at 14px; rows pad at 8px; gaps inside controls are 6 to 8px. Lists inside the label pane bleed to the pane edge and divide with full-width hairlines.

At 1180px and below the columns narrow to 220px and 296px and the status-bar shortcut hints hide. At 860px and below the window loses its margin and corners and stacks: title bar, photo at 62vh, queue (max 220px), label pane, status bar; the photo size, cursor readout and long progress text hide.

## Elevation & Depth

Depth is tonal. The ground sits lowest, the window surface above it, and the raised surface marks what is current or selected. Hairlines separate regions. The only drop shadow is the window's soft ambient lift; selected rows use an inset 1px hairline ring instead of a shadow.

### Shadow Vocabulary
- **Window lift** (`box-shadow: 0 30px 80px -30px rgb(0 0 0 / 0.7)`): the app window only.
- **Current row ring** (`box-shadow: inset 0 0 0 1px` line-2): the current queue row.
- **Input focus halo** (`box-shadow: 0 0 0 3px` line-2): focused text inputs, with the border moving to line-3.

### Named Rules
**The One Lift Rule.** Only the window casts a shadow. Everything inside it separates by tone and hairline.

## Shapes

Corners scale with the object: 12px for the window, 8px for rows, options, inputs and problems, 6px for icon buttons, 5px for keycaps, 4px for the photo and canvas chips, 2px for type swatches. Anything you press to choose or commit is a full pill (999px): the primary button, the segmented class control and its segments, and the class-lock callouts. Status dots and traffic lights are circles. Borders are always 1px hairlines. Icons are inline 16px line SVGs with a 1.4 round stroke in currentColor.

## Components

### Buttons
Quiet until pressed, and the one commit action is unmistakable.
- **Shape:** full pill (999px), 34px tall.
- **Primary:** filled with the text color, ground-colored 500 text, 14px side padding, full width at the foot of the label pane, keycap inline with a ground-tinted outline.
- **Hover / Focus:** background eases to 86% text mixed into ground over 160ms; focus shows a 2px text-2 outline offset 2px. Disabled drops to 60% opacity with a progress cursor.
- **Icon button:** 24px square, 6px corners, text-3 icon; hover washes line-2 and lifts the icon to full text.

### Segmented Control
- **Style:** a ground track with a hairline border and 3px padding holding equal pill segments, 30px tall, each with its keycap.
- **State:** resting segments are text-2; hover washes line-2; the pressed segment fills with the text color and ground text, like the primary button.

### Chips
- **Type option:** 32px row in a two-column grid, 8px corners, faint hairline border, 8px swatch, label, keycap at right. Selected: raised surface, full text, border at 55% of its type color.
- **Keycap:** 11px mono on a line-1 fill with a line-2 border and 5px corners, min 18px wide.

### Cards / Containers
- **Corner Style:** 12px window; panes have no corners of their own.
- **Background:** surface-1 window, ground photo well.
- **Shadow Strategy:** see The One Lift Rule.
- **Border:** 1px line-2 around the window and between every region.
- **Internal Padding:** 14px panes.

### Inputs / Fields
- **Style:** 30px, ground fill, 1px line-2 border, 8px corners, orange caret, text-3 placeholder.
- **Focus:** border to line-3 plus a 3px line-2 halo; no outline.
- **Inline select:** borderless, transparent, 500 weight with a small chevron; options on surface-1.

### Navigation
- **Queue rows:** 8px padding, 8px corners, a 16px status icon (dashed circle to label, green check labeled), ellipsized name, tabular text-3 meta. Hover washes line-1 and lifts text; current row sits on surface-2 with an inset hairline ring. Groups are headed by a Label-style heading with a tabular count.
- **Mobile:** the queue stacks under the photo, capped at 220px.

### App Window
- **Title bar:** three neutral line-3 traffic lights, a centered photo name with its mono pixel size, and at right the save status (dot: text-3 idle, green saved, full text unsaved) and progress count.
- **Status bar:** 30px, 12px text-2: orange-dotted mode, current box-type swatch, mono cursor readout and timer, keycap hints pushed right.

### Photo Canvas
- **Boxes:** 1.5px type-color stroke over a 3.5px 60% ground halo so it reads on any photo; selected boxes stroke at 2.5px with a 12% fill and 6px ground-filled corner handles.
- **Chips:** 18px tall, 4px corners, type-color fill with ground 500 11px sans text, placed above or below the box where free. The selected chip adds " · " and the box text, truncated at 24 characters.
- **Drawing:** a 6/4 dashed stroke with a 10% fill; the crosshair is a 3/4 dashed 1px line at 75% of the active type color.
- **Class lock:** until a class is picked, a 135deg hatched ground veil (40% and 25% bands, 7px) covers the photo with a pill callout and three pill key hints.

### Box Rows
- **Style:** full-bleed rows with 10px 14px padding and a hairline below: swatch, inline type select, mono coordinates, remove button, then the text input or a text-3 note.
- **State:** selected rows sit on surface-2 with a 1px type-color left edge.

### Problems
- **Style:** 8px corners, 14% red tint, text mixed 45% red, 16px problem icon, 12px text.

## Do's and Don'ts

### Do:
- **Do** keep the whole tool inside one window with traffic lights, a centered title and a status bar.
- **Do** derive every neutral from the text color at 60% or 50% for text and 2.5%, 10% or 20% for hairlines.
- **Do** keep tertiary text at 50% so counts and hints hold 4.5:1.
- **Do** fill the one commit action with the text color and make choose-and-commit controls full pills.
- **Do** show the shortcut as a keycap next to every keyboard-reachable control.
- **Do** set coordinates, sizes and timers in mono with tabular figures, in original photo pixels.
- **Do** ease state changes over 160ms with cubic-bezier(0.16, 1, 0.3, 1), and drop all motion under reduced-motion.

### Don't:
- **Don't** use orange for anything that is not the live state: no orange buttons, borders or headings.
- **Don't** introduce a gray that is not the text color at an opacity.
- **Don't** fill chrome controls with box-type colors; they stay swatches, edges and tinted borders.
- **Don't** add drop shadows inside the window; separate with tone and hairlines.
- **Don't** set words in mono or bring in a display or serif face.
- **Don't** color the traffic lights; they are neutral line-3 dots.
