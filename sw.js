// Cache the whole app on first visit so it works with no connection afterwards.
const CACHE = 'pt-prep-cca64f8bca50';
const ASSETS = ['./', './index.html', './exam-prep.html', './learning.html', './exercise-reference.html',
                './manifest.webmanifest'];
// The encrypted diagrams are not precached: they are large, and the network-first
// handler below stores each one the first time it is viewed.

self.addEventListener('install', e => {
  e.waitUntil(caches.open(CACHE).then(c => c.addAll(ASSETS)).then(() => self.skipWaiting()));
});

self.addEventListener('activate', e => {
  e.waitUntil(
    caches.keys()
      .then(ks => Promise.all(ks.filter(k => k !== CACHE).map(k => caches.delete(k))))
      .then(() => self.clients.claim())
  );
});

// Network first so a new round of questions arrives when there is a connection,
// cache fallback so the app still opens when there is not.
self.addEventListener('fetch', e => {
  if (e.request.method !== 'GET') return;
  e.respondWith(
    fetch(e.request)
      .then(r => {
        const copy = r.clone();
        caches.open(CACHE).then(c => c.put(e.request, copy));
        return r;
      })
      .catch(() => caches.match(e.request).then(r => r || caches.match('./index.html')))
  );
});
