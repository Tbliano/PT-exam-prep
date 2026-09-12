# PT Exam Prep

Revision for the NASM personal training material, in Raccoon Touch branding. One page, no build
tooling to install, works offline.

## What is here

**Two quiz decks, played independently.**

- **NASM exam prep** — everything examinable, from scope of practice through to the energy systems.
- **Muscles** — origin, insertion, action and role, drawn from the NASM Appendix C tables, the
  anatomy and physiology notes, and standard anatomy.

Rounds of twenty. Wrong answers show the correct one with a short explanation, are stored as
**difficult**, and come back in later rounds until answered correctly twice in a row. At most a
quarter of any round is difficult questions, so rounds stay mixed. Progress is kept in the browser on
that device only and is never sent anywhere.

**Both notes documents**, the exam preparation one and the longer learning one, laid out for
reading with a table of contents that follows the scroll.

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

Edit `questions-exam.json` or `questions-muscles.json`, then:

```
python3 build.py
```

Each entry is:

```json
{"t":"Topic", "q":"Question?", "o":["A","B","C","D"], "a":1, "e":"Why."}
```

`a` is the zero-based index of the correct option. Each question gets a stable id hashed from its
text, so reordering or inserting questions does not disturb stored progress. The build also bumps the
service worker cache version so a redeploy actually refreshes.

## Files

| | |
|---|---|
| `template.html` | The quiz page, before the questions are inlined |
| `reader-template.html` | The notes reader, before the ciphertext is inlined |
| `build.py` | Builds `index.html` |
| `build-notes.py` | Builds `exam-prep.html` and `learning.html` |
| `md2html.py` | A small dependency-free markdown converter |

`index.html`, `exam-prep.html` and `learning.html` are generated. Do not edit them by hand.
