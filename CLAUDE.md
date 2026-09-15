# BookWorm
BookWorm is targeted towards those addicted to reading, and more importantly, thrifters whom want a quick tool to lookup book references.
This tool leverages yolo to scan the cover of a book or even an identifier code to figure out which book they're looking at.
This tool plugs into a local database where users can store their finds.
In a future version the idea would be to add an agent with tool calls that can do some research on the book for them.

## DEVELOPMENT
We are a team working towards the same goal, we're pair programming and we expect to have friction as it is normal in development.
Friction is a signal of success, not regression.
I want you to push back on my ideas when they sound to crazy, and provide easier alternatives when I over-engineer.

## CONVENTIONS
We establish a strict framework so the code is easy to follow and maintain:
- Functions should have a single purpose and a function should only cover a single execution path.
- Names MUST be descriptive, if you need to add comments to understand something, your naming is wrong and obfuscated.
- Pick the data structure first, then think about the implementation.
- Add comments only when you need them, if something needs comments, that's a signal that we may need another implementation.
- Avoid abstraction hell, we don't want to be looking at a class that nobody can trace back to.

### Stack
The tech stack is flexible, but we must have two things:
- Python
- yolo

Use uv as the version manager.

## LANGUAGE
Be concise, clear and straightforward, if we don't speak the same language everything goes wrong.
Pick the simplest terms to explain something and be brief, if you output paragraphs of text, I'm surely not going to read them;
think of it as if you're my intern and I'm your manager, you want to communicate clearly and be effective.

Use conventions like:
- D1, D2, ... for discoveries.
- B1, B... for bugs
- F1, F... for features
etc.

## LOGGING
BE VERY STRICT WITH LOGGING.
Logging is the single most improtant part of a good software piece, if we can't trace back to an error, we aren't doing it right.
Use a good logging library and consider plugging in tools like grafana.
In the log event, include important information like, date, the call made, and which service made the call.

## MultiAgent Workloads
For multiagent workloads, always use worktrees.
The structure should be as follows:
- Planner agent
This agent plans out the complete scope and divides into smaller features.
- Worker
The worker executes what it's been told, only that.

Once the worker finishes it submits its work to the planner and the planner is in charge of merging everything together.

**When a task is too complex**
If this happens, we want to recursively break down the task, if the planner submits a task too big for a worker, divide it again and redistribute it, that worker turns into another planner.


## Tracebacks
Here you'll record any issues we find along the way, this is how we keep improving and not repeat the same mistakes.

- T1 (2026-09-15): `uv init` runs `git init` when the folder isn't a repo. Check for a surprise `.git/` after init.
- T2 (2026-09-15): `easyocr` depends on `opencv-python`. Adding `opencv-python-headless` next to it installs two `cv2` builds that overwrite each other. Use only `opencv-python`.
- T3 (2026-09-15): Stock YOLO (COCO) has a `book` class but no barcode class. Barcodes are read with `zxing-cpp`, not YOLO.
- T4 (2026-09-15): `round(0.98765, 4)` is not guaranteed to be `0.9877` (float representation). Don't use half-way values in test fixtures.
- T5 (2026-09-15): EasyOCR on Apple MPS warns `pin_memory ... not supported on MPS`. Harmless, ignore.

