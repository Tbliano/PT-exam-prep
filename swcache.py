"""Name the service worker cache after the content it holds.

Both build scripts call this, and either may run alone or before the other.
A counter inflated by one per script per deploy — two per deploy once both
scripts bumped it — and said nothing about what it named. This digests the
pages actually written, so the name identifies the deployed bytes and both
scripts agree on it. The pages are re-encrypted with a fresh IV each build,
so the digest still changes on every run; that is what busts the cache.
"""
import hashlib, pathlib, re

# The pages sw.js precaches. Missing ones are skipped, so this stays correct
# while a document is being added.
PAGES = ['index.html', 'learning.html', 'exercise-reference.html',
         'learning.enc', 'exercise-reference.enc']


def stamp(here):
    """Rewrite the cache name in sw.js from a digest of the built pages.

    Returns the new name, or None if there is no sw.js to stamp.
    """
    sw = pathlib.Path(here) / 'sw.js'
    if not sw.exists():
        return None
    h = hashlib.sha256()
    for name in PAGES:
        f = pathlib.Path(here) / name
        if f.exists():
            h.update(f.read_bytes())
    version = f'pt-prep-{h.hexdigest()[:12]}'
    sw.write_text(re.sub(r'pt-prep-[0-9a-z]+', version, sw.read_text()))
    return version
