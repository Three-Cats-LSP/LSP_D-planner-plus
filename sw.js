// LSP D-Planner — Service Worker
// Network-first for HTML (always fresh), cache-first for static assets.
// CACHE_VERSION is derived from app-version.js (same source as index.html APP_VERSION).

importScripts('app-version.js');
const CACHE_VERSION = 'lsp-dplanner-plus-v' + APP_VERSION;

// These are never cached — always fetched live or passed through
const NEVER_CACHE = [
  '.apk',
  '.aab',
  'version.json',
  'raw.githubusercontent.com'
];

function shouldNeverCache(url) {
  return NEVER_CACHE.some(pattern => url.href.includes(pattern));
}

function isHTMLRequest(request) {
  const accept = request.headers.get('Accept') || '';
  return accept.includes('text/html');
}

function getAppBasePath() {
  const p = self.location.pathname || '/';
  if (p.includes('/d-planner-plus')) return '/d-planner-plus/';
  if (p.includes('/d-planner-ccr')) return '/d-planner-ccr/';
  if (p.includes('/d-planner')) return '/d-planner/';
  if (p.includes('/LSP_D-planner-plus')) return '/LSP_D-planner-plus/';
  if (p.includes('/LSP_D-planner')) return '/LSP_D-planner/';
  const swDir = p.replace(/[^/]*$/, '');
  return swDir || '/LSP_D-planner-plus/';
}

const APP_BASE = getAppBasePath();
const OFFLINE_INDEX = APP_BASE + 'index.html';

// Required for offline/PWA startup (Tier-3 ZHL + self-hosted fonts/icons)
const PRECACHE_ASSETS = [
  OFFLINE_INDEX,
  APP_BASE + 'app-version.js',
  APP_BASE + 'capacitor-bridge.js',
  APP_BASE + 'android-select-picker.js',
  APP_BASE + 'zhl-engine-bundle.js',
  APP_BASE + 'vpm-engine-bundle.js',
  APP_BASE + 'zhl-worker-bridge.js',
  APP_BASE + 'zhl-schedule-worker.js',
  APP_BASE + 'vendor/jspdf.umd.min.js',
  APP_BASE + 'vendor/fonts/fonts.css',
  APP_BASE + 'vendor/fonts/DejaVuSans.ttf',
  APP_BASE + 'vendor/fonts/DejaVuSans-Bold.ttf',
  APP_BASE + 'vendor/fonts/JTUSjIg69CK48gW7PXoo9Wdhyzbi.woff2',
  APP_BASE + 'vendor/fonts/JTUSjIg69CK48gW7PXoo9Wlhyw.woff2',
  APP_BASE + 'vendor/fonts/QGYvz_MVcBeNP4NJtEtq.woff2',
  APP_BASE + 'vendor/fonts/QGYvz_MVcBeNP4NJuktqQ4E.woff2',
  APP_BASE + 'vendor/fonts/tDbV2o-flEEny0FZhsfKu5WU4xD0OwG_TA.woff2',
  APP_BASE + 'vendor/fonts/tDbV2o-flEEny0FZhsfKu5WU4xD1OwG_TA.woff2',
  APP_BASE + 'vendor/fonts/tDbV2o-flEEny0FZhsfKu5WU4xD2OwG_TA.woff2',
  APP_BASE + 'vendor/fonts/tDbV2o-flEEny0FZhsfKu5WU4xD4OwG_TA.woff2',
  APP_BASE + 'vendor/fonts/tDbV2o-flEEny0FZhsfKu5WU4xD7OwE.woff2',
  APP_BASE + 'vendor/fonts/tDbV2o-flEEny0FZhsfKu5WU4xD_OwG_TA.woff2',
  APP_BASE + 'vendor/icons/giw-icon-192.png',
  APP_BASE + 'vendor/icons/toolbox-204167.png',
  APP_BASE + 'vendor/icons/settings-2099058.png',
  APP_BASE + 'manifest.json',
  APP_BASE + 'icon-192.png',
  APP_BASE + 'icon-512.png',
];

// Install — skip waiting immediately so new SW takes over fast
self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(CACHE_VERSION)
      .then(cache => cache.addAll(PRECACHE_ASSETS))
      .then(() => self.skipWaiting())
  );
});

// Activate — delete ALL old caches, claim clients immediately
self.addEventListener('activate', event => {
  event.waitUntil(
    caches.keys()
      .then(keys => Promise.all(
        keys
          .filter(key => key !== CACHE_VERSION)
          .map(key => {
            console.log('[SW] Deleting old cache:', key);
            return caches.delete(key);
          })
      ))
      .then(() => self.clients.claim())
  );
});

self.addEventListener('message', event => {
  if (event.data && event.data.type === 'SKIP_WAITING') {
    self.skipWaiting();
  }
});

// Fetch strategy:
//   - APK / external URLs: pass through, never intercept
//   - HTML (index.html, navigation): network-first, cache fallback
//   - Everything else (JS, CSS, fonts, etc.): cache-first, network fallback
self.addEventListener('fetch', event => {
  if (event.request.method !== 'GET') return;

  const url = new URL(event.request.url);

  // Never intercept cross-origin or APK requests
  if (url.origin !== self.location.origin) return;
  if (shouldNeverCache(url)) return;

  // Network-first for HTML — ensures index.html is always up to date
  if (isHTMLRequest(event.request) || url.pathname.endsWith('.html') || url.pathname.endsWith('/')) {
    event.respondWith(
      fetch(event.request)
        .then(response => {
          if (response.ok) {
            // Update cache with fresh version
            const clone = response.clone();
            caches.open(CACHE_VERSION).then(cache => {
              const key = new Request(url.origin + url.pathname);
              cache.put(key, clone);
            });
          }
          return response;
        })
        .catch(() => {
          // Network failed — serve cached version as offline fallback
          return caches.match(event.request, { ignoreSearch: true })
            .then(cached => cached || caches.match(OFFLINE_INDEX, { ignoreSearch: true }));
        })
    );
    return;
  }

  // Cache-first for all other static assets
  event.respondWith(
    caches.match(event.request, { ignoreSearch: true })
      .then(cached => {
        if (cached) return cached;
        return fetch(event.request)
          .then(response => {
            if (response.ok && url.pathname.startsWith(APP_BASE)) {
              const clone = response.clone();
              const cacheKey = new Request(url.origin + url.pathname);
              caches.open(CACHE_VERSION).then(cache => cache.put(cacheKey, clone));
            }
            return response;
          });
      })
  );
});
