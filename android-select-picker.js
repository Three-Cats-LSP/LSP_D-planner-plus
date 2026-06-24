/**
 * Android WebView/Capacitor: replace native <select> picker with an in-app sheet.
 * Native picker shows blank options when web fonts / appearance CSS are applied.
 */
(function (global) {
  'use strict';

  function isAndroidNative() {
    return document.documentElement.classList.contains('android-webview')
      || document.documentElement.classList.contains('capacitor-native')
      || (global.Capacitor && global.Capacitor.isNativePlatform && global.Capacitor.isNativePlatform());
  }

  if (!isAndroidNative()) return;

  var selectObservers = [];

  function disconnectAllObservers() {
    selectObservers.forEach(function (obs) {
      try { obs.disconnect(); } catch (_) {}
    });
    selectObservers = [];
  }

  if (typeof window !== 'undefined') {
    window.addEventListener('beforeunload', disconnectAllObservers);
  }

  /** Wrapped select -> syncBtn(); used when .value / .selectedIndex change without change event. */
  var selectSyncFns = typeof WeakMap !== 'undefined' ? new WeakMap() : null;
  var valueSetterPatched = false;

  function patchSelectValueSetters() {
    if (valueSetterPatched || !selectSyncFns) return;
    valueSetterPatched = true;
    var proto = HTMLSelectElement.prototype;
    var valueDesc = Object.getOwnPropertyDescriptor(proto, 'value');
    var idxDesc = Object.getOwnPropertyDescriptor(proto, 'selectedIndex');
    if (valueDesc && valueDesc.set) {
      Object.defineProperty(proto, 'value', {
        configurable: true,
        enumerable: valueDesc.enumerable,
        get: valueDesc.get,
        set: function (v) {
          valueDesc.set.call(this, v);
          var sync = selectSyncFns.get(this);
          if (sync) sync();
        }
      });
    }
    if (idxDesc && idxDesc.set) {
      Object.defineProperty(proto, 'selectedIndex', {
        configurable: true,
        enumerable: idxDesc.enumerable,
        get: idxDesc.get,
        set: function (v) {
          idxDesc.set.call(this, v);
          var sync = selectSyncFns.get(this);
          if (sync) sync();
        }
      });
    }
  }

  function syncSelect(sel) {
    if (!selectSyncFns || !sel) return;
    var sync = selectSyncFns.get(sel);
    if (sync) sync();
  }

  function syncAllSelects() {
    if (!selectSyncFns) return;
    selectSyncFns.forEach(function (sync) { sync(); });
  }

  global.LspAndroidSelect = { sync: syncSelect, syncAll: syncAllSelects };

  function labelForSelect(sel) {
    var idx = sel.selectedIndex;
    if (idx < 0) return '—';
    var opt = sel.options[idx];
    return opt ? (opt.textContent || opt.label || opt.value || '—') : '—';
  }

  function titleForSelect(sel) {
    var field = sel.closest('.field');
    if (field) {
      var label = field.querySelector('label');
      if (label && label.textContent.trim()) return label.textContent.trim();
    }
    if (sel.id) return sel.id.replace(/([A-Z])/g, ' $1').replace(/^./, function (c) { return c.toUpperCase(); });
    return 'Choose option';
  }

  function closeSheet() {
    var sheet = document.getElementById('lsp-android-select-sheet');
    if (sheet) sheet.remove();
    document.body.classList.remove('lsp-android-select-open');
  }

  function openSheet(sel, syncBtn) {
    closeSheet();

    var overlay = document.createElement('div');
    overlay.id = 'lsp-android-select-sheet';
    overlay.className = 'lsp-android-select-sheet';
    overlay.addEventListener('click', function (e) {
      if (e.target === overlay) closeSheet();
    });

    var panel = document.createElement('div');
    panel.className = 'lsp-android-select-panel';
    panel.addEventListener('click', function (e) { e.stopPropagation(); });

    var heading = document.createElement('div');
    heading.className = 'lsp-android-select-title';
    heading.textContent = titleForSelect(sel);

    var list = document.createElement('div');
    list.className = 'lsp-android-select-list';
    list.setAttribute('role', 'listbox');

    for (var i = 0; i < sel.options.length; i++) {
      (function (opt, index) {
        if (opt.disabled && !opt.selected) return;
        var item = document.createElement('button');
        item.type = 'button';
        item.className = 'lsp-android-select-item';
        item.setAttribute('role', 'option');
        if (index === sel.selectedIndex) item.classList.add('is-selected');
        item.textContent = opt.textContent || opt.label || opt.value;
        if (opt.disabled) {
          item.disabled = true;
          item.setAttribute('aria-disabled', 'true');
          item.classList.add('is-disabled-option');
        }
        item.addEventListener('click', function () {
          if (opt.disabled) return;
          sel.selectedIndex = index;
          sel.dispatchEvent(new Event('change', { bubbles: true }));
          syncBtn();
          closeSheet();
        });
        list.appendChild(item);
      })(sel.options[i], i);
    }

    panel.appendChild(heading);
    panel.appendChild(list);
    overlay.appendChild(panel);
    document.body.appendChild(overlay);
    document.body.classList.add('lsp-android-select-open');
    var selectedItem = list.querySelector('.is-selected');
    if (selectedItem) {
      requestAnimationFrame(function () {
        selectedItem.scrollIntoView({ block: 'nearest' });
      });
    }
  }

  function wrapSelect(sel) {
    if (sel.dataset.lspAndroidSelect === '1') return;
    sel.dataset.lspAndroidSelect = '1';

    var wrap = document.createElement('div');
    wrap.className = 'lsp-android-select-wrap';
    sel.parentNode.insertBefore(wrap, sel);
    wrap.appendChild(sel);

    var btn = document.createElement('button');
    btn.type = 'button';
    btn.className = 'lsp-android-select-btn' + (sel.className ? (' ' + sel.className) : '');
    btn.setAttribute('aria-haspopup', 'listbox');

    function syncBtn() {
      btn.textContent = labelForSelect(sel);
      btn.disabled = !!sel.disabled;
      btn.classList.toggle('is-disabled', !!sel.disabled);
    }
    syncBtn();

    if (selectSyncFns) selectSyncFns.set(sel, syncBtn);

    btn.addEventListener('click', function () {
      if (sel.disabled) return;
      openSheet(sel, syncBtn);
    });

    wrap.appendChild(btn);
    sel.classList.add('lsp-android-select-native');
    sel.setAttribute('tabindex', '-1');
    sel.setAttribute('aria-hidden', 'true');

    sel.addEventListener('change', syncBtn);

    function blockNative(e) {
      e.preventDefault();
      if (!sel.disabled) openSheet(sel, syncBtn);
    }
    sel.addEventListener('mousedown', blockNative);
    sel.addEventListener('touchstart', blockNative, { passive: false });
    sel.addEventListener('focus', function () { sel.blur(); });

    var selObserver = new MutationObserver(function () { syncBtn(); });
    selObserver.observe(sel, {
      childList: true,
      subtree: true,
      attributes: true,
      attributeFilter: ['disabled']
    });
    selectObservers.push(selObserver);
  }

  function enhanceAll(root) {
    var scope = root && root.querySelectorAll ? root : document;
    scope.querySelectorAll('select:not([data-lsp-android-select="1"])').forEach(wrapSelect);
  }

  function boot() {
    patchSelectValueSetters();
    enhanceAll(document);
    var domObserver = new MutationObserver(function (mutations) {
      mutations.forEach(function (m) {
        m.addedNodes.forEach(function (node) {
          if (node.nodeType !== 1) return;
          if (node.tagName === 'SELECT') wrapSelect(node);
          else enhanceAll(node);
        });
      });
    });
    domObserver.observe(document.documentElement, { childList: true, subtree: true });
    selectObservers.push(domObserver);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', boot);
  } else {
    boot();
  }
})(typeof window !== 'undefined' ? window : globalThis);
