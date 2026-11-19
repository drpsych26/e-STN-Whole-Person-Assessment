// Service worker for the STN assessment review copy.
// Scope: caches the static application shell only (the page, manifest and runtime config).
// It never caches or stores client responses, form data or any cross-origin or non-GET request.
// Offline use is limited to opening the shell; no client data is kept offline by this worker.
const CACHE = "stn-assessment-shell-v1";
const SHELL = [
  "./",
  "./assessment-demo.REVIEW-CORRECTED.html",
  "./manifest.webmanifest",
  "./runtime-config.js",
];

self.addEventListener("install", (event) => {
  event.waitUntil(caches.open(CACHE).then((cache) => cache.addAll(SHELL)));
  self.skipWaiting();
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k)))
    ).then(() => self.clients.claim())
  );
});

self.addEventListener("fetch", (event) => {
  const req = event.request;
  if (req.method !== "GET") return;
  const url = new URL(req.url);
  if (url.origin !== self.location.origin) return;
  if (!SHELL.some((p) => url.pathname.endsWith(p.replace("./", "/")) || (p === "./" && url.pathname.endsWith("/")))) {
    return; // not a shell file: go to the network, do not cache
  }
  event.respondWith(
    fetch(req)
      .then((res) => {
        if (res.ok) {
          const copy = res.clone();
          caches.open(CACHE).then((cache) => cache.put(req, copy));
        }
        return res;
      })
      .catch(() => caches.match(req).then((hit) => hit || Response.error()))
  );
});
