/* GPL-3.0-or-later. App-level ContentResolver client, not the privileged content shell tool. */
package local.pt.schedule;
import android.content.Context;
import android.net.Uri;
import android.os.Bundle;
import org.json.JSONObject;

public final class ScheduleClient {
    public static void main(String[] args) {
        try { run(args); }
        catch (Throwable e) { e.printStackTrace(System.err); System.exit(1); }
    }
    private static void run(String[] args) throws Exception {
        if (args.length < 1 || args.length > 2) throw new IllegalArgumentException("command [JSON]");
        android.os.Looper.prepareMainLooper();
        Class<?> type = Class.forName("android.app.ActivityThread");
        Object thread = type.getMethod("systemMain").invoke(null);
        Context system = (Context) type.getMethod("getSystemContext").invoke(thread);
        android.content.pm.ApplicationInfo info = system.getPackageManager().getApplicationInfo("com.termux", 0);
        Class<?> compatibility = Class.forName("android.content.res.CompatibilityInfo");
        Object defaultCompatibility = compatibility.getField("DEFAULT_COMPATIBILITY_INFO").get(null);
        Object loadedApk = type.getMethod("getPackageInfoNoCheck", android.content.pm.ApplicationInfo.class, compatibility)
            .invoke(thread, info, defaultCompatibility);
        java.lang.reflect.Method createContext = Class.forName("android.app.ContextImpl")
            .getDeclaredMethod("createAppContext", type, Class.forName("android.app.LoadedApk"));
        createContext.setAccessible(true);
        Context termux = (Context) createContext.invoke(null, thread, loadedApk);
        if ("context-check".equals(args[0])) {
            System.out.println(new JSONObject().put("uid", android.os.Process.myUid())
                .put("package", termux.getPackageName()).put("opPackage", termux.getOpPackageName()));
            System.exit(0);
        }
        Bundle result = termux.getContentResolver().call(
            Uri.parse("content://org.fossify.clock.schedule.schedule.api"), args[0],
            args.length == 2 ? args[1] : "{}", null);
        if (result == null) throw new IllegalStateException("No API response");
        String json = result.getString("json");
        System.out.println(json);
        if (json == null || !new JSONObject(json).optBoolean("ok")) System.exit(1);
        System.exit(0);
    }
}
