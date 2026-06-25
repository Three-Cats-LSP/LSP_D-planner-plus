/**
 * capacitor-bridge.js
 *
 * Intercepts ALL blob download attempts from exportTXT() and exportPDF().
 *
 * jsPDF 2.5.1 uses a.dispatchEvent(new MouseEvent('click')) — NOT a.click().
 * So we patch BOTH methods on HTMLAnchorElement.
 *
 * FILES ARE SAVED TO:
 *   Primary:  /storage/emulated/0/Download/<filename>   (public Downloads folder)
 *             Uses Directory.EXTERNAL_STORAGE + path 'Download/<filename>'
 *             Requires WRITE_EXTERNAL_STORAGE (declared in manifest, maxSdkVersion=32)
 *             On Android 10+ (API 29+) this uses scoped storage — same visible result.
 *   Fallback: Directory.EXTERNAL (app-scoped, USB-visible, no permission needed)
 *   Last:     Directory.CACHE
 *
 * After saving, the Share sheet opens so user can also forward the file.
 * On web/PWA this entire file does nothing.
 */

(function () {
  if (!window.Capacitor || !window.Capacitor.isNativePlatform()) return;

  const FS = 'Filesystem';
  const SH = 'Share';

  // ── helpers ──────────────────────────────────────────────────────────────

  function blobToBase64(blob) {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onloadend = () => resolve(reader.result.split(',')[1]);
      reader.onerror = reject;
      reader.readAsDataURL(blob);
    });
  }

  function notify(msg, isError) {
    console.log('[CapBridge]', msg);
    if (typeof window.showExportToast === 'function') {
      window.showExportToast(msg);
      return;
    }
    const div = document.createElement('div');
    div.textContent = msg;
    div.style.cssText = [
      'position:fixed','bottom:24px','left:50%','transform:translateX(-50%)',
      'background:' + (isError ? 'rgba(220,50,50,0.95)' : 'rgba(30,30,30,0.92)'),
      'color:#fff',
      'padding:10px 22px','border-radius:20px','font-size:13px','z-index:99999',
      'pointer-events:none','max-width:85vw','text-align:center',
      'font-family:sans-serif','line-height:1.4'
    ].join(';');
    document.body.appendChild(div);
    setTimeout(() => div.remove(), isError ? 5000 : 3500);
  }

  // Request storage permission (needed for EXTERNAL_STORAGE on Android ≤ 12).
  // On Android 13+ this is a no-op (permission removed from system).
  async function ensurePermission() {
    const plugin = Capacitor.Plugins[FS];
    if (!plugin || typeof plugin.requestPermissions !== 'function') return true;
    try {
      const result = await plugin.requestPermissions();
      const status = result && result.publicStorage;
      if (status === 'granted') return true;
      if (status === 'denied') {
        notify('Storage permission denied — cannot save to Downloads', true);
        return false;
      }
      if (status != null && status !== 'prompt') {
        console.warn('[CapBridge] unexpected publicStorage permission status:', status);
      }
      return true;
    } catch (e) {
      // Android 13+ throws here — that's fine, we don't need the permission
      console.log('[CapBridge] requestPermissions threw (API 33+, expected):', e && e.message);
      return true;
    }
  }

  // Try writing to a specific directory. Returns { uri, dir } or null.
  async function tryWrite(base64Data, filename, directory, path) {
    try {
      const result = await Capacitor.Plugins[FS].writeFile({
        path: path || filename,
        data: base64Data,
        directory: directory,
        recursive: true
      });
      console.log('[CapBridge] writeFile OK dir=' + directory + ' uri=' + result.uri);
      return { uri: result.uri, dir: directory };
    } catch (err) {
      console.warn('[CapBridge] writeFile FAILED dir=' + directory + ':', err && err.message ? err.message : err);
      return null;
    }
  }

  // Check if a file already exists in a directory using Filesystem.stat().
  async function fileExists(path, directory) {
    try {
      await Capacitor.Plugins[FS].stat({ path, directory });
      return true;
    } catch (e) {
      return false; // stat throws if file not found
    }
  }

  // Return a unique filename by appending (1), (2), ... if the file already exists.
  // e.g. 'LSP_plan.pdf' → 'LSP_plan (1).pdf' → 'LSP_plan (2).pdf'
  async function uniqueFilename(filename, directory, dirPath) {
    const dot = filename.lastIndexOf('.');
    const base = dot > -1 ? filename.slice(0, dot) : filename;
    const ext  = dot > -1 ? filename.slice(dot)    : '';
    const checkPath = p => fileExists(dirPath != null && dirPath !== '' ? dirPath + p : p, directory);

    if (!(await checkPath(filename))) return filename;
    for (let i = 1; i <= 999; i++) {
      const candidate = `${base} (${i})${ext}`;
      if (!(await checkPath(candidate))) return candidate;
    }
    return filename; // fallback — should never reach here
  }

  // Write to Downloads → app External → Cache (first success wins)
  async function saveFile(base64Data, filename) {
    // 1. Public Downloads folder (/sdcard/Download/)
    //    Works on all Android versions with WRITE_EXTERNAL_STORAGE permission
    const dlName = await uniqueFilename(filename, 'EXTERNAL_STORAGE', 'Download/');
    let saved = await tryWrite(base64Data, dlName, 'EXTERNAL_STORAGE', 'Download/' + dlName);
    if (saved) return { ...saved, label: 'Downloads folder', finalName: dlName };

    // 2. App-scoped external (Android/data/com.threecats.lsp.dplanner/files/)
    //    No permission needed, USB-visible
    const extName = await uniqueFilename(filename, 'EXTERNAL', '');
    saved = await tryWrite(base64Data, extName, 'EXTERNAL', extName);
    if (saved) return { ...saved, label: 'Android/data/com.threecats.lsp.dplanner/files/', finalName: extName };

    // 3. Last resort — app cache
    const cacheName = await uniqueFilename(filename, 'CACHE', '');
    saved = await tryWrite(base64Data, cacheName, 'CACHE', cacheName);
    if (saved) return { ...saved, label: 'app cache (use Share to save permanently)', finalName: cacheName };

    return null;
  }

  // Open native Share sheet for a file:// URI
  async function shareFile(fileUri, filename) {
    const plugin = Capacitor.Plugins[SH];
    if (!plugin || typeof plugin.share !== 'function') return;
    try {
      await plugin.share({ title: filename, url: fileUri, dialogTitle: 'Open or share ' + filename });
    } catch (err) {
      const msg = (err && err.message ? err.message : String(err)).toLowerCase();
      if (!msg.includes('cancel') && !msg.includes('dismiss')) {
        notify('Share error: ' + msg, true);
      }
    }
  }

  // ── main handler ─────────────────────────────────────────────────────────

  async function handleBlobDownload(blob, filename) {
    let base64Data;
    try {
      base64Data = await blobToBase64(blob);
    } catch (err) {
      notify('Export failed: cannot read file — ' + err, true);
      return;
    }

    // Request permission first (shows dialog on Android ≤ 12 if not yet granted)
    const ok = await ensurePermission();
    if (!ok) return;

    const saved = await saveFile(base64Data, filename);
    if (!saved) {
      notify('Export failed — could not write to device', true);
      return;
    }

    notify('✓ Saved to ' + saved.label + ': ' + (saved.finalName || filename));

    // Also open Share sheet so user can forward/open in viewer
    await shareFile(saved.uri, saved.finalName || filename);
  }

  // Read blob synchronously — caller may revoke the blob: URL before async fetch completes.
  function readBlobFromHref(href) {
    try {
      const xhr = new XMLHttpRequest();
      xhr.open('GET', href, false);
      xhr.responseType = 'blob';
      xhr.send();
      if (xhr.status === 200 && xhr.response) return xhr.response;
    } catch (_) {}
    try {
      const xhr = new XMLHttpRequest();
      xhr.open('GET', href, false);
      xhr.responseType = 'blob';
      xhr.send();
      if (xhr.status === 200 && xhr.response) {
        if (xhr.response instanceof Blob) return xhr.response;
        if (typeof xhr.response === 'string') return new Blob([xhr.response]);
        if (xhr.response instanceof ArrayBuffer) return new Blob([xhr.response]);
      }
    } catch (_) {}
    return null;
  }

  function interceptBlobDownload(anchor) {
    if (!anchor.download || !anchor.href || !anchor.href.startsWith('blob:')) return false;
    const href = anchor.href;
    const dl = anchor.download;
    const blob = readBlobFromHref(href);
    if (blob) {
      handleBlobDownload(blob, dl).catch(function (err) {
        notify('Export error: ' + (err && err.message ? err.message : err), true);
      });
      return true;
    }
    notify('Export error: could not read export file', true);
    return false;
  }

  // ── patch a.click() — used by exportTXT ──────────────────────────────────

  const _origClick = HTMLAnchorElement.prototype.click;
  HTMLAnchorElement.prototype.click = function () {
    if (interceptBlobDownload(this)) return;
    _origClick.call(this);
  };

  // ── patch a.dispatchEvent() — used by jsPDF doc.save() ───────────────────

  const _origDispatch = HTMLAnchorElement.prototype.dispatchEvent;
  HTMLAnchorElement.prototype.dispatchEvent = function (event) {
    if (
      event instanceof MouseEvent && event.type === 'click' &&
      interceptBlobDownload(this)
    ) {
      return true;
    }
    return _origDispatch.call(this, event);
  };

  console.log('[CapBridge] Active — saving to Downloads folder');
})();
