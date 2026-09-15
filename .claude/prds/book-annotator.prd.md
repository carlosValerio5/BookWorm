# Book Annotator

## Problem
BookWorm developers test the scanner on real book photos but have no ground truth for where the boxes should be or what text is inside them. Real-photo tests only check the kind (from the folder name) and the ISBN (from the file name), so OCR misreads, duplicate book boxes and missed ISBNs are found by reading logs and eyeballing images. Until that changes we can't measure whether a scanner change made things better or worse, and we won't have labels to train YOLO or an OCR-with-boxes model later.

## Evidence
- Real-photo tests cover 2 photos and check only the kind and the ISBN, never boxes or text (`.claude/tdd/d11-scan-shrunk-copy.tdd.md`, known gaps).
- OCR read "Histora" instead of "Historia" and dropped "de la Literatura". This was found by reading logs by hand (`.claude/tdd/heic-ocr-confidence-spanish.tdd.md`).
- D14: YOLO returns overlapping book boxes (0.47 and 0.27) on one photo. Nothing says which box is correct.
- A sideways printed "ISBN 978-607-641-089-9" is split into separate OCR pieces, and only a visual check caught it.
- Team estimate: labeling by hand without a tool takes too long to be practical. The exact time is not measured, so it's TBD and needs validation by timing the first labeling session.
- The team rejected Label Studio and CVAT because they want a lightweight tool built for this one use case. Assumption: this is faster to set up and use than a general-purpose tool plus a converter. Needs validation via a prototype timed against the per-photo target below.

## Users
- **Primary**: BookWorm developers who take real book photos while working on the scanner. They need labels when a scanner change needs checking, when a new known gap shows up, or when they're building a training set.
- **Not for**: thrifters and other end users of BookWorm, outside annotation teams, and anyone who needs hosted or multi-user labeling.

## Hypothesis
We believe **a lightweight local annotator that pre-fills boxes from the scanner, where you classify the photo first and then correct the boxes** will **let us build ground-truth labels for real book photos quickly** for **BookWorm developers**.
We'll know we're right when **labeling takes under 1 minute per photo** and **a test compares scanner output against at least 30 labeled photos**.

## Success Metrics
| Metric | Target | How measured |
|---|---|---|
| Time to label one photo | Under 1 minute (median) | Time from opening a photo to saving its annotation, recorded in the tool's logs |
| Labeled real photos | At least 30 | Count of saved annotations |
| Scanner accuracy test | Runs against every labeled photo | The test suite reports kind, ISBN, box and text agreement per photo |
| Pre-fill correction rate | TBD, needs a baseline from the first 30 photos | Share of pre-filled boxes a developer moved, retyped or deleted |

## Scope
**MVP**: open a real book photo (HEIC included) from a local folder in a local web app. Pick the class: `isbn`, `cover` or `unknown`, where "another" means `unknown`. See the scanner's boxes and text already filled in. Draw, move and delete boxes, give each one a type, and correct the text or ISBN inside it. Save one annotation per photo with:
- the class
- each box's coordinates in the original photo's pixels
- each box's type and text
- whether a developer confirmed each box

Labeled photos can be reopened and edited. Labels stay on the developer's machine and out of git, like the photos.

**Out of scope**
- Multiple users, logins or hosting. It's one developer on their own machine.
- Training or fine-tuning any model. The labels come first, and training is a separate project.
- Polygons or segmentation masks. The scanner and target models use boxes.
- The local database for thrifters' finds. That's a different product feature.
- Mobile use. Labeling happens at a desk.
- Sharing or syncing labels between developers. They're gitignored for now; see Open Questions.

## Delivery Milestones
<!-- Status: pending | in-progress | complete -->

| # | Milestone | Outcome | Status | Plan |
|---|---|---|---|---|
| 1 | Label a photo by hand | A developer opens a photo, classifies it, draws typed boxes with text, saves, and can reopen and edit it | pending | — |
| 2 | Pre-fill from the scanner | Photos open with the scanner's class, boxes and text already filled in, and the developer only confirms or corrects them | pending | — |
| 3 | Scanner accuracy test | A test compares scanner output with at least 30 labeled photos and reports where they disagree | pending | — |
| 4 | Training export | Labels convert to YOLO training format and to the format of an OCR-with-boxes model such as Chandra | pending | — |

## Open Questions
- [ ] Which box types exist per class? For example, cover could have title, author and publisher, and ISBN could have barcode and printed ISBN. Is it a fixed list or free text? This decides what the scanner test can compare and which YOLO classes we train.
- [ ] What training format does an OCR-with-boxes model like Chandra expect? The annotation must hold everything that format needs. TBD, needs validation by reading the model's docs before milestone 1 is done.
- [ ] Do boxes need rotation for sideways text, such as the printed ISBN on the D11 photo, or are upright boxes enough for YOLO and the OCR model?
- [ ] How do labels survive a lost laptop, and how do two developers share them if they're gitignored?
- [ ] Should a photo the scanner fails to open (a corrupt HEIC, say) be skipped or recorded as a labeling failure?

## Risks
| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Pre-filled labels copy the scanner's mistakes, so the accuracy test passes on wrong ground truth | High | High | Every box records whether a developer confirmed it, unconfirmed boxes look different, and a photo can't be saved as done with unconfirmed boxes |
| The bespoke tool grows into a general-purpose labeler | Medium | Medium | Keep to the out-of-scope list. If milestone 1 misses the 1-minute target, reconsider Label Studio plus a converter |
| The annotation format can't be converted to YOLO or Chandra training data | Medium | High | Confirm both target formats (open question) before milestone 1 is done |
| Box coordinates don't line up with the photo (HEIC orientation, the scanner's 1280px copy) | Medium | High | Store coordinates in original photo pixels and check a saved annotation drawn back on its photo |
| Nobody takes 30 real photos, so the hypothesis can't be tested | Medium | Medium | Set a photo-taking target alongside milestone 1 |
| Gitignored labels are lost or diverge between developers | Medium | Medium | TBD, see open question on backup and sharing |

---
*Status: DRAFT. Requirements only. Implementation planning pending via /plan.*
