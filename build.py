#!/usr/bin/env python3
"""Inline the logo and both question banks into a single self-contained index.html."""
import json, pathlib, re, sys

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from swcache import stamp

here = pathlib.Path(__file__).parent

def qid(text):
    h = 5381
    for ch in text:
        h = ((h * 33) ^ ord(ch)) & 0xFFFFFFFF
    return format(h, 'x')

def deck(fn):
    qs = json.loads((here / fn).read_text())
    out, seen = [], set()
    for q in qs:
        i = qid(q['q'])
        assert i not in seen, 'duplicate question: ' + q['q']
        seen.add(i)
        assert len(q['o']) == 4 and 0 <= q['a'] < 4 and q['e'].strip()
        out.append({'id': i, 't': q['t'], 'q': q['q'], 'o': q['o'], 'a': q['a'], 'e': q['e']})
    return out

data = {
    'muscles': {
        'name': 'Muscles',
        'blurb': 'Origin, insertion, action and role. NASM Appendix C, the A&P notes and standard anatomy.',
        'q': deck('questions-muscles.json'),
    },
    'derive': {
        'name': 'Derive the action',
        'blurb': 'Given only where a muscle attaches, work out what it does when it shortens. Reasoning, not recall.',
        'q': deck('questions-derive.json'),
    },
}

html = (here / 'template.html').read_text()
html = html.replace('__LOGO__', (here / '_logo.svg').read_text().strip())
html = html.replace('__DATA__', json.dumps(data, ensure_ascii=False, separators=(',', ':')))
(here / 'index.html').write_text(html)

# Name the service worker cache after the content, so a redeploy refreshes
# and running the build twice changes nothing.
stamp(here)

total = sum(len(d['q']) for d in data.values())
print(f"index.html built: {total} questions "
      + ", ".join(f"{k} {len(v['q'])}" for k, v in data.items())
      + f" — {(here/'index.html').stat().st_size/1024:.0f} KB")
