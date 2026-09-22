#!/usr/bin/env python3
"""Render the course notes to encrypted, self-contained reading pages.

The markdown never enters the repository. Each page ships as AES-GCM ciphertext
that the browser decrypts with a passphrase-derived key, and the diagrams are
encrypted the same way and decrypted to blob URLs as they scroll into view.
"""
import base64, getpass, hashlib, json, os, pathlib, re, secrets, shutil, subprocess, sys

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from md2html import convert
from swcache import stamp

HERE = pathlib.Path(__file__).parent
SRC = pathlib.Path.home() / 'personal' / 'coursera'
ASSETS_OUT = HERE / 'notes-assets'
ITER = 250_000

# Where the in-browser editor commits published notes back to. The page fetches
# each note's ciphertext as a separate <stem>.enc file, re-encrypts an edit in
# the browser, and writes that one file back through the GitHub contents API.
REPO = 'Tbliano/PT-exam-prep'
BRANCH = 'main'

# Two separate documents, two separate pages.
DOCS = [
    ('learning.md',  'learning.html',  'The body and training', 'Learning'),
    ('exercise-reference.md', 'exercise-reference.html', 'The practice reference', 'Practice'),
]

# The capture folders the practice reference points at. Each becomes its own
# encrypted payload, fetched and shown in an overlay when its name is tapped.
# They are source material rather than another set of notes, so they get no
# page and no place in the navigation.
SOURCES = [
    ('fitness-programming', '_fitness-programming', 'Understanding Fitness Programming',
     ['00-course-structure.md', 'raw-transcripts.md']),
    ('biomechanics', '_biomechanics', 'Clinical Biomechanics',
     ['00-course-structure.md', 'module1-upper-quadrant.md', 'module1-workbook.md',
      'modules2-6-raw-transcripts.md']),
    ('groundwork', '_groundwork', 'Prehab Rehab 101 Groundwork',
     ['00-course-structure.md', 'raw-transcripts.md']),
    ('sc-rehab', '_sc-rehab', 'S&C for Injury Prevention',
     ['00-course-structure.md', 'raw-transcripts.md']),
]

# ---------- key ----------

def passphrase():
    if os.environ.get('PT_PASSPHRASE'):
        return os.environ['PT_PASSPHRASE']
    f = HERE / '.passphrase'
    if f.exists():
        return f.read_text().strip()
    p = getpass.getpass('Passphrase for the notes: ')
    if p != getpass.getpass('Again: '):
        sys.exit('They did not match.')
    f.write_text(p)
    f.chmod(0o600)
    print('Saved to .passphrase (git-ignored) so future builds do not ask.')
    return p

def salt():
    """Stable across builds, so a remembered key keeps working after a rebuild."""
    f = HERE / '.salt'
    if not f.exists():
        f.write_bytes(secrets.token_bytes(16))
        f.chmod(0o600)
    return f.read_bytes()

NODE = shutil.which('node') or '/Users/tliano/.local/node/bin/node'

def encrypt(key, data: bytes):
    """AES-256-GCM. Done in node because openssl enc does not support AEAD ciphers.
    Returns the iv and the ciphertext with the auth tag appended, which is the
    layout WebCrypto's decrypt expects."""
    script = (
        "const c=require('crypto');const b=[];process.stdin.on('data',d=>b.push(d))"
        ".on('end',()=>{const k=Buffer.from(process.argv[1],'hex'),"
        "iv=Buffer.from(process.argv[2],'hex'),"
        "ci=c.createCipheriv('aes-256-gcm',k,iv),"
        "ct=Buffer.concat([ci.update(Buffer.concat(b)),ci.final(),ci.getAuthTag()]);"
        "process.stdout.write(ct)});"
    )
    iv = secrets.token_bytes(12)
    p = subprocess.run([NODE, '-e', script, key.hex(), iv.hex()],
                       input=data, capture_output=True)
    if p.returncode:
        sys.exit('node: ' + p.stderr.decode()[:300])
    return iv, p.stdout

# ---------- images ----------

def images(key, names):
    ASSETS_OUT.mkdir(exist_ok=True)
    for old in ASSETS_OUT.glob('*.enc'):
        old.unlink()
    total = 0
    for name in sorted(names):
        src = SRC / 'assets' / name
        if not src.exists():
            print('  missing:', name)
            continue
        tmp = HERE / '_tmp.png'
        subprocess.run(['sips', '-Z', '900', str(src), '--out', str(tmp)],
                       capture_output=True)
        iv, ct = encrypt(key, tmp.read_bytes())
        (ASSETS_OUT / (name + '.enc')).write_bytes(iv + ct)
        total += len(ct)
        tmp.unlink()
    return len(list(ASSETS_OUT.glob('*.enc'))), total

# ---------- build ----------

