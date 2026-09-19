#!/usr/bin/env python3
"""Render the course notes to encrypted, self-contained reading pages.

The markdown never enters the repository. Each page ships as AES-GCM ciphertext
that the browser decrypts with a passphrase-derived key, and the diagrams are
encrypted the same way and decrypted to blob URLs as they scroll into view.
"""
import base64, getpass, hashlib, json, os, pathlib, re, secrets, shutil, subprocess, sys

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from md2html import convert

HERE = pathlib.Path(__file__).parent
SRC = pathlib.Path.home() / 'personal' / 'coursera'
ASSETS_OUT = HERE / 'notes-assets'
ITER = 250_000

# Two separate documents, two separate pages.
DOCS = [
    ('exam-prep.md', 'exam-prep.html', 'NASM exam preparation', 'Exam prep'),
    ('learning.md',  'learning.html',  'The body and training', 'Learning'),
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
        html = html.replace('href="exam-prep.md', 'href="exam-prep.html')
        html = html.replace('href="learning.md', 'href="learning.html')
        html = html.replace(f'href="{out}#', 'href="#')   # same-page links stay in-page
        html = html.replace('>exam-prep.md<', '>the exam preparation notes<')
        html = html.replace('>learning.md<', '>the learning notes<')

        payload = json.dumps({'title': title, 'html': html, 'toc': toc}, ensure_ascii=False)
        iv, ct = encrypt(key, payload.encode())
        blob = json.dumps({
            'salt': base64.b64encode(salt()).decode(),
            'iv': base64.b64encode(iv).decode(),
            'ct': base64.b64encode(ct).decode(),
            'iter': ITER,
        }, separators=(',', ':'))

        page = (template
                .replace('__LOGO__', logo)
                .replace('__TITLE__', title)
                .replace('__TAG__', tag)
                .replace('__FOOT__', f'{len(md.split()):,} words. Encrypted; readable offline once unlocked.')
                .replace('__PAYLOAD__', blob))
        (HERE / out).write_text(page)
        print(f'{out:18} {len(page)/1024:6.0f} KB   {len(toc)} sections, '
              f'{html.count("<table>")} tables, {html.count("<figure>")} figures')

    if used:
        n, size = images(key, used)
        print(f'notes-assets/      {size/1024/1024:6.1f} MB   {n} encrypted diagrams')

    # Bump the service worker cache name so a redeploy actually refreshes.
    # The notes pages are in the worker's ASSETS list, so without this a
    # returning visitor keeps being served the previously cached version.
    sw = HERE / 'sw.js'
    if sw.exists():
        v = int(re.search(r'pt-prep-v(\d+)', sw.read_text()).group(1))
        sw.write_text(re.sub(r'pt-prep-v\d+', f'pt-prep-v{v + 1}', sw.read_text()))
        print(f'sw.js              cache bumped to pt-prep-v{v + 1}')

if __name__ == '__main__':
    main()
