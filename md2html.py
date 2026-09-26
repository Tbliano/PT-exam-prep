#!/usr/bin/env python3
"""A small markdown to HTML converter, covering exactly what the course notes use:
headings, paragraphs, pipe tables, blockquotes, lists, images, rules, and inline
emphasis, code and links. No dependencies, so the build stays reproducible."""
import html, re

def slug(text):
    s = re.sub(r'<[^>]+>', '', text).lower()
    s = re.sub(r'[^a-z0-9\s-]', '', s)
    return re.sub(r'\s+', '-', s.strip())[:60]

def inline(text):
    text = html.escape(text, quote=False)
    codes = []
    def stash(m):
        codes.append(m.group(1))
        return f'\x00{len(codes)-1}\x00'
    text = re.sub(r'`([^`]+)`', stash, text)
    text = re.sub(r'!\[([^\]]*)\]\(([^)]+)\)', r'<img src="\2" alt="\1">', text)
    text = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', r'<a href="\2">\1</a>', text)
    text = re.sub(r'\*\*([^*]+)\*\*', r'<strong>\1</strong>', text)
    text = re.sub(r'(?<![*\w])\*([^*]+)\*(?!\*)', r'<em>\1</em>', text)
    text = re.sub(r'\x00(\d+)\x00', lambda m: '<code>' + codes[int(m.group(1))] + '</code>', text)
    return text

def convert(md):
    lines = md.split('\n')
    out, toc, i = [], [], 0
    n = len(lines)

    while i < n:
        line = lines[i]

        # blank
        if not line.strip():
            i += 1
            continue

        # heading
        m = re.match(r'^(#{1,6})\s+(.*)$', line)
        if m:
            lvl, text = len(m.group(1)), m.group(2).strip()
            sid = slug(text)
            if lvl in (2, 3):
                toc.append((lvl, text, sid))
            out.append(f'<h{lvl} id="{sid}">{inline(text)}</h{lvl}>')
            i += 1
            continue

        # horizontal rule
        if re.match(r'^-{3,}\s*$', line):
            out.append('<hr>')
            i += 1
            continue

        # standalone image
        m = re.match(r'^!\[([^\]]*)\]\(([^)]+)\)\s*$', line)
        if m:
            alt, src = html.escape(m.group(1), quote=True), m.group(2)
            cap = f'<figcaption>{inline(m.group(1))}</figcaption>' if m.group(1) else ''
            out.append(f'<figure><img src="{src}" alt="{alt}" loading="lazy">{cap}</figure>')
            i += 1
            continue

        # table
        if line.lstrip().startswith('|') and i + 1 < n and re.match(r'^\s*\|[\s:|-]+\|\s*$', lines[i+1]):
            def cells(row):
                return [c.strip() for c in row.strip().strip('|').split('|')]
            head = cells(line)
            aligns = []
            for spec in cells(lines[i+1]):
                aligns.append('center' if spec.startswith(':') and spec.endswith(':')
                              else 'right' if spec.endswith(':') else 'left')
            i += 2
            body = []
            while i < n and lines[i].lstrip().startswith('|'):
                body.append(cells(lines[i]))
                i += 1
            th = ''.join(f'<th style="text-align:{a}">{inline(c)}</th>'
                         for c, a in zip(head, aligns + ['left'] * len(head)))
            trs = []
            for row in body:
                tds = ''.join(f'<td style="text-align:{a}">{inline(c)}</td>'
                              for c, a in zip(row, aligns + ['left'] * len(row)))
                trs.append(f'<tr>{tds}</tr>')
            out.append('<div class="tw"><table><thead><tr>' + th + '</tr></thead><tbody>'
                       + ''.join(trs) + '</tbody></table></div>')
            continue

        # blockquote
        if line.lstrip().startswith('>'):
            block = []
            while i < n and (lines[i].lstrip().startswith('>') or
                             (block and lines[i].strip() and not lines[i].lstrip().startswith(('#', '-', '|')))):
                block.append(re.sub(r'^\s*>\s?', '', lines[i]))
                i += 1
            inner = convert('\n'.join(block))[0]
            cls = 'note'
            joined = ' '.join(block)[:80]
            for key, k in (('**Safety.**', 'safety'), ('**What to say.**', 'say'), ('From the A&P notes', 'ap'), ('From Science of Exercise', 'soe'), ('Added', 'added')):
                if key in joined:
                    cls = 'note ' + k
                    break
            out.append(f'<blockquote class="{cls}">{inner}</blockquote>')
            continue

        # list
        m = re.match(r'^(\s*)([-*]|\d+\.)\s+(.*)$', line)
        if m:
            ordered = not m.group(2) in ('-', '*')
            items, base = [], len(m.group(1))
            while i < n:
                mm = re.match(r'^(\s*)([-*]|\d+\.)\s+(.*)$', lines[i])
                if mm and len(mm.group(1)) == base:
                    items.append([mm.group(3)])
                    i += 1
                elif items and lines[i].strip() and lines[i].startswith(' ' * (base + 2)):
                    items[-1].append(lines[i].strip())   # continuation line
                    i += 1
                else:
                    break
            tag = 'ol' if ordered else 'ul'
            lis = ''.join('<li>' + inline(' '.join(it)) + '</li>' for it in items)
            out.append(f'<{tag}>{lis}</{tag}>')
            continue

        # paragraph
        para = []
        while i < n and lines[i].strip() and not re.match(
                r'^(#{1,6}\s|>|\s*[-*]\s|\s*\d+\.\s|\|)', lines[i]) and not re.match(r'^-{3,}\s*$', lines[i]):
            para.append(lines[i].strip())
            i += 1
        if para:
            out.append('<p>' + inline(' '.join(para)) + '</p>')
        else:
            i += 1

    return '\n'.join(out), toc
