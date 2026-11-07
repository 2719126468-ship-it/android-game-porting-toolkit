package com.agpt.cdogs;

import android.os.Bundle;
import android.util.Log;
import android.view.Gravity;
import android.view.KeyEvent;
import android.view.MotionEvent;
import android.view.View;
import android.widget.Button;
import android.widget.GridLayout;
import android.widget.LinearLayout;
import android.widget.RelativeLayout;

import org.libsdl.app.SDLActivity;

import java.io.File;
import java.io.FileNotFoundException;
import java.io.FileOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.util.HashSet;
import java.util.Set;

/** SDLActivity wrapper with private-storage data deployment and touch controls. */
public final class CdogsActivity extends SDLActivity {
    private static final String TAG = "AGPT-CDogs";
    private static final String DATA_MARKER = ".agpt-cdogs-data-2.5.0";
    private static final String[] DATA_DIRS = {
        "data", "dogfights", "doc", "graphics", "missions", "music", "sounds"
    };

    private final Set<Integer> pressedKeys = new HashSet<>();

    @Override
    protected String[] getLibraries() {
        return new String[] { "SDL2", "SDL2_mixer", "main" };
    }

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        try {
            deployBundledGameData();
        } catch (IOException error) {
            Log.e(TAG, "Failed to deploy C-Dogs game data", error);
            throw new IllegalStateException("C-Dogs game data could not be installed", error);
        }