def main():
    key = hashlib.pbkdf2_hmac('sha256', passphrase().encode(), salt(), ITER, 32)
    logo = (HERE / '_logo.svg').read_text().strip()
    template = (HERE / 'reader-template.html').read_text()
    used = set()

    for src, out, title, tag in DOCS:
        md = (SRC / src).read_text()
        md = re.sub(r'^## Contents\n(?:.*\n)*?(?=^## )', '', md, flags=re.M)  # the sidebar replaces it
        md = re.sub(r'^#\s+.*\n', '', md, count=1, flags=re.M)                # h1 comes from the title
        html, toc = convert(md)

        for m in re.finditer(r'src="assets/([^"]+)"', html):
            used.add(m.group(1))
        html = re.sub(r'<img src="assets/([^"]+)"', r'<img data-enc="notes-assets/\1.enc"', html)
        # rewrite cross-document links, keeping any #anchor on the end
        html = html.replace('href="learning.md', 'href="learning.html')
        html = html.replace('href="exercise-reference.md', 'href="exercise-reference.html')
        html = html.replace(f'href="{out}#', 'href="#')   # same-page links stay in-page
        html = html.replace('>exam-prep.md<', '>the exam preparation notes<')
        # The exam preparation notes are no longer published, so unwrap those
        # links and leave the sentence intact.
        html = re.sub(r'<a href="exam-prep\.md[^"]*">(.*?)</a>', r'\1', html, flags=re.S)
        # Capture folders open in an overlay instead of linking nowhere.
        for slug, folder, label, _files in SOURCES:
            html = html.replace(
                f'<a href="{folder}/">{folder}/</a>',
                f'<a class="srcref" data-src="{slug}" href="#">{label}</a>')
        html = html.replace('>learning.md<', '>the learning notes<')
        html = html.replace('>exercise-reference.md<', '>the practice reference<')

        # The markdown travels inside the encrypted payload too, so the browser
        # can edit the real source rather than round-tripping the rendered HTML.
        payload = json.dumps({'title': title, 'md': md, 'html': html, 'toc': toc}, ensure_ascii=False)
        iv, ct = encrypt(key, payload.encode())
        blob = json.dumps({
            'salt': base64.b64encode(salt()).decode(),
            'iv': base64.b64encode(iv).decode(),
            'ct': base64.b64encode(ct).decode(),
            'iter': ITER,
        }, separators=(',', ':'))

        # The ciphertext lives in its own file, fetched at runtime, so an edit
        # rewrites this one small file instead of a large HTML page.
        stem = out[:-5]  # drop '.html'
        (HERE / (stem + '.enc')).write_text(blob)

        srcmap = json.dumps([[s, f, l] for s, f, l, _ in SOURCES])
        page = (template
                .replace('__LOGO__', logo)
                .replace('__TITLE__', title)
                .replace('__TAG__', tag)
                .replace('__FOOT__', f'{len(md.split()):,} words. Encrypted; readable offline once unlocked.')
                .replace('__STEM__', stem)
                .replace('__REPO__', REPO)
                .replace('__BRANCH__', BRANCH)
                .replace('__SOURCES__', srcmap))
        (HERE / out).write_text(page)
        print(f'{out:18} {len(page)/1024:6.0f} KB page + {len(blob)/1024:5.0f} KB payload   '
              f'{len(toc)} sections, {html.count("<table>")} tables, {html.count("<figure>")} figures')

    # ---------- source appendices ----------
    SOURCES_OUT = HERE / 'sources'
    SOURCES_OUT.mkdir(exist_ok=True)
    for old in SOURCES_OUT.glob('*.enc'):
        old.unlink()
    stotal = 0
    for slug, folder, label, files in SOURCES:
        parts = []
        for fn in files:
            f = SRC / folder / fn
            if f.exists():
                parts.append(f.read_text())
            else:
                print('  missing:', folder + '/' + fn)
        if not parts:
            continue
        shtml, _stoc = convert('\n\n---\n\n'.join(parts))
        iv, ct = encrypt(key, json.dumps({'title': label, 'html': shtml},
                                         ensure_ascii=False).encode())
        (SOURCES_OUT / (slug + '.enc')).write_bytes(iv + ct)
        stotal += len(ct)
    if stotal:
        print(f'sources/           {stotal/1024/1024:6.1f} MB   '
              f'{len(list(SOURCES_OUT.glob("*.enc")))} encrypted source appendices')

    if used:
        n, size = images(key, used)
        print(f'notes-assets/      {size/1024/1024:6.1f} MB   {n} encrypted diagrams')

    # Bump the service worker cache name so a redeploy actually refreshes.
    # The notes pages are in the worker's ASSETS list, so without this a
    # returning visitor keeps being served the previously cached version.
    version = stamp(HERE)
    if version:
        print(f'sw.js              cache named {version}')

if __name__ == '__main__':
    main()
