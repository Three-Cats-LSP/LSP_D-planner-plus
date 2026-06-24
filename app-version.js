/**
 * App version — single source of truth for index.html and sw.js.
 * Bump here only; sw.js derives CACHE_VERSION from APP_VERSION via importScripts.
 */
const APP_VERSION = '2.51.04';
(function (g) {
  g.APP_VERSION = APP_VERSION;
})(typeof self !== 'undefined' ? self : globalThis);
