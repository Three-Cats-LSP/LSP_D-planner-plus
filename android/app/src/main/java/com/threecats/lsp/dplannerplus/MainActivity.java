package com.threecats.lsp.dplannerplus;

import android.os.Bundle;
import android.webkit.CookieManager;
import android.webkit.WebView;
import androidx.core.view.WindowCompat;
import androidx.core.view.WindowInsetsControllerCompat;
import com.getcapacitor.BridgeActivity;

public class MainActivity extends BridgeActivity {

    private static final String NATIVE_SELECT_FIX_JS =
        "document.documentElement.classList.add('android-webview','capacitor-native');";

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        WindowCompat.setDecorFitsSystemWindows(getWindow(), false);
        applyStatusBarIconColor();
        injectNativeSelectFix();
    }

    @Override
    public void onResume() {
        super.onResume();
        applyStatusBarIconColor();
        injectNativeSelectFix();
    }

    private void injectNativeSelectFix() {
        try {
            WebView webView = getBridge() != null ? getBridge().getWebView() : null;
            if (webView != null) {
                webView.post(() -> webView.evaluateJavascript(NATIVE_SELECT_FIX_JS, null));
            }
        } catch (Exception ignored) {
            // Non-critical
        }
    }

    private void applyStatusBarIconColor() {
        try {
            String cookies = CookieManager.getInstance().getCookie("https://localhost");
            boolean isLight = false;
            if (cookies != null) {
                for (String part : cookies.split(";")) {
                    String trimmed = part.trim();
                    if (trimmed.startsWith("diveTheme=")) {
                        isLight = "light".equals(trimmed.substring("diveTheme=".length()).trim());
                        break;
                    }
                }
            }
            WindowInsetsControllerCompat ctrl =
                new WindowInsetsControllerCompat(getWindow(), getWindow().getDecorView());
            ctrl.setAppearanceLightStatusBars(isLight);
        } catch (Exception e) {
            // Non-critical
        }
    }
}