        super.onCreate(savedInstanceState);
        addTouchControls();
    }

    private void deployBundledGameData() throws IOException {
        File root = getFilesDir();
        if (!root.isDirectory() && !root.mkdirs()) {
            throw new IOException("Cannot create app-private files directory");
        }
        File marker = new File(root, DATA_MARKER);
        if (marker.isFile()) {
            return;
        }

        // Do not overwrite user files or custom campaigns. If a previous first-run
        // extraction was interrupted, the next launch fills only missing files.
        for (String directory : DATA_DIRS) {
            copyAssetTree(directory, new File(root, directory));
        }

        FileOutputStream output = new FileOutputStream(marker);
        try {
            output.write("C-Dogs SDL 2.5.0\n".getBytes("UTF-8"));
            output.flush();
            output.getFD().sync();
        } finally {
            output.close();
        }
    }

    private void copyAssetTree(String assetPath, File target) throws IOException {
        InputStream input = null;
        try {
            input = getAssets().open(assetPath);
        } catch (FileNotFoundException isDirectory) {
            // Directories cannot be opened as streams; recurse through their entries.
        }

        if (input != null) {
            try {
                if (!target.exists()) {
                    File parent = target.getParentFile();
                    if (parent != null && !parent.isDirectory() && !parent.mkdirs()) {
                        throw new IOException("Cannot create " + parent);
                    }
                    FileOutputStream output = new FileOutputStream(target);
                    try {
                        byte[] buffer = new byte[16 * 1024];
                        int count;
                        while ((count = input.read(buffer)) != -1) {
                            output.write(buffer, 0, count);
                        }
                        output.flush();
                        output.getFD().sync();
                    } finally {
                        output.close();
                    }
                }
            } finally {
                input.close();
            }
            return;
        }

        if (!target.isDirectory() && !target.mkdirs()) {
            throw new IOException("Cannot create game-data directory " + target);
        }
        String[] children = getAssets().list(assetPath);
        if (children == null) {
            throw new IOException("Cannot list bundled game-data path " + assetPath);
        }
        for (String child : children) {
            copyAssetTree(assetPath + "/" + child, new File(target, child));
        }
    }

    private Button createKeyButton(String label, final int keyCode) {
        Button button = new Button(this);
        button.setText(label);
        button.setAllCaps(false);
        button.setTextSize(12);
        button.setMinWidth(dp(48));
        button.setMinHeight(dp(48));
        button.setAlpha(0.62f);
        button.setOnTouchListener(new View.OnTouchListener() {
            @Override
            public boolean onTouch(View view, MotionEvent event) {
                int action = event.getActionMasked();
                if (action == MotionEvent.ACTION_DOWN) {
                    if (pressedKeys.add(keyCode)) {
                        SDLActivity.onNativeKeyDown(keyCode);
                    }
                    view.setPressed(true);
                    return true;
                }
                if (action == MotionEvent.ACTION_UP || action == MotionEvent.ACTION_CANCEL) {
                    releaseKey(keyCode);
                    view.setPressed(false);
                    return true;
                }
                return true;
            }
        });
        return button;
    }

    private void addTouchControls() {
        if (mLayout == null) {
            Log.w(TAG, "SDL layout is not ready; touch controls were not attached");
            return;
        }

        LinearLayout pad = new LinearLayout(this);
        pad.setOrientation(LinearLayout.VERTICAL);
        pad.setGravity(Gravity.CENTER);
        pad.setAlpha(0.82f);

        LinearLayout middle = new LinearLayout(this);
        middle.setOrientation(LinearLayout.HORIZONTAL);
        middle.setGravity(Gravity.CENTER);

        pad.addView(createKeyButton("▲", KeyEvent.KEYCODE_DPAD_UP));
        middle.addView(createKeyButton("◀", KeyEvent.KEYCODE_DPAD_LEFT));
        middle.addView(createKeyButton("▼", KeyEvent.KEYCODE_DPAD_DOWN));
        middle.addView(createKeyButton("▶", KeyEvent.KEYCODE_DPAD_RIGHT));
        pad.addView(middle);

        RelativeLayout.LayoutParams padParams = new RelativeLayout.LayoutParams(
            RelativeLayout.LayoutParams.WRAP_CONTENT,
            RelativeLayout.LayoutParams.WRAP_CONTENT
        );
        padParams.addRule(RelativeLayout.ALIGN_PARENT_LEFT);
        padParams.addRule(RelativeLayout.ALIGN_PARENT_BOTTOM);
        padParams.setMargins(dp(10), 0, 0, dp(10));
        mLayout.addView(pad, padParams);

        GridLayout actions = new GridLayout(this);
        actions.setColumnCount(2);
        actions.setRowCount(3);
        actions.setAlpha(0.82f);
        actions.addView(createKeyButton("FIRE · X", KeyEvent.KEYCODE_X));
        actions.addView(createKeyButton("ALT · Z", KeyEvent.KEYCODE_Z));
        actions.addView(createKeyButton("GRENADE · S", KeyEvent.KEYCODE_S));
        actions.addView(createKeyButton("MAP · A", KeyEvent.KEYCODE_A));
        actions.addView(createKeyButton("ENTER", KeyEvent.KEYCODE_ENTER));
        actions.addView(createKeyButton("BACK · ESC", KeyEvent.KEYCODE_ESCAPE));

        RelativeLayout.LayoutParams actionParams = new RelativeLayout.LayoutParams(
            RelativeLayout.LayoutParams.WRAP_CONTENT,
            RelativeLayout.LayoutParams.WRAP_CONTENT
        );
        actionParams.addRule(RelativeLayout.ALIGN_PARENT_RIGHT);
        actionParams.addRule(RelativeLayout.ALIGN_PARENT_BOTTOM);
        actionParams.setMargins(0, 0, dp(10), dp(10));
        mLayout.addView(actions, actionParams);
        actions.bringToFront();
        pad.bringToFront();
    }

    private int dp(int value) {
        return Math.round(value * getResources().getDisplayMetrics().density);
    }

    private void releaseKey(int keyCode) {
        if (pressedKeys.remove(keyCode)) {
            SDLActivity.onNativeKeyUp(keyCode);
        }
    }

    private void releaseAllKeys() {
        Integer[] keys = pressedKeys.toArray(new Integer[pressedKeys.size()]);
        for (Integer key : keys) {
            releaseKey(key);
        }
    }

    @Override
    protected void onPause() {
        releaseAllKeys();
        super.onPause();
    }

    @Override
    protected void onDestroy() {
        releaseAllKeys();
        super.onDestroy();
    }
}
