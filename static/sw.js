/* ── FoodRush Service Worker ──────────────────────────────────────────────── */
const CACHE_NAME = 'foodrush-v1';

// Assets to cache immediately on install (App Shell)
const PRECACHE_ASSETS = [
    '/',
    '/static/css/style.css',
    '/static/js/main.js',
    '/static/icons/icon-192.png',
    '/static/icons/icon-512.png',
    '/static/images/default.png'
];

// ── Install: pre-cache the app shell ────────────────────────────────────────
self.addEventListener('install', event => {
    event.waitUntil(
        caches.open(CACHE_NAME).then(cache => {
            return cache.addAll(PRECACHE_ASSETS.map(url => {
                return new Request(url, { cache: 'reload' });
            })).catch(err => {
                console.warn('[SW] Pre-cache partial failure (some assets missing):', err);
            });
        })
    );
    self.skipWaiting();
});

// ── Activate: clean up old caches ───────────────────────────────────────────
self.addEventListener('activate', event => {
    event.waitUntil(
        caches.keys().then(keys =>
            Promise.all(
                keys.filter(k => k !== CACHE_NAME).map(k => caches.delete(k))
            )
        )
    );
    self.clients.claim();
});

// ── Fetch: Network-first for pages, Cache-first for static assets ─────────
self.addEventListener('fetch', event => {
    const { request } = event;
    const url = new URL(request.url);

    // Skip non-GET, cross-origin, and API requests
    if (request.method !== 'GET') return;
    if (url.origin !== location.origin) return;
    if (url.pathname.startsWith('/chatbot') ||
        url.pathname.startsWith('/add-to-cart') ||
        url.pathname.startsWith('/update-cart') ||
        url.pathname.startsWith('/place-order') ||
        url.pathname.startsWith('/submit-review') ||
        url.pathname.startsWith('/search-suggestions')) return;

    // Static assets → Cache first, fallback to network
    if (url.pathname.startsWith('/static/')) {
        event.respondWith(
            caches.match(request).then(cached => {
                if (cached) return cached;
                return fetch(request).then(response => {
                    if (response.ok) {
                        const clone = response.clone();
                        caches.open(CACHE_NAME).then(c => c.put(request, clone));
                    }
                    return response;
                });
            })
        );
        return;
    }

    // HTML pages → Network first, fallback to cache
    event.respondWith(
        fetch(request)
            .then(response => {
                if (response.ok) {
                    const clone = response.clone();
                    caches.open(CACHE_NAME).then(c => c.put(request, clone));
                }
                return response;
            })
            .catch(() => caches.match(request).then(cached => {
                if (cached) return cached;
                // Generic offline fallback
                return caches.match('/').then(home => home || new Response(
                    `<!DOCTYPE html><html><head><meta charset="UTF-8">
          <meta name="viewport" content="width=device-width,initial-scale=1">
          <title>FoodRush – Offline</title>
          <style>
            body{font-family:Poppins,sans-serif;background:#0f0f1a;color:#fff;
                 display:flex;flex-direction:column;align-items:center;
                 justify-content:center;min-height:100vh;margin:0;text-align:center;padding:20px;}
            .icon{font-size:4rem;margin-bottom:1rem;}
            h1{font-size:1.8rem;margin-bottom:.5rem;color:#a78bfa;}
            p{color:#94a3b8;margin-bottom:2rem;}
            button{background:linear-gradient(135deg,#7c3aed,#db2777);border:none;
                   color:#fff;padding:12px 28px;border-radius:50px;font-size:1rem;
                   cursor:pointer;font-family:inherit;}
          </style></head>
          <body>
            <div class="icon">🍔</div>
            <h1>You're Offline</h1>
            <p>No internet connection. Please check your network and try again.</p>
            <button onclick="location.reload()">🔄 Try Again</button>
          </body></html>`,
                    { headers: { 'Content-Type': 'text/html' } }
                ));
            }))
    );
});
