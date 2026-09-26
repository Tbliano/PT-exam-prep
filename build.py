#!/usr/bin/env python3
"""Inline the logo and both question banks into a single self-contained index.html."""
import json, pathlib, re, sys

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from swcache import stamp
from sections import index as section_index

here = pathlib.Path(__file__).parent

def qid(text):
    h = 5381
    for ch in text:
        h = ((h * 33) ^ ord(ch)) & 0xFFFFFFFF
    return format(h, 'x')

SECS = section_index()

def deck(fn):
    if not (here / fn).exists():
        return []
    qs = json.loads((here / fn).read_text())
    out, seen = [], set()
    for q in qs:
        i = qid(q['q'])
        assert i not in seen, 'duplicate question: ' + q['q']
        seen.add(i)
        assert len(q['o']) == 4 and 0 <= q['a'] < 4 and q['e'].strip()
        if q.get('sec'):
            assert q['sec'] in SECS, 'unknown section ' + q['sec'] + ' for: ' + q['q']
        out.append({'id': i, 't': q['t'], 'q': q['q'], 'o': q['o'], 'a': q['a'], 'e': q['e'],
                    'ar': q.get('ar') or area(fn, q['t'], q.get('sec'))})
    return out

# Broad areas for the exam summary. A question can set its own with "ar";
# otherwise its deck and topic decide.
GYM_TECHNIQUE = {'Setting it up', 'Spotting and safety', 'Easier or harder'}
def area(fn, topic, sec=None):
    if fn == 'questions-muscles.json':
        return 'Muscle anatomy'
    if fn == 'questions-derive.json':
        return 'Muscle actions'
    if fn == 'questions-gym.json':
        return 'Technique and safety' if topic in GYM_TECHNIQUE else 'Exercise selection'
    if sec:
        return SECS[sec]['area']
    return topic

data = {
    'muscles': {
        'name': 'Muscles',
        'blurb': 'Origin, insertion, action and role. NASM Appendix C, the A&P notes and standard anatomy.',
        'q': deck('questions-muscles.json'),
    },
    'gym': {
        'name': 'What works what',
        'blurb': 'Exercises, machines and muscles, in both directions. The mapping that gets used every day on the gym floor.',
        'round': 10,   # long stems to read, so a shorter round
        'q': deck('questions-gym.json'),
    },
    'derive': {
        'name': 'Derive the action',
        'blurb': 'Given only where a muscle attaches, work out what it does when it shortens. Reasoning, not recall.',
        'round': 10,   # harder thinking per question, so a shorter round
        'q': deck('questions-derive.json'),
    },
    'notes': {
        'name': 'The notes, section by section',
        'blurb': 'Physiology, programming, nutrition, assessment, safety and client scenarios, written from the corrected notes. The same questions appear under Test me in each section.',
        'q': deck('questions-sections.json'),
    },
}
data = {k: v for k, v in data.items() if v['q']}

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
