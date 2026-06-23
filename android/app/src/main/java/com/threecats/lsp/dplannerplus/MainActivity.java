package com.threecats.lsp.dplannerplus;

import android.os.Bundle;
import android.webkit.CookieManager;
import androidx.core.view.WindowCompat;
import androidx.core.view.WindowInsetsControllerCompat;
import com.getcapacitor.BridgeActivity;

public class MainActivity extends BridgeActivity {

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        WindowCompat.setDecorFitsSystemWindows(getWindow(), false);
        applyStatusBarIconColor();
    }

    @Override
    public void onResume() {
        super.onResume();
        applyStatusBarIconColor();
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
