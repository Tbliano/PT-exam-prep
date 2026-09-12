# PT Exam Prep

A quiz site for revising the NASM personal training material, in Raccoon Touch branding.

Two independent decks:

- **NASM exam prep** — everything examinable, from scope of practice through to the energy systems.
- **Muscles** — origin, insertion, action and role, drawn from the NASM Appendix C tables, the
  anatomy and physiology notes, and standard anatomy.

Rounds of twenty. Wrong answers show the correct one with a short explanation, are stored as
**difficult**, and come back in later rounds until answered correctly twice in a row. At most a
quarter of any round is difficult questions, so rounds stay mixed. Progress is kept in the browser on
that device only and is never sent anywhere.

## Offline

`index.html` is entirely self-contained: the questions, styles and logo are all inlined and it makes
no external requests. Open it from disk and it works with no server and no connection.

Served over HTTPS it also registers a service worker and a web app manifest, so it can be added to a
phone home screen and will open with no signal after the first visit.

## Editing the questions

Edit `questions-exam.json` or `questions-muscles.json`, then:

```
python3 build.py
```

Each entry is:

```json
{"t":"Topic", "q":"Question?", "o":["A","B","C","D"], "a":1, "e":"Why."}
```

`a` is the zero-based index of the correct option. The build script assigns each question a stable id
from a hash of its text, so reordering or inserting questions does not disturb stored progress. It
also bumps the service worker cache version so a redeploy actually refreshes.

`template.html` holds the page; `index.html` is generated and should not be edited by hand.
