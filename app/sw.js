// Minimal service worker so the dashboard can be installed as an app. Always uses the network (live data, no stale cache).
self.addEventListener("install", () => self.skipWaiting());
self.addEventListener("activate", (e) => e.waitUntil(self.clients.claim()));
self.addEventListener("fetch", () => {});
