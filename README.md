# PT Exam Prep

Revision and study for personal training, in Raccoon Touch branding. No build tooling to install,
works offline.

## What is here

**Four quiz decks, played independently.**

- **Muscles** — origin, insertion, action and role, drawn from the NASM Appendix C tables, the
  anatomy and physiology notes, and standard anatomy.
- **What works what** — exercises, machines and muscles, in both directions, with a set where the
  variation is the point rather than the mapping, and a set on correct position and setup.
- **Derive the action** — given only where a muscle attaches, work out what it does when it
  shortens, what it decelerates, and what it stabilises. Reasoning rather than recall.
- **The notes, section by section** — physiology, programming, nutrition, assessment, safety and
  client scenarios, written from the corrected notes. The same questions appear under **Test me** in
  each section of the notes.

All four were checked against the corrected notes in September 2026 and reviewed for give-aways
(correct answers that are the longest option, echo the stem, or sit among absurd distractors).

**Exam mode.** A hundred questions drawn from every deck, an equal share from each area, options and
order shuffled each time. Sixty minutes, 70% to pass, no feedback until the end. Each result is kept
on the device with the wrong answers and why, and a progress view shows scores over time and which
areas are strong or need work. An exam miss also marks the question difficult in its own deck. An
unfinished exam survives a reload, and marks itself when the time runs out.

Rounds are twenty questions, or fifteen and ten where the thinking is heavier; a deck sets its own
length in `build.py`.

**The NASM exam preparation notes and question deck were removed once the exam was passed**, on
21 September 2026. The markdown still exists locally; it is simply no longer published.

Rounds of twenty. Wrong answers show the correct one with a short explanation, are stored as
**difficult**, and come back in later rounds until answered correctly twice in a row. At most a
quarter of any round is difficult questions, so rounds stay mixed. Progress is kept in the browser on
that device only and is never sent anywhere.

**Both notes documents**, the learning one and the practice reference, laid out for reading with a
table of contents that follows the scroll, and set up for study:

- every section can be marked **Know**, **Shaky** or **New**, with progress shown in the contents;
- tapping a heading folds the section to its name and mark, and a known section starts folded;
- any text can be highlighted, with an optional note, and **Highlights** lists them all;
- **Test me** at the end of a section asks up to ten of its questions; a wrong answer marks it Shaky.

Marks, highlights and notes are saved on the device. With a GitHub token saved (the same one the
editor uses), they also sync between devices through an encrypted `study-<page>.enc` in this
repository, merged item by item so the newest change wins.

**The capture folders behind the practice reference** open in an overlay when their name is tapped,
rather than becoming documents of their own. Each is a separate encrypted payload under `sources/`,
fetched the first time it is opened and kept for the session, so the page itself stays small.

## Offline

`index.html` is self-contained: questions, styles and logo are all inlined and it makes no external
requests. Open it from disk and it works with no server and no connection.

Served over HTTPS it also registers a service worker and a web app manifest, so it can be added to a
phone home screen and opens with no signal after the first visit. On iOS this must be done from
Safari; other browsers there cannot install a web app.

## The notes are encrypted

The markdown source is **not in this repository**. Only ciphertext is published. The page decrypts in
the browser with AES-256-GCM, using a key derived from a passphrase by PBKDF2-SHA256 at 250,000
iterations. Any diagrams are encrypted separately and decrypted to blob URLs as they scroll into view.
The key is remembered per device after the first unlock.

This is real protection, not a JavaScript password box: nothing readable is ever served.

To rebuild the notes:

```
python3 build-notes.py
```

It reads the markdown from `~/personal/coursera`, asks for the passphrase the first time, and stores
it in `.passphrase` along with a fixed `.salt`. Both are git-ignored. The salt is kept stable so a
remembered key survives a rebuild; delete `.salt` and every device has to unlock again.

## Editing the questions

Edit `questions-muscles.json`, `questions-gym.json`, `questions-derive.json` or
`questions-sections.json`, then run both builds (the section questions also travel, encrypted, inside
the notes for Test me):

```
python3 build.py
python3 build-notes.py
```

Each entry is:

```json
{"t":"Topic", "q":"Question?", "o":["A","B","C","D"], "a":1, "e":"Why.", "sec":"learning#section-id"}
```

`sec` is optional: it ties a question to a section of the notes, so it appears under that section's
Test me. `python3 sections.py` lists every section with its id, chapter, exam area and a target
number of questions (about one per 175 words) in `_work/sections.json`. The chapter-to-area mapping
for the exam lives in `sections.py`; a question can override it with `"ar"`.

`a` is the zero-based index of the correct option. Each question gets a stable id hashed from its
text, so reordering or inserting questions does not disturb stored progress.

## The service worker cache

`index.html`, `learning.html` and `exercise-reference.html` are all in the service worker's asset list, so a
returning visitor is served whatever that cache holds. **Both build scripts bump the cache version**,
which is what makes a redeploy actually refresh. Run whichever script matches what you changed, or
both, and the bump is handled.

## Files

| | |
|---|---|
| `template.html` | The quiz page, before the questions are inlined |
| `reader-template.html` | The notes reader, before the ciphertext is inlined |
| `build.py` | Builds `index.html` |
| `build-notes.py` | Builds `learning.html` and `exercise-reference.html` |
| `sections.py` | The study sections of both notes documents, and their exam areas |
| `md2html.py` | A small dependency-free markdown converter |

`index.html`, `learning.html` and `exercise-reference.html` are generated. Do not edit them by hand.
