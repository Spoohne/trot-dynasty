// Trot Dynasty's service worker: the installed game opens fast and fails gracefully.
// Game pages are live (cash, entries, results), so they always come from the network; when there is none, a branded
// offline page shows instead of the browser's error. Art, sounds, fonts and scripts under /mock/ are kept once fetched,
// so the replay and the barn load instantly on the next visit. Bump VERSION to drop everything cached.
const VERSION = "td-v2";
const SHELL = ["/offline", "/mock/brand/logo_text.png", "/mock/brand/app_192.png"];

self.addEventListener("install", e => {
  e.waitUntil(caches.open(VERSION).then(c => c.addAll(SHELL)).then(() => self.skipWaiting()));
});

self.addEventListener("activate", e => {
  e.waitUntil(caches.keys().then(keys => Promise.all(keys.filter(k => k !== VERSION).map(k => caches.delete(k))))
    .then(() => self.clients.claim()));
});

self.addEventListener("fetch", e => {
  const req = e.request, url = new URL(req.url);
  if (req.method !== "GET" || url.origin !== location.origin) return;           // posts and other sites: untouched
  if (req.mode === "navigate") {                                               // a page: live, or the offline page
    e.respondWith(fetch(req).catch(() => caches.match("/offline")));
    return;
  }
  if (url.pathname.startsWith("/mock/")) {
    const code = /\.(js|css)$/.test(url.pathname);                             // scripts and styles change with every deploy: live first, the
    e.respondWith(caches.open(VERSION).then(c => code                           // cached copy only when there's no network. Art and sounds: cached once fetched
      ? fetch(req).then(res => { if (res.ok) c.put(req, res.clone()); return res; }).catch(() => c.match(req))
      : c.match(req).then(hit => hit || fetch(req).then(res => { if (res.ok) c.put(req, res.clone()); return res; }))));
  }
});
