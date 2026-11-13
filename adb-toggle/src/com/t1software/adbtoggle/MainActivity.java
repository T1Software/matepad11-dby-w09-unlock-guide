package com.t1software.adbtoggle;

import android.app.Activity;
import android.content.Context;
import android.graphics.Color;
import android.graphics.Typeface;
import android.net.wifi.WifiManager;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.widget.Button;
import android.widget.LinearLayout;
import android.widget.ScrollView;
import android.widget.TextView;
import android.widget.ToggleButton;

import java.io.BufferedReader;
import java.io.InputStreamReader;

public class MainActivity extends Activity {

    private static final int PORT = 5555;

    private TextView statusView, ipView, logView;
    private ToggleButton toggle;
    private Handler handler;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        handler = new Handler(Looper.getMainLooper());

        LinearLayout root = new LinearLayout(this);
        root.setOrientation(LinearLayout.VERTICAL);
        int p = dp(20);
        root.setPadding(p, p, p, p);
        root.setBackgroundColor(Color.parseColor("#101014"));

        TextView title = new TextView(this);
        title.setText("ADB over Wi-Fi");
        title.setTextSize(24);
        title.setTypeface(Typeface.DEFAULT_BOLD);
        title.setTextColor(Color.WHITE);
        root.addView(title);

        statusView = new TextView(this);
        statusView.setTextSize(15);
        statusView.setTextColor(Color.parseColor("#9AA0A6"));
        statusView.setPadding(0, dp(8), 0, dp(16));
        root.addView(statusView);

        toggle = new ToggleButton(this);
        toggle.setTextSize(18);
        toggle.setPadding(0, dp(18), 0, dp(18));
        toggle.setOnClickListener(v -> onToggle(toggle.isChecked()));
        root.addView(toggle, new LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT,
                LinearLayout.LayoutParams.WRAP_CONTENT));

        ipView = new TextView(this);
        ipView.setTextSize(22);
        ipView.setTextColor(Color.parseColor("#8AB4F8"));
        ipView.setTypeface(Typeface.MONOSPACE);
        ipView.setPadding(0, dp(20), 0, dp(8));
        root.addView(ipView);

        TextView hint = new TextView(this);
        hint.setText("On your PC:\n  adb connect <ip>:5555");
        hint.setTextSize(14);
        hint.setTextColor(Color.parseColor("#9AA0A6"));
        hint.setTypeface(Typeface.MONOSPACE);
        hint.setPadding(0, 0, 0, dp(16));
        root.addView(hint);

        Button refresh = new Button(this);
        refresh.setText("Refresh");
        refresh.setOnClickListener(v -> refreshState());
        root.addView(refresh);

        logView = new TextView(this);
        logView.setTextSize(12);
        logView.setTextColor(Color.parseColor("#C0C0C0"));
        logView.setTypeface(Typeface.MONOSPACE);
        logView.setPadding(0, dp(16), 0, 0);

        ScrollView scroll = new ScrollView(this);
        scroll.addView(logView);
        root.addView(scroll, new LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT, 0, 1f));

        setContentView(root);
        refreshState();
    }

    private int dp(int v) {
        return Math.round(getResources().getDisplayMetrics().density * v);
    }

    private void refreshState() {
        String svc = shell("getprop service.adb.tcp.port").trim();
        String per = shell("getprop persist.adb.tcp.port").trim();

        boolean on = PORT == parseIntSafe(svc) || PORT == parseIntSafe(per);
        toggle.setChecked(on);
        toggle.setText(on ? "DISABLE" : "ENABLE");
        statusView.setText(on
                ? "Wireless ADB is ON   (persist=" + blank(per) + ")"
                : "Wireless ADB is OFF");

        ipView.setText(getWifiIp() + ":" + PORT);
    }

    private String blank(String s) { return (s == null || s.isEmpty()) ? "-" : s; }

    private int parseIntSafe(String s) {
        try { return Integer.parseInt(s.trim()); } catch (Exception e) { return -1; }
    }

    private void onToggle(boolean enable) {
        toggle.setEnabled(false);
        logView.setText("");
        log("requesting root...");

        new Thread(() -> {
            if (!checkRoot()) {
                post(() -> {
                    log("ERROR: no root.");
                    log("Open APatch -> Superuser and allow this app.");
                    toggle.setEnabled(true);
                    toggle.setChecked(!enable);
                    refreshState();
                });
                return;
            }
            log("root ok");

            if (enable) {
                runRoot("setprop service.adb.tcp.port " + PORT);
                runRoot("setprop persist.adb.tcp.port " + PORT);
                log("set service.adb.tcp.port = " + PORT);
                log("set persist.adb.tcp.port = " + PORT);
                runRoot("setprop ctl.restart adbd");
                log("adbd restarted");
            } else {
                runRoot("setprop service.adb.tcp.port \"\"");
                runRoot("setprop persist.adb.tcp.port \"\"");
                log("cleared both tcp port props");
                runRoot("setprop ctl.restart adbd");
                log("adbd restarted (USB only)");
            }

            sleep(2500);
            String ip = getWifiIp();
            post(() -> {
                toggle.setEnabled(true);
                refreshState();
                log(enable
                        ? "Done.  adb connect " + ip + ":" + PORT
                        : "Done. Wireless ADB disabled.");
            });
        }).start();
    }

    private boolean checkRoot() {
        return runRoot("id").contains("uid=0");
    }

    private String runRoot(String cmd) {
        return shell("su -c '" + cmd.replace("'", "'\\''") + "'");
    }

    private String shell(String cmd) {
        StringBuilder sb = new StringBuilder();
        try {
            Process proc = Runtime.getRuntime().exec(new String[]{"sh", "-c", cmd});
            BufferedReader r = new BufferedReader(new InputStreamReader(proc.getInputStream()));
            String line;
            while ((line = r.readLine()) != null) sb.append(line).append('\n');
            r.close();
            BufferedReader e = new BufferedReader(new InputStreamReader(proc.getErrorStream()));
            while ((line = e.readLine()) != null) sb.append(line).append('\n');
            e.close();
            proc.waitFor();
        } catch (Exception ex) {
            sb.append("EX: ").append(ex.getMessage());
        }
        return sb.toString();
    }

    /** Read the Wi-Fi IPv4 from WifiManager, which needs no shell and no root. */
    private String getWifiIp() {
        try {
            WifiManager wm = (WifiManager) getApplicationContext()
                    .getSystemService(Context.WIFI_SERVICE);
            int ipInt = wm.getConnectionInfo().getIpAddress();
            if (ipInt != 0) {
                return String.format("%d.%d.%d.%d",
                        ipInt & 0xff, (ipInt >> 8) & 0xff,
                        (ipInt >> 16) & 0xff, (ipInt >> 24) & 0xff);
            }
        } catch (Exception ignored) { }
        return "no Wi-Fi";
    }

    private void log(String s) {
        post(() -> logView.append(s + "\n"));
    }

    private void post(Runnable r) {
        handler.post(r);
    }

    private void sleep(long ms) {
        try { Thread.sleep(ms); } catch (InterruptedException ignored) { }
    }
}
