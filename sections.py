#!/usr/bin/env python3
"""The study sections of both notes documents: every h2 intro and h3, with the id
the reader gives it, its chapter, its size and the broad exam area it belongs to.
"Test me" hangs questions off these ids; the exam groups results by area.

Run directly to write _work/sections.json for whoever is writing questions."""
import json, pathlib, re, sys
sys.path.insert(0, str(pathlib.Path(__file__).parent))
from md2html import slug

SRC = pathlib.Path.home() / 'personal' / 'coursera'
STEMS = ['learning', 'exercise-reference']

# Chapters grouped into the areas the exam reports on. Few enough that every
# area gets a real share of a hundred questions.
AREA = {
    'Five principles': 'Programming',
    'The human movement system': 'Anatomy and movement',
    'The skeletal system': 'Anatomy and movement',
    'Joints': 'Anatomy and movement',
    'The spine': 'Anatomy and movement',
    'How the body moves': 'Anatomy and movement',
    'The muscular system': 'Anatomy and movement',
    'The nervous system': 'Nervous system and motor control',
    'The cardiorespiratory system': 'Heart, lungs and energy',
    'Energy systems': 'Heart, lungs and energy',
    'Measuring energy and fuel use': 'Heart, lungs and energy',
    'Applying this to practice': 'Programming',
    'Nutrition in practice': 'Nutrition',
    'Assessing a client': 'Assessment and safety',
    'Designing a programme': 'Programming',
    'Working with a client': 'Coaching and behaviour change',
    'Training young people': 'Special populations',
    'Exercise as medicine': 'Special populations',
}
SKIP = {'Contents', 'Appendix: what the evidence supports'}

def area_for(stem, chapter):
    if stem == 'exercise-reference':
        return 'Technique and safety'
    return AREA.get(chapter, chapter)

def sections():
    out = []
    for stem in STEMS:
        md = (SRC / (stem + '.md')).read_text()
        chapter, cur = '', None
        for line in md.split('\n'):
            m = re.match(r'^(#{2,3})\s+(.*)$', line)
            if m:
                lvl, title = len(m.group(1)), m.group(2).strip()
                if lvl == 2:
                    chapter = title
                cur = None if chapter in SKIP else {
                    'stem': stem, 'sid': slug(title), 'level': lvl, 'chapter': chapter,
                    'title': title, 'area': area_for(stem, chapter), 'words': 0}
                if cur:
                    out.append(cur)
            elif cur and not line.startswith('#'):
                cur['words'] += len(line.split())
    out = [s for s in out if s['words'] > 0]
    for s in out:
        # About one question per 175 words, two at least, ten at most; skip slivers.
        s['target'] = max(2, min(10, round(s['words'] / 175))) if s['words'] >= 40 else 0
    return out

def index():
    """{'learning#sid': section} for looking up a question's "sec"."""
    return {s['stem'] + '#' + s['sid']: s for s in sections()}

if __name__ == '__main__':
    secs = sections()
    work = pathlib.Path(__file__).parent / '_work'
    work.mkdir(exist_ok=True)
    json.dump(secs, open(work / 'sections.json', 'w'), indent=1, ensure_ascii=False)
    print(len(secs), 'sections;', sum(s['target'] for s in secs), 'target questions')
