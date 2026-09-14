// Minimal service worker to make the app installable (PWA).
// It intentionally does not cache API responses so admin data is always fresh.
self.addEventListener("install", () => self.skipWaiting());
self.addEventListener("activate", (event) => event.waitUntil(self.clients.claim()));
self.addEventListener("fetch", () => {});
