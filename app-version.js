/**
 * App version — single source of truth for index.html and sw.js.
 * Bump here only; sw.js derives CACHE_VERSION from APP_VERSION via importScripts.
 */
(function (g) {
  'use strict';
  g.APP_VERSION = '2.51.18';
})(typeof self !== 'undefined' ? self : globalThis);
